import logging
import os
from pathlib import Path
from typing import List, Union

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from yt_dlp.utils import sanitize_filename

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata, MetadataType
from models.service_list import Services
from modules.base_service import BaseService
from utils import process_video_for_telegram, escape_html, truncate_string, store_url, url_hash
from .models import NicoVideoCallback
from .utils import get_video_formats

logger = logging.getLogger(__name__)


class NicoVideoService(BaseService):
    name = "NicoVideo"

    def __init__(self, output_path: str = "storage/temp/", arq=None) -> None:
        super().__init__()
        self.output_path = output_path
        self.arq = arq

    async def get_info(self, url: str, **kwargs) -> MediaMetadata | None:
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True,
            )

        store_url(url)

        job = await self.arq.enqueue_job(
            "universal_ytdlp_extract",
            url=url,
            extract_only=True,
            _queue_name="heavy",
        )
        try:
            result = await job.result()
        except Exception as e:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                service=Services.NICOVIDEO,
                message=f"Failed to fetch NicoVideo info: {e}",
                url=url,
                critical=True,
                is_logged=True
            )
        clean_info = result.get("info")

        if not clean_info:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="No video info returned from NicoVideo",
                url=url,
                service=Services.NICOVIDEO,
                critical=True,
                is_logged=True,
            )

        formats_data = get_video_formats(clean_info.get("formats") or [], max_size_mb=100, duration=clean_info.get("duration"))
        formats = formats_data.get("formats", [])
        if not formats:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="No valid formats found for NicoVideo",
                url=url,
                service=Services.NICOVIDEO,
                is_logged=True,
            )

        markup = InlineKeyboardBuilder()
        row: list = []

        for video_format in formats:
            try:
                callback_data_video = NicoVideoCallback(
                    type="video",
                    video_id=video_format['video_format_id'],
                    audio_id=video_format['audio_format_id'],
                    url_hash=url_hash(url)
                ).pack()

                button = InlineKeyboardButton(
                    text=f"🎬 {video_format['resolution']}, {video_format['total_size_mb']}MB",
                    callback_data=callback_data_video
                )
                row.append(button)

                if len(row) == 2:
                    markup.row(*row)
                    row = []
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to create button for format {video_format}: {e}")
                continue

        if row:
            markup.row(*row)

        # Adding the best audio download button
        if formats_data.get("best_audio"):
            try:
                callback_data_audio = NicoVideoCallback(
                    type="audio",
                    audio_id=formats_data['best_audio']['format_id'],
                    url_hash=url_hash(url)
                ).pack()

                markup.row(
                    InlineKeyboardButton(
                        text="🎵 Audio",
                        callback_data=callback_data_audio
                    )
                )
            except (KeyError, ValueError) as e:
                logger.warning(f"Failed to create audio button: {e}")

        # ---- Thumbnail ----
        video_id_str = clean_info.get("id", "unknown")
        safe_id = sanitize_filename(str(video_id_str))
        thumbnail_path = os.path.join(self.output_path, f"{safe_id}.jpg")
        thumbnail_url = clean_info.get("thumbnail")
        if thumbnail_url:
            try:
                await self.arq.enqueue_job(
                    "universal_download",
                    url=thumbnail_url,
                    destination=thumbnail_path,
                    _queue_name="light",
                )
            except Exception as e:
                logger.warning(f"Failed to download NicoVideo thumbnail: {e}")

        return MediaMetadata(
            type=MetadataType.METADATA,
            url=url,
            title=clean_info.get("title"),
            description=clean_info.get("description"),
            duration=clean_info.get("duration"),
            performer=clean_info.get("uploader") or clean_info.get("channel"),
            performer_url=clean_info.get("channel_url") or clean_info.get("webpage_url"),
            cover=thumbnail_path,
            media_type="video",
            keyboard=markup.as_markup(),
        )

    async def download(
        self,
        url: Union[str, MediaMetadata],
        video_id: str = "__default__",
        audio_id: str | None = None,
        media_type: str = "video",
        **kwargs,
    ) -> List[MediaContent]:
        if isinstance(url, MediaMetadata):
            url = url.url

        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True,
            )

        if media_type == "audio":
            return await self.download_audio(url, audio_id)
        return await self.download_video(url, video_id, audio_id)

    async def download_video(
        self,
        url: str,
        video_id: str = "__default__",
        audio_id: str | None = None,
    ) -> List[MediaContent]:
        # Build yt-dlp format selector
        if video_id == "__default__" or not video_id:
            # Let yt-dlp choose automatically
            actual_format: str | None = None
        elif audio_id:
            actual_format = f"{video_id}+{audio_id}"
        else:
            actual_format = video_id

        logger.info(f"Downloading NicoVideo: {url} (format_selector={actual_format!r})")

        output_template = os.path.join(
            self.output_path,
            f"%(id)s_{sanitize_filename('%(title)s')}.%(ext)s",
        )

        job = await self.arq.enqueue_job(
            "universal_ytdlp_extract",
            url=url,
            extract_only=False,
            format_selector=actual_format,
            output_template=output_template,
            _queue_name="heavy",
        )
        try:
            result = await job.result()
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                service=Services.NICOVIDEO,
                message=f"Failed to download NicoVideo: {e}",
                url=url,
                critical=True,
                is_logged=True
            )

        clean_info = result.get("info")
        filepath = result.get("filepath")

        if not filepath:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message="yt-dlp returned no file path",
                url=url,
                service=Services.NICOVIDEO,
                is_logged=True,
                critical=True,
            )

        fixed_video, thumbnail, width, height, duration = await process_video_for_telegram(
            self.arq, filepath
        )

        # Only use thumbnail if it actually exists on disk
        cover_path = Path(thumbnail) if thumbnail and os.path.exists(thumbnail) else None

        title = truncate_string(
            escape_html(clean_info.get("title") or "NicoVideo") if clean_info else "NicoVideo",
            100,
        )
        performer = (
            clean_info.get("uploader") or clean_info.get("channel") or "NicoVideo"
        ) if clean_info else "NicoVideo"

        return [
            MediaContent(
                type=MediaType.VIDEO,
                path=Path(fixed_video),
                title=title,
                performer=performer,
                width=width,
                height=height,
                duration=int(duration),
                cover=cover_path,
            )
        ]

    async def download_audio(self, url: str, format_id: str) -> List[MediaContent]:
        logger.info(f"Starting audio download for URL: {url} with format: {format_id}")

        output_template = os.path.join(
            self.output_path,
            f"%(id)s_{sanitize_filename('%(title)s')}.%(ext)s",
        )

        # Скачиваем аудио без конвертации для сохранения качества
        job = await self.arq.enqueue_job(
            "universal_ytdlp_extract",
            url=url,
            extract_only=False,
            format_selector=format_id,
            output_template=output_template,
            extract_audio=True,
            _queue_name="heavy",
        )
        try:
            result = await job.result()
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                service=Services.NICOVIDEO,
                message=f"Failed to download NicoVideo audio: {e}",
                url=url,
                critical=True,
                is_logged=True
            )

        clean_info = result.get("info")
        filepath = result.get("filepath")

        if not filepath:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message="yt-dlp returned no file path",
                url=url,
                service=Services.NICOVIDEO,
                is_logged=True,
                critical=True,
            )

        base_path = filepath.rsplit(".", 1)[0]
        thumbnail_path = f"{base_path}.jpg"

        thumbnail_url = clean_info.get("thumbnail") if clean_info else None
        if thumbnail_url:
            try:
                await self.arq.enqueue_job(
                    "universal_download",
                    url=thumbnail_url,
                    destination=thumbnail_path,
                    _queue_name="light",
                )
            except Exception as e:
                logger.warning(f"Failed to download thumbnail: {e}")

        job = await self.arq.enqueue_job(
            "universal_metadata_update",
            filepath,
            title=clean_info.get("title", "audio") if clean_info else "audio",
            artist=clean_info.get("uploader", "NicoVideo") if clean_info else "NicoVideo",
            cover_file=thumbnail_path,
            _queue_name="heavy",
        )
        try:
            await job.result()
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            # Not critical since the file is already downloaded
            # But let's log it

        return [
            MediaContent(
                type=MediaType.AUDIO,
                path=Path(filepath),
                duration=clean_info.get("duration", 0) if clean_info else 0,
                title=truncate_string(
                    escape_html(clean_info.get("title") or "NicoVideo") if clean_info else "NicoVideo",
                    100,
                ),
                cover=Path(thumbnail_path) if os.path.exists(thumbnail_path) else None,
            )
        ]
