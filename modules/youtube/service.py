import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

import yt_dlp
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from yt_dlp.utils import sanitize_filename

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata, MetadataType
from modules.base_service import BaseService
from utils import download_file, store_url, async_update_metadata, url_hash
from models.service_list import Services

from .models import YoutubeCallback
from .utils import get_video_info, get_ytdlp_options

logger = logging.getLogger(__name__)


class YouTubeService(BaseService):
    name = "YouTube"
    _download_executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, output_path: str = "storage/temp/") -> None:
        super().__init__()
        self.output_path = output_path

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
        # Сохраняем URL в кеше для обратного преобразования
        store_url(url)

        with yt_dlp.YoutubeDL(get_ytdlp_options()) as ydl:
            loop = asyncio.get_running_loop()
            info_dict = await loop.run_in_executor(
                self._download_executor,
                lambda: ydl.extract_info(url, download=False)
            )

        if not info_dict:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="No video info returned",
                url=url,
                service=Services.YOUTUBE,
                critical=True,
                is_logged=True
            )

        video_info = await get_video_info(info_dict, max_size_mb=1024)

        video_id = info_dict.get('id', 'unknown')
        video_title = info_dict.get('title', 'video')

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

        thumbnail_url = info_dict.get("thumbnail", None)
        if thumbnail_url:
            try:
                await download_file(thumbnail_url, thumbnail_path)
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
            title=info_dict.get("title", None),
            description=info_dict.get("description", None),
            duration=info_dict.get("duration", None),
            performer=info_dict.get("uploader", None),
            performer_url=info_dict.get("channel_url", None),
            cover=thumbnail_path,
            media_type="video",
            keyboard=markup.as_markup()
        )

    async def download_video(self, url: str, format: str) -> List[MediaContent]:
        logger.info(f"Starting video download for URL: {url} with format: {format}")
        options = get_ytdlp_options()
        options["format"] = format
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                loop = asyncio.get_event_loop()

                info_dict = await loop.run_in_executor(
                    self._download_executor,
                    lambda: ydl.extract_info(url, download=True)
                )

                if not info_dict:
                    raise BotError(
                        code=ErrorCode.DOWNLOAD_FAILED,
                        message="Failed to download video",
                        url=url,
                        service=Services.YOUTUBE,
                        critical=True,
                        is_logged=True
                    )

                return [
                    MediaContent(
                        type=MediaType.VIDEO,
                        path=Path(ydl.prepare_filename(info_dict)),
                        width=info_dict.get("width", None),
                        height=info_dict.get("height", None),
                        duration=info_dict.get("duration", None),
                        title=info_dict.get("title", "video"),
                    )
                ]
        except BotError as ebot:
            ebot.service = Services.YOUTUBE
            raise ebot
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"yt-dlp download failed for format {format}: {e}")
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=str(e),
                url=url,
                service=Services.YOUTUBE,
                is_logged=True
            )

    async def download_audio(self, url: str, format: str) -> List[MediaContent]:
        logger.info(f"Starting audio download for URL: {url} with format: {format}")
        options = get_ytdlp_options()
        options["format"] = format
        options["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }]

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                loop = asyncio.get_running_loop()

                info_dict = await loop.run_in_executor(
                    self._download_executor,
                    lambda: ydl.extract_info(url, download=True)
                )
                if not info_dict:
                    raise BotError(
                        code=ErrorCode.DOWNLOAD_FAILED,
                        message="Failed to download audio",
                        service=Services.YOUTUBE,
                        url=url,
                        is_logged=True
                    )

                # Use yt-dlp's prepare_filename to get actual file path
                audio_path = ydl.prepare_filename(info_dict).rsplit('.', 1)[0] + '.mp3'
                base_path = audio_path.rsplit('.', 1)[0]
                thumbnail_path = f"{base_path}.jpg"

                thumbnail_url = info_dict.get("thumbnail", None)
                if thumbnail_url:
                    try:
                        await download_file(thumbnail_url, thumbnail_path)
                    except Exception as e:
                        logger.warning(f"Failed to download thumbnail: {e}")

                await async_update_metadata(
                    audio_path,
                    title=info_dict.get("title", "audio"),
                    artist=info_dict.get("uploader", "unknown"),
                    cover_file=thumbnail_path
                )

                return [MediaContent(
                    type=MediaType.AUDIO,
                    path=Path(audio_path),
                    duration=info_dict.get("duration", 0),
                    title=info_dict.get("title", "audio"),
                    cover=Path(thumbnail_path)
                )]
        except BotError as ebot:
            ebot.service = Services.YOUTUBE
            raise ebot
        except yt_dlp.utils.DownloadError as e:
            logger.error(f"yt-dlp download failed for format {format}: {e}")
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=str(e),
                url=url,
                service=Services.YOUTUBE,
                is_logged=True,
                critical=True
            )
