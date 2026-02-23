import asyncio
import logging
import os
import html
from pathlib import Path
from typing import List, Optional
import uuid
from concurrent.futures import ThreadPoolExecutor

from models.service_list import Services

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata, MetadataType, MediaAttachment
from modules.base_service import BaseService
from utils import truncate_string, process_video_for_telegram
from .utils import get_post_info

logger = logging.getLogger(__name__)


class RedditService(BaseService):
    name = "Reddit"
    _download_executor = ThreadPoolExecutor(max_workers=5)

    def __init__(self, output_path: str = "storage/temp", arq = None) -> None:
        super().__init__()
        self.output_path = output_path
        self.arq = arq

    async def get_info(self, url: str) -> Optional[MediaMetadata]:
        info = await get_post_info(url)
        if not info:
            raise BotError(ErrorCode.METADATA_ERROR, message="Failed to get Reddit post info", service=Services.REDDIT, url=url, is_logged=True)
        caption = truncate_string(f"{info.get('author', '')} on {info.get('subreddit_name_prefixed', '')}\n{info.get('title', '')}", 1024)
        has_spoiler = info.get("spoiler", False)
        is_over18 = info.get("over_18", False)

        if info.get("is_self") == True:
            raise BotError(ErrorCode.NOT_FOUND, message="Failed to get Reddit post info", service=Services.REDDIT, url=url, is_logged=False)

        # If post is video
        if info.get("is_video") == True:
            return MediaMetadata(
                type=MetadataType.METADATA,
                url=url,
                media_type="video",
                title=caption,
                extra={
                    "spoiler": has_spoiler or is_over18
                }
            )
        # If post is Gallery with photo and gif
        elif info.get("is_gallery") == True:
            media_type = "gallery"
            media_metadata = info.get("media_metadata", {})
            items = info.get("gallery_data", {}).get("items", [])

            media_items = []

            for item in items:
                media_id = item.get("media_id")
                if not media_id or media_id not in media_metadata:
                    continue

                meta = media_metadata[media_id]
                source = meta.get("s", {})
                if not source:
                    continue

                media_url = None

                if meta.get("e") == "AnimatedImage":
                    media_url = source.get("mp4") or source.get("gif")
                    media_url = html.unescape(media_url)
                    ext = "mp4" if source.get("mp4") else "gif"
                else:
                    media_url = source.get("u")
                    if not media_url:
                        continue

                    media_url = html.unescape(media_url)
                    mime = meta.get("m", "")
                    if "png" in mime:
                        ext = "png"
                    elif "gif" in mime:
                        ext = "gif"
                    else:
                        ext = "jpg"

                media_items.append(MediaAttachment(
                    url=media_url,
                    mime_type=ext
                ))

            return MediaMetadata(
                type=MetadataType.METADATA,
                url=url,
                media_type=media_type,
                title=caption,
                attachments=media_items,
                                extra={
                    "spoiler": has_spoiler or is_over18
                }
            )

        elif info.get("post_hint") == "image":
            media_type = "photo"
            preview = info.get("preview", {})
            img_url = None
            width = height = None

            # Try to get highest quality from preview
            if preview and "images" in preview and preview["images"]:
                resolutions = preview["images"][0].get("resolutions", [])
                if resolutions:
                    highest = resolutions[-1]
                    img_url = highest.get("url")
                    width = highest.get("width")
                    height = highest.get("height")

                if not img_url:
                    source = preview["images"][0].get("source", {})
                    img_url = source.get("url")
                    width = source.get("width")
                    height = source.get("height")

            if not img_url:
                img_url = info.get("url_overridden_by_dest") or info.get("url")

            if not img_url:
                raise BotError(ErrorCode.NOT_FOUND, "No media URL found", info.get("url", ""), is_logged=True)

            img_url = html.unescape(img_url)
            is_gif = ".gif" in img_url

            if is_gif and preview and "images" in preview and preview["images"]:
                media_type = "gif"
                mp4_url = preview["images"][0].get("variants", {}).get("mp4", {}).get("source", {}).get("url")
                if mp4_url:
                    img_url = html.unescape(mp4_url)
                    ext = ".mp4"
                else:
                    ext = ".gif"
            else:
                ext = "." + img_url.split('?')[0].split('.')[-1]

            return MediaMetadata(
                type=MetadataType.METADATA,
                url=img_url,
                title=caption,
                width=width,
                height=height,
                media_type=media_type,
                extra={
                    "file_type": ext,
                    "spoiler": has_spoiler or is_over18
                }
            )

        return None

    async def download(self, meta: MediaMetadata) -> List[MediaContent]:
        media_contents = []
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )
        try:
            if isinstance(meta, str):
                raise BotError(ErrorCode.INVALID_URL, message="Invalid metadata format", url=meta, is_logged=True)

            if meta.media_type == "gallery" and meta.attachments:
                download_tasks = []

                for item in meta.attachments:
                    filepath = f"{self.output_path}/{uuid.uuid4()}.{item.mime_type}"
                    job = await self.arq.enqueue_job(
                        'universal_download',
                        url=item.url,
                        destination=filepath,
                        headers={"Accept": "image/avif,image/apng,image/svg+xml,image/*,*/*;q=0.8"},
                        _queue_name='light'
                    )
                    download_tasks.append(job)

                results = await asyncio.gather(*[job.result() for job in download_tasks], return_exceptions=True)

                media_contents = []
                for i, res in enumerate(results):
                    if isinstance(res, BaseException):
                        logger.error(f"Error downloading Reddit item {i}: {res}")
                        continue

                    if res and os.path.exists(str(res)):
                        path_obj = Path(res)
                        ext = path_obj.suffix.lower()
                        m_type = MediaType.PHOTO if ext == '.jpg' or ext == ".png" else MediaType.GIF

                        media_contents.append(MediaContent(
                            type=m_type,
                            path=path_obj,
                            title=meta.title,
                            is_blured=meta.extra.get('spoiler', False)
                        ))

                return media_contents

            elif meta.media_type == "video":
                job = await self.arq.enqueue_job(
                    "universal_ytdlp_extract",
                    meta.url,
                    extract_only=False,
                    output_template=os.path.join(self.output_path, f"{uuid.uuid4()}.%(ext)s"),
                    _queue_name='heavy'
                )
                result_data = await job.result()
                downloaded_path = result_data.get("filepath")
                fixed_video, thumbnail, width, height, duration = await process_video_for_telegram(self.arq, downloaded_path)

                return [MediaContent(
                    type=MediaType.VIDEO,
                    path=Path(fixed_video),
                    title=meta.title,
                    width=width,
                    height=height,
                    is_blured=meta.extra.get('spoiler', False),
                    cover=Path(thumbnail),
                    duration=int(duration)
                )]

            elif meta.media_type == "photo" or meta.media_type == "gif":
                file_ext = meta.extra.get('file_type')
                filename = os.path.join(self.output_path, f"{uuid.uuid4()}.{file_ext}")
                job = await self.arq.enqueue_job(
                    'universal_download',
                    url=meta.url,
                    destination=filename,
                    headers={"Accept": "image/avif,image/apng,image/svg+xml,image/*,*/*;q=0.8"},
                    _queue_name='light'
                )
                result = await job.result()

                if not result or not os.path.exists(str(result)):
                    raise BotError(ErrorCode.DOWNLOAD_FAILED, message="Failed to download media file", url=meta.url, is_logged=True)

                m_type = MediaType.GIF if meta.media_type == "gif" else MediaType.PHOTO

                return [MediaContent(
                    type=m_type,
                    path=Path(result),
                    title=meta.title,
                    width=meta.width,
                    height=meta.height,
                    is_blured=meta.extra.get('spoiler', False)
                )]
            else:
                raise BotError(ErrorCode.NOT_FOUND, message="Unsupported media type", service=Services.REDDIT, url=meta.url, is_logged=True)

        except BotError:
            raise
        except Exception as e:
            logger.error(f"Error downloading Reddit media: {e}")
            raise BotError(ErrorCode.DOWNLOAD_FAILED, message=str(e), url=meta.url, is_logged=True)
