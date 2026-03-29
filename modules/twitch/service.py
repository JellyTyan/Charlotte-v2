import logging
import os
from pathlib import Path
from typing import List, Union

from yt_dlp.utils import sanitize_filename

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata, MetadataType
from models.service_list import Services
from modules.base_service import BaseService
from utils import process_video_for_telegram, escape_html, truncate_string

logger = logging.getLogger(__name__)


class TwitchService(BaseService):
    name = "Twitch"

    def __init__(self, output_path: str = "storage/temp/", arq=None) -> None:
        super().__init__()
        self.output_path = output_path
        self.arq = arq

    async def download(self, url: Union[str, MediaMetadata], **kwargs) -> List[MediaContent]:
        """Download Twitch clip directly via yt-dlp heavy worker (format=best)."""
        if isinstance(url, MediaMetadata):
            url = url.url

        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True,
            )

        logger.info(f"Downloading Twitch clip: {url}")

        output_template = os.path.join(
            self.output_path,
            f"%(id)s_{sanitize_filename('%(title)s')}.%(ext)s",
        )

        job = await self.arq.enqueue_job(
            "universal_ytdlp_extract",
            url=url,
            extract_only=False,
            format_selector="best",
            output_template=output_template,
            _queue_name="heavy",
        )
        try:
            result = await job.result()
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                service=Services.TWITCH,
                message=f"Failed to download Twitch clip: {e}",
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
                service=Services.TWITCH,
                is_logged=True,
                critical=True,
            )

        fixed_video, thumbnail, width, height, duration = await process_video_for_telegram(
            self.arq, filepath
        )

        title = truncate_string(
            escape_html(clean_info.get("title") or "Twitch Clip") if clean_info else "Twitch Clip",
            100,
        )
        performer = (clean_info.get("uploader") or clean_info.get("channel") or "Twitch") if clean_info else "Twitch"

        return [
            MediaContent(
                type=MediaType.VIDEO,
                path=Path(fixed_video),
                title=title,
                performer=performer,
                width=width,
                height=height,
                duration=int(duration),
                cover=Path(thumbnail) if thumbnail else None,
            )
        ]

    async def get_info(self, url: str, **kwargs) -> MediaMetadata | None:
        """Not used — TwitchService downloads directly in download()."""
        return MediaMetadata(
            type=MetadataType.METADATA,
            url=url,
            media_type="video",
        )
