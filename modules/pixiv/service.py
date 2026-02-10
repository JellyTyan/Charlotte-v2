import asyncio
import logging
import os
import re
from pathlib import Path
from typing import List, Optional

from curl_cffi.requests import AsyncSession

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from models.service_list import Services
from modules.base_service import BaseService
from utils import escape_html, get_user_agent

logger = logging.getLogger(__name__)


class PixivService(BaseService):
    name = "Pixiv"

    def __init__(self, output_path: str = "storage/temp/", arq=None) -> None:
        super().__init__()
        self.output_path = output_path
        self.arq = arq

    async def download(self, url: str) -> List[MediaContent]:
        logger.debug(f"Starting Pixiv download for URL: {url}")

        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )

        # Extract pixiv ID
        match = re.search(r'pixiv\.net/.*/artworks/(\d+)', url)
        if not match:
            raise BotError(ErrorCode.INVALID_URL, message="Invalid Pixiv URL", service=Services.PIXIV, url=url, is_logged=True)

        pixiv_id = match.group(1)
        logger.debug(f"Extracted Pixiv ID: {pixiv_id}")

        headers = {
            "Accept": "application/json",
            "Referer": "https://www.pixiv.net/",
            "User-Agent": get_user_agent(),
        }

        async with AsyncSession(impersonate="chrome136") as session:
            try:
                # Get artwork info
                logger.debug(f"Fetching artwork info for ID: {pixiv_id}")
                response = await session.get(
                    f"https://www.pixiv.net/ajax/illust/{pixiv_id}",
                    headers=headers,
                    allow_redirects=True
                )
                if response.status_code != 200:
                    raise BotError(ErrorCode.NOT_FOUND, message="Artwork not found", service=Services.PIXIV, url=url, is_logged=True)

                info = response.json()
                title = info.get("body", {}).get("illustTitle", "")
                logger.debug(f"Artwork title: {title}")

                # Get pages info
                logger.debug(f"Fetching pages info for ID: {pixiv_id}")
                response = await session.get(
                    f"https://www.pixiv.net/ajax/illust/{pixiv_id}/pages",
                    headers=headers,
                    allow_redirects=True
                )
                if response.status_code != 200:
                    raise BotError(ErrorCode.NOT_FOUND, message="Failed to retrieve pages", service=Services.PIXIV, url=url, is_logged=True)

                pages = response.json().get("body", [])
                if not pages:
                    raise BotError(ErrorCode.NOT_FOUND, message="No images found", service=Services.PIXIV, url=url, is_logged=True)

                logger.debug(f"Found {len(pages)} page(s)")

                result = []
                download_jobs = []

                for i, page in enumerate(pages):
                    img_url = page.get("urls", {}).get("original")
                    if not img_url:
                        logger.warning(f"No original URL for page {i}")
                        continue

                    filename = os.path.join(self.output_path, img_url.split("/")[-1])
                    logger.debug(f"Enqueueing download for page {i}: {img_url}")

                    # Enqueue ARQ download job
                    job = await self.arq.enqueue_job(
                        "universal_download",
                        img_url,
                        filename,
                        headers=headers,
                        _queue_name='light'
                    )
                    download_jobs.append(job)

                    result.append(MediaContent(
                        type=MediaType.PHOTO,
                        path=Path(filename),
                        title=escape_html(title),
                        original_size=True
                    ))

                # Wait for all downloads to complete
                logger.debug(f"Waiting for {len(download_jobs)} download(s) to complete")
                await asyncio.gather(*[job.result() for job in download_jobs])

                logger.debug(f"Pixiv download completed: {len(result)} images")
                return result

            except BotError:
                raise
            except Exception as e:
                logger.error(f"Error downloading Pixiv media: {e}")
                raise BotError(ErrorCode.DOWNLOAD_FAILED, message=str(e), service=Services.PIXIV, url=url, is_logged=True)

    async def get_info(self, url: str) -> Optional[MediaMetadata]:
        return None
