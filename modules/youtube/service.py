import logging
import os
from pathlib import Path
from typing import List

from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from yt_dlp.utils import sanitize_filename

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata, MetadataType
from modules.base_service import BaseService
from utils import store_url, url_hash, process_video_for_telegram
from models.service_list import Services

from .models import YoutubeCallback
from .utils import get_video_info, get_ytdlp_options

logger = logging.getLogger(__name__)


class YouTubeService(BaseService):
    name = "YouTube"

    def __init__(self, output_path: str = "storage/temp/", arq = None) -> None:
        super().__init__()
        self.output_path = output_path
        self.arq = arq

    async def download(self, url: str, format_choice: str = "") -> List[MediaContent]:
        if not format_choice:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message="Format choice is required",
                url=url,
                service=Services.YOUTUBE,
                is_logged=True
            )

        parts = format_choice.split('_')
        if len(parts) < 3:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Invalid format choice: {format_choice}",
                url=url,
                service=Services.YOUTUBE,
                is_logged=True
            )

        media_type = parts[-2]
        media_format = parts[-1]

        if media_type == "audio":
            return await self.download_audio(url, media_format)
        return await self.download_video(url, media_format)

    async def get_info(self, url: str) -> MediaMetadata|None:
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )

        # Сохраняем URL в кеше для обратного преобразования
        store_url(url)

        job = await self.arq.enqueue_job(
            "universal_ytdlp_extract",
            url=url,
            extract_only = True,
            extra_opts=get_ytdlp_options(),
            _queue_name='heavy'
        )
        result = await job.result()
        clean_info = result["info"]

        if not clean_info:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="No video info returned",
                url=url,
                service=Services.YOUTUBE,
                critical=True,
                is_logged=True
            )

        video_info = await get_video_info(clean_info, max_size_mb=1024)

        video_id = clean_info.get('id', 'unknown')
        video_title = clean_info.get('title', 'video')

        # Validate and sanitize to prevent path traversal
        safe_id = sanitize_filename(str(video_id))
        safe_title = sanitize_filename(str(video_title))

        base_path = os.path.join(
            self.output_path,
            f"{safe_id}_{safe_title}"
        )
        # Ensure the path is within output_path
        base_path = os.path.abspath(base_path)
        if not base_path.startswith(os.path.abspath(self.output_path)):
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Invalid file path detected",
                url=url,
                service=Services.YOUTUBE,
                critical=True,
                is_logged=True
            )

        thumbnail_path = f"{base_path}.jpg"

        thumbnail_url = clean_info.get("thumbnail", None)
        if thumbnail_url:
            try:
                await self.arq.enqueue_job('universal_download', url=thumbnail_url, destination=thumbnail_path, _queue_name='light')
            except Exception as e:
                logger.warning(f"Failed to download thumbnail: {e}")

        markup = InlineKeyboardBuilder()
        formats = list(reversed(video_info["formats"]))

        # Building keyboard row
        row = []
        for video_format in formats:
            try:
                callback_data_video = YoutubeCallback(
                    type="video",
                    sponsored=False,
                    format_id=video_format['video_format_id'],
                    audio_id=video_format['audio_format_id'],
                    url_hash=url_hash(url)
                ).pack()

                callback_data_video_sponsor = YoutubeCallback(
                    type="video",
                    sponsored=True,
                    format_id=video_format['video_format_id'],
                    audio_id=video_format['audio_format_id'],
                    url_hash=url_hash(url)
                ).pack()

                if video_format['total_size_mb'] > 100:
                    button = InlineKeyboardButton(
                        text=f"⭐ {video_format['resolution']}, {video_format['total_size_mb']}MB",
                        callback_data=callback_data_video_sponsor
                    )
                else:
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
        if video_info["best_audio"]:
            try:
                callback_data_audio = YoutubeCallback(
                    type="audio",
                    format_id=video_info['best_audio']['format_id'],
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

        return MediaMetadata(
            type=MetadataType.METADATA,
            url=url,
            title=clean_info.get("title", None),
            description=clean_info.get("description", None),
            duration=clean_info.get("duration", None),
            performer=clean_info.get("uploader", None),
            performer_url=clean_info.get("channel_url", None),
            cover=thumbnail_path,
            media_type="video",
            keyboard=markup.as_markup()
        )

    async def download_video(self, url: str, format: str) -> List[MediaContent]:
        logger.info(f"Starting video download for URL: {url} with format: {format}")
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )
        try:
            job = await self.arq.enqueue_job(
                "universal_ytdlp_extract",
                url=url,
                extract_only = False,
                format_selector=format,
                output_template=f"{self.output_path}%(id)s_{sanitize_filename('%(title)s')}.%(ext)s",
                extra_opts=get_ytdlp_options(),
                _queue_name='heavy'
            )
            result = await job.result()
            clean_info = result["info"]
            filepath = result["filepath"]

            if not clean_info:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message="Failed to download video",
                    url=url,
                    service=Services.YOUTUBE,
                    critical=True,
                    is_logged=True
                )

            fixed_video, thumbnail, width, height, duration = await process_video_for_telegram(self.arq, filepath)

            return [
                MediaContent(
                    type=MediaType.VIDEO,
                    path=Path(fixed_video),
                    width=width,
                    height=height,
                    duration=int(duration),
                    title=clean_info.get("title", "video"),
                    cover=Path(thumbnail)
                )
            ]
        except BotError as ebot:
            ebot.service = Services.YOUTUBE
            raise ebot

    async def download_audio(self, url: str, format: str) -> List[MediaContent]:
        logger.info(f"Starting audio download for URL: {url} with format: {format}")
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )

        try:
            job = await self.arq.enqueue_job(
                "universal_ytdlp_extract",
                url=url,
                extract_only = False,
                format_selector=format,
                output_template=f"{self.output_path}%(id)s_{sanitize_filename('%(title)s')}.%(ext)s",
                extra_opts=get_ytdlp_options(),
                extract_audio=True,
                _queue_name='heavy'
            )
            result = await job.result()
            clean_info = result["info"]
            filepath = result["filepath"]

            if not clean_info:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message="Failed to download audio",
                    service=Services.YOUTUBE,
                    url=url,
                    is_logged=True
                )

            # Use yt-dlp's prepare_filename to get actual file path
            base_path = filepath.rsplit('.', 1)[0]
            thumbnail_path = f"{base_path}.jpg"

            thumbnail_url = clean_info.get("thumbnail", None)
            if thumbnail_url:
                try:
                    await self.arq.enqueue_job('universal_download', url=thumbnail_url, destination=thumbnail_path, _queue_name='light')
                except Exception as e:
                    logger.warning(f"Failed to download thumbnail: {e}")

            job = await self.arq.enqueue_job(
                "universal_metadata_update",
                filepath,
                title=clean_info.get("title", "audio"),
                artist=clean_info.get("uploader", "unknown"),
                cover_file=thumbnail_path,
                _queue_name='heavy'
            )

            await job.result()

            return [MediaContent(
                type=MediaType.AUDIO,
                path=Path(filepath),
                duration=clean_info.get("duration", 0),
                title=clean_info.get("title", "audio"),
                cover=Path(thumbnail_path)
            )]
        except BotError as ebot:
            ebot.service = Services.YOUTUBE
            raise ebot
