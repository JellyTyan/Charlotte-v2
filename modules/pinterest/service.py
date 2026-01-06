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
from utils import download_file
from .utils import get_pin_info, download_photo, download_m3u8_video

logger = logging.getLogger(__name__)


class PinterestService(BaseService):
    name = "Pinterest"

    def __init__(self, output_path: str = "storage/temp/pinterest") -> None:
        super().__init__()
        self.output_path = output_path
        os.makedirs(self.output_path, exist_ok=True)

    async def download(self, url: str) -> List[MediaContent]:
        result = []

        async with httpx.AsyncClient(follow_redirects=True) as client:
            try:
                response = await client.get(url)
                url = str(response.url)

                match = re.search(r"/pin/(\d+)", url)
                if not match:
                    raise BotError(
                        code=ErrorCode.INVALID_URL,
                        message="Failed to extract post_id from URL",
                        url=url,
                        is_logged=False,
                    )

                post_id = int(match.group(1))
                post_dict = await get_pin_info(post_id, client)

                image_signature = post_dict["image_signature"]
                title = post_dict["title"]

                if post_dict["ext"] == "mp4":
                    video_url = post_dict["video"]
                    filename = os.path.join(self.output_path, f"{image_signature}.mp4")

                    if video_url.endswith(".m3u8"):
                        await download_m3u8_video(video_url, filename)
                    else:
                        await download_file(video_url, filename, client=client)

                    result.append(MediaContent(
                        type=MediaType.VIDEO,
                        path=Path(filename),
                        title=title,
                        original_size=True
                    ))

                elif post_dict["ext"] == "carousel":
                    carousel_data = post_dict["carousel_data"]
                    for i, image_url in enumerate(carousel_data):
                        filename = os.path.join(
                            self.output_path, f"{image_signature}_{i}.jpg"
                        )
                        await download_photo(image_url, filename, client)
                        result.append(MediaContent(
                            type=MediaType.PHOTO,
                            path=Path(filename),
                            title=title,
                            original_size=True
                        ))

                elif post_dict["ext"] == "jpg":
                    image_url = post_dict["image"]

                    if image_url.endswith(".gif"):
                        filename = os.path.join(self.output_path, f"{image_signature}.gif")
                        await download_file(image_url, filename, client=client)
                        result.append(MediaContent(
                            type=MediaType.GIF,
                            path=Path(filename),
                            original_size=True
                        ))
                    else:
                        filename = os.path.join(self.output_path, f"{image_signature}.jpg")
                        await download_photo(image_url, filename, client)
                        result.append(MediaContent(
                            type=MediaType.PHOTO,
                            path=Path(filename),
                            title=title,
                            original_size=True
                        ))

                else:
                    raise BotError(
                        code=ErrorCode.DOWNLOAD_FAILED,
                        message=f"Unsupported file type: {post_dict['ext']}",
                        url=url,
                        is_logged=True,
                    )

                return result

            except BotError:
                raise
            except Exception as e:
                logger.error(f"Error downloading Pinterest media: {str(e)}")
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message=str(e),
                    url=url,
                    is_logged=True
                )

    async def get_info(self, url: str) -> Optional[MediaMetadata]:
        return None
