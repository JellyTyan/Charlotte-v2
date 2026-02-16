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
from modules.base_service import BaseService
from utils import get_extra_audio_options, transliterate
from .utils import get_cover_url, get_song_info, get_playlist_info

logger = logging.getLogger(__name__)

class SoundCloudService(BaseService):
    name = "SoundCloud"
    _download_executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, output_path: str = "storage/temp/", arq = None) -> None:
        super().__init__()
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
        response = await job.result()

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
        result = await job.result()

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
            job = await self.arq.enqueue_job(
                "universal_ytdlp_extract",
                url=meta.url,
                extract_only = False,
                format_selector = None,
                output_template = f"storage/temp/{transliterate(meta.title or str(uuid.uuid4()))}.%(ext)s",
                extra_opts=get_extra_audio_options(),
                extract_audio = True,
                _queue_name='heavy'
            )
            result = await job.result()
            info_dict = result["info"]
            filepath = result["filepath"]

            cover_path = None
            cover_url = get_cover_url(info_dict)

            if cover_url:
                try:
                    cover_path = f"{self.output_path}/{transliterate(meta.title or str(uuid.uuid4()))}.jpg"
                    logger.debug(f"Downloading cover: {cover_url}")
                    job = await self.arq.enqueue_job(
                        "universal_download",
                        url=cover_url,
                        destination=cover_path,
                        _queue_name='light'
                    )
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
            await job.result()

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
