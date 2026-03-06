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
from modules.base_service import BaseService
from utils import truncate_string, process_video_for_telegram
from .utils import get_post_info, sanitize_filename
from models.service_list import Services

logger = logging.getLogger(__name__)


class BlueSkyService(BaseService):
    name = "Twitter"

    def __init__(self, output_path: str = "storage/temp", arq = None) -> None:
        super().__init__()
        self.output_path = output_path
        self.arq = arq

    async def download(self, url: str, allow_nsfw: Optional[bool] = True) -> List[MediaContent]:
        data_pattern = r"https:\/\/bsky\.app\/profile\/(?P<username>[^\/]+)\/post\/(?P<post_id>[a-z0-9]+)"
        result = []
        match = re.match(data_pattern, url)
        if match:
            username = match.group("username")
            post_id = match.group("post_id")
        else:
            raise BotError(ErrorCode.INVALID_URL, service=Services.BLUESKY, message="Invalid URL", is_logged=True)

        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )

        async with AsyncSession(impersonate="chrome136") as client:
            try:
                post_dict = await get_post_info(post_id, username, client)

                first_item = post_dict.get("thread", [])[0]
                post = first_item.get("value", {}).get("post", {})
                embed = post.get("embed", {})
                record = post.get("record", {})
                title = record.get("text")

                tasks = []
                if embed.get("$type") == "app.bsky.embed.images#view":
                    images = embed.get("images", [])

                    for image in images:
                        image_url = image.get("fullsize")

                        photo_id_pattern = r'/([^/]+)@jpeg$'
                        match = re.search(photo_id_pattern, image_url)
                        if match:
                            photo_id = match.group(1)
                        else:
                            raise BotError(ErrorCode.INVALID_URL)

                        safe_filename = sanitize_filename(os.path.basename(photo_id))
                        filename = os.path.join(self.output_path, f"{safe_filename}.jpg")

                        tasks.append(await self.arq.enqueue_job('universal_download', url=image_url, destination=filename,_queue_name='light'))
                        result.append(MediaContent(
                            type=MediaType.PHOTO,
                            path=Path(filename),
                            title=truncate_string(f"{username} on BlueSky - {title}"),
                        ))
                    
                    if tasks:
                        await asyncio.gather(*[job.result() for job in tasks], return_exceptions=True)
                elif embed.get("$type") == "app.bsky.embed.video#view":
                    video_url = embed.get("playlist")
                    safe_filename = sanitize_filename(os.path.basename(f"{username}_{post_id}"))
                    filename = os.path.join(self.output_path, f"{safe_filename}.mp4")
                    # Ensure path stays within output directory
                    if not os.path.abspath(filename).startswith(os.path.abspath(self.output_path)):
                        raise BotError(ErrorCode.INVALID_URL, message="Invalid file path")

                    job = await self.arq.enqueue_job('universal_ytdlp_extract', url=video_url, output_template=filename,extract_only=False, _queue_name='heavy')
                    job_result = await job.result()

                    fixed_video, thumbnail, width, height, duration = await process_video_for_telegram(self.arq, job_result['filepath'])

                    result.append(
                        MediaContent(
                            type=MediaType.VIDEO,
                            path=Path(fixed_video),
                            title=truncate_string(f"{username} on BlueSky - {title}"),
                            cover=Path(thumbnail),
                            width=width,
                            height=height,
                            duration=int(duration)
                        )
                    )
                else:
                    raise BotError(ErrorCode.NOT_FOUND, message="No video or image found in post", is_logged=True)

            except BotError as e:
                raise e
            except Exception as e:
                logger.error(f"Error downloading BlueSky video: {str(e)}")
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message=str(e),
                    url=url,
                    critical=True,
                    is_logged=True,
                )
            return result

    async def get_info(self, url: str) -> Optional[MediaMetadata]:
        return None
