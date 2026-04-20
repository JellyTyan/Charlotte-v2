import logging
import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List
from aiofiles import os as aios

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from models.service_list import Services
from utils import get_extra_audio_options, transliterate, sanitize_filename
from .utils import get_cover_url, get_song_info, get_playlist_info

logger = logging.getLogger(__name__)

class SoundCloudService:
    name = "SoundCloud"
    _download_executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, output_path: str = "storage/temp/", arq = None) -> None:
        self.output_path = output_path
        self.arq = arq

    async def get_info(self, url: str, *args, **kwargs) -> MediaMetadata|None:
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )

        job = await self.arq.enqueue_job("universal_http_request", url = url, method="GET")
        try:
            response = await job.result()
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                service=Services.SOUNDCLOUD,
                message=f"Failed to fetch SoundCloud page: {e}",
                url=url,
                is_logged=True
            )

        status_code = response["status_code"]
        if status_code != 200:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"HTTP {status_code}",
                service=Services.SOUNDCLOUD,
                url=url,
                is_logged=True
            )

        response_text = response["text"]

        job = await self.arq.enqueue_job(
            "universal_html_parse",
            html_content = response_text,
            selectors={
                "track_id": 'meta[property="twitter:app:url:googleplay"]'
            },
            extract_type="attr",
            attribute="content",
        )
        try:
            result = await job.result()
        except Exception as e:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                service=Services.SOUNDCLOUD,
                message=f"Failed to parse SoundCloud HTML: {e}",
                url=url,
                critical=True,
                is_logged=True
            )

        raw_link_list = result.get("track_id")

        if raw_link_list and len(raw_link_list) > 0:
            raw_link = raw_link_list[0]
            match = re.search(r'soundcloud://([a-z]+):(\d+)', raw_link)
            if not match:
                raise BotError(
                    code=ErrorCode.INTERNAL_ERROR,
                    url=url,
                    message="Failed to parse track ID",
                    service=Services.SOUNDCLOUD,
                    critical=True,
                    is_logged=True
                )
            sc_type = match.group(1)
            sc_id = match.group(2)
        else:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                url=url,
                message="Failed to get track ID",
                service=Services.SOUNDCLOUD,
                critical=True,
                is_logged=True
            )

        if sc_type == "sounds":
            return await get_song_info(int(sc_id))
        elif sc_type == "playlists":
            return await get_playlist_info(int(sc_id))
        else:
            raise BotError(
                code=ErrorCode.NOT_FOUND,
                url=url,
                message="Unsupported SoundCloud type",
                service=Services.SOUNDCLOUD,
                critical=False,
                is_logged=True
            )

    async def download(self, meta: MediaMetadata) -> List[MediaContent]:
        logger.debug(f"Starting download for: {meta.url}")
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )
        try:
            safe_title = sanitize_filename(transliterate(meta.title or str(uuid.uuid4())))
            job = await self.arq.enqueue_job(
                "universal_ytdlp_extract",
                url=meta.url,
                extract_only = False,
                format_selector = None,
                output_template = f"storage/temp/{safe_title}.%(ext)s",
                extra_opts=get_extra_audio_options(),
                extract_audio = True,
                _queue_name='heavy'
            )
            try:
                result = await job.result()
            except Exception as e:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    service=Services.SOUNDCLOUD,
                    message=f"Failed to download audio: {e}",
                    url=meta.url,
                    critical=True,
                    is_logged=True
                )
            info_dict = result["info"]
            filepath = result["filepath"]

            cover_path = None
            cover_url = get_cover_url(info_dict)

            if cover_url:
                safe_cover_name = sanitize_filename(transliterate(meta.title or str(uuid.uuid4())))
                cover_path = f"{self.output_path}/{safe_cover_name}.jpg"
                logger.debug(f"Downloading cover: {cover_url}")
                job = await self.arq.enqueue_job(
                    "universal_download",
                    url=cover_url,
                    destination=cover_path,
                    _queue_name='light'
                )
                try:
                    await job.result()
                except Exception as e:
                    logger.warning(f"Failed to download cover: {e}")
                    cover_path = None

            logger.debug("Updating metadata")
            job = await self.arq.enqueue_job(
                "universal_metadata_update",
                filepath,
                title=meta.title,
                artist=meta.performer,
                cover_file=cover_path,
                _queue_name='heavy'
            )
            try:
                await job.result()
            except Exception as e:
                logger.error(f"Failed to update metadata: {e}")
                # Not critical since the file is already downloaded

            if await aios.path.exists(filepath):
                logger.debug(f"Download completed: {filepath}")
                cover_file = None
                if cover_path and await aios.path.exists(cover_path):
                    cover_file = Path(cover_path)
                return [MediaContent(
                    type=MediaType.AUDIO,
                    path=Path(filepath),
                    duration=int(info_dict.get("duration", 0)) if info_dict.get("duration") else None,
                    title=meta.title,
                    performer=meta.performer,
                    cover=cover_file
                )]
            else:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message="Audio file not found after download",
                    url=meta.url,
                    service=Services.SOUNDCLOUD,
                    is_logged=True,
                )

        except BotError:
            raise
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Error downloading SoundCloud Audio: {e}",
                url=meta.url,
                service=Services.SOUNDCLOUD,
                critical=True,
                is_logged=True
            )
