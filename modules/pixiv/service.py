import asyncio
import logging
import os
import re
from pathlib import Path
from typing import List, Optional

import httpx

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from modules.base_service import BaseService
from utils import download_file, get_user_agent

logger = logging.getLogger(__name__)


class PixivService(BaseService):
    name = "Pixiv"

    def __init__(self, output_path: str = "storage/temp") -> None:
        super().__init__()
        self.output_path = output_path

    async def download(self, url: str) -> List[MediaContent]:
        # Extract pixiv ID
        match = re.search(r'pixiv\.net/.*/artworks/(\d+)', url)
        if not match:
            raise BotError(ErrorCode.INVALID_URL, "Invalid Pixiv URL", url, is_logged=True)
        
        pixiv_id = match.group(1)
        
        headers = {
            "Accept": "application/json",
            "Referer": "https://www.pixiv.net/",
            "User-Agent": get_user_agent(),
        }
        
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            try:
                # Get artwork info
                response = await client.get(f"https://www.pixiv.net/ajax/illust/{pixiv_id}")
                if response.status_code != 200:
                    raise BotError(ErrorCode.NOT_FOUND, "Artwork not found", url, is_logged=True)
                
                info = response.json()
                title = info.get("body", {}).get("illustTitle", "")
                
                # Get pages info
                response = await client.get(f"https://www.pixiv.net/ajax/illust/{pixiv_id}/pages")
                if response.status_code != 200:
                    raise BotError(ErrorCode.NOT_FOUND, "Failed to retrieve pages", url, is_logged=True)
                
                pages = response.json().get("body", [])
                if not pages:
                    raise BotError(ErrorCode.NOT_FOUND, "No images found", url, is_logged=True)
                
                result = []
                tasks = []
                
                for page in pages:
                    img_url = page.get("urls", {}).get("original")
                    if not img_url:
                        continue
                    
                    filename = os.path.join(self.output_path, img_url.split("/")[-1])
                    tasks.append(download_file(img_url, filename, client=client, headers=headers))
                    result.append(MediaContent(
                        type=MediaType.PHOTO,
                        path=Path(filename),
                        title=title,
                        original_size=True
                    ))
                
                await asyncio.gather(*tasks)
                return result
                
            except BotError:
                raise
            except Exception as e:
                logger.error(f"Error downloading Pixiv media: {e}")
                raise BotError(ErrorCode.DOWNLOAD_FAILED, str(e), url, is_logged=True)

    async def get_info(self, url: str) -> Optional[MediaMetadata]:
        return None
