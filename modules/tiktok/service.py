import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional, Union
import time
from urllib.parse import urlparse, urlunparse

from curl_cffi.requests import AsyncSession
from yt_dlp.utils import sanitize_filename

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata, MetadataType
from models.service_list import Services
from modules.base_service import BaseService
from utils import truncate_string, escape_html, process_video_for_telegram

from .utils import get_tikwm_info

logger = logging.getLogger(__name__)


class TiktokService(BaseService):
    name = "TikTok"
    _download_executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, output_path: str = "storage/temp/", arq=None) -> None:
        super().__init__()
        self.output_path = output_path
        self.arq = arq

    async def download(self, item: Union[str, MediaMetadata]) -> List[MediaContent]:
        metadata: MediaMetadata
        if isinstance(item, str):
            fetched_metadata = await self.get_info(item)
            if not fetched_metadata:
                raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Failed to fetch metadata",
                url=item,
                service=Services.TIKTOK,
                is_logged=True,
                critical=True
            )
            metadata = fetched_metadata
        else:
            metadata = item

        if metadata.media_type == "video":
            return await self._process_video(metadata)
        elif metadata.media_type == "gallery":
            return await self._process_photos(metadata)
        else:
            raise BotError(
            code=ErrorCode.INVALID_URL,
            message="Unsupported media type",
            url=metadata.url,
            service=Services.TIKTOK,
            is_logged=True,
            critical=True
        )

    async def get_info(self, url: str) -> Optional[MediaMetadata]:
        logger.info(f"Getting info for: {url}")
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )
        resolved_url = await self._resolve_url(url)
        parsed = urlparse(resolved_url)
        resolved_url = urlunparse(parsed._replace(query=""))
        logger.debug(f"Resolved URL: {resolved_url}")

        # 1. Fetch data from both sources
        tikwm_info = await get_tikwm_info(resolved_url)
        tikwm_data = tikwm_info.get("data", {}) if tikwm_info and tikwm_info.get("msg") == "success" else {}

        job = await self.arq.enqueue_job(
            "universal_gallery_dl",
            url=resolved_url,
            extract_only=True,
            _queue_name='heavy'
        )
        result = await job.result()

        gallery_data = result.get("items", None)[0]
        if not gallery_data:
            logger.warning(f"Gallery-dl failed for {resolved_url}")
            pass

        # 2. Extract General Metadata (Priority: Gallery-DL)
        author_data = gallery_data.get("author", {}) if gallery_data else tikwm_data.get("author", {})
        author_name = author_data.get("nickname") or author_data.get("uniqueId") or author_data.get("unique_id") or "Unknown"

        description = ""
        if gallery_data:
            description = gallery_data.get("desc") or gallery_data.get("description") or ""
        if not description:
            description = tikwm_data.get("title") or ""
        escaped_description = escape_html(description)

        music_title = "Unknown Title"
        music_author = "Unknown Artist"
        music_cover_url = None
        music_play_url = None

        if gallery_data:
            music_obj = gallery_data.get("music", {})
            music_title = music_obj.get("title") or music_title
            music_author = music_obj.get("authorName") or music_author
            music_cover_url = music_obj.get("coverLarge") or music_obj.get("coverMedium")
            music_play_url = music_obj.get("playUrl")

        # Fallback music info from tikwm if missing
        if music_title == "Unknown Title" and tikwm_data:
            music_info = tikwm_data.get("music_info", {})
            music_title = music_info.get("title") or music_title
            music_author = music_info.get("author") or music_author
            if not music_cover_url:
                music_cover_url = music_info.get("cover")
            if not music_play_url:
                music_play_url = music_info.get("play")

        # 3. Determine Media Type & Content Sources
        is_gallery = False
        image_urls = []

        if gallery_data and ("imagePost" in gallery_data or "images" in gallery_data):
            img_post = gallery_data.get("imagePost", {})
            imgs = img_post.get("images", []) if img_post else gallery_data.get("images", [])

            if imgs:
                is_gallery = True
                for img in imgs:
                    if isinstance(img, dict) and "imageURL" in img:
                        url_list = img["imageURL"].get("urlList", [])
                        if url_list:
                            image_urls.append(url_list[-1])

        if not is_gallery and tikwm_data.get("images"):
            is_gallery = True
            image_urls = tikwm_data.get("images")

        media_type = "gallery" if is_gallery else "video"

        video_url = None
        if media_type == "video":
            video_url = tikwm_data.get("play") or tikwm_data.get("wmplay") or tikwm_data.get("hdplay")
            if not video_url and gallery_data:
                video_info = gallery_data.get("video", {})
                video_url = video_info.get("playAddr") or video_info.get("downloadAddr")

        metadata = MediaMetadata(
            type=MetadataType.METADATA,
            url=resolved_url,
            title=truncate_string(description, 100) if description else "TikTok Media",
            description=escaped_description,
            performer=author_name,
            media_type=media_type,
            extra={
                "video_url": video_url,
                "image_urls": image_urls,
                "music_title": music_title,
                "music_author": music_author,
                "music_cover_url": music_cover_url,
                "music_url": music_play_url,
                "tikwm_data": tikwm_data,
                "gallery_data": gallery_data
            }
        )
        return metadata

    async def _resolve_url(self, url: str) -> str:
        """
        Follows redirects to get the full URL and cleans it.
        """
        try:
            async with AsyncSession(impersonate="chrome136") as session:
                response = await session.head(url, allow_redirects=True)
                if response.status_code >= 400:
                    response = await session.get(url, allow_redirects=True)

                final_url = str(response.url)

                return final_url
        except Exception as e:
            logger.warning(f"Failed to resolve URL {url}: {e}")
            return url

    async def _process_video(self, metadata: MediaMetadata) -> List[MediaContent]:
        logger.info(f"Processing as Video: {metadata.url}")
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )

        download_url = metadata.extra.get("video_url")
        if not download_url:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message="No video URL found",
                url=metadata.url,
                service=Services.TIKTOK,
                is_logged=True,
                critical=True
            )

        video_filename = f"{metadata.performer}_{int(time.time())}.mp4"
        filepath = os.path.join(self.output_path, sanitize_filename(video_filename))

        # Download
        if not download_url.startswith("http"):
            download_url = f"https://www.tikwm.com{download_url}"
        download_url = await self._resolve_url(download_url)

        job = await self.arq.enqueue_job("universal_download", download_url, filepath)
        video_path = await job.result()

        fixed_video, thumbnail, width, height, duration = await process_video_for_telegram(self.arq, video_path)

        if not video_path:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message="Failed to download video file",
                url=metadata.url,
                service=Services.TIKTOK,
                is_logged=True,
                critical=True
            )

        return [
            MediaContent(
                type=MediaType.VIDEO,
                path=Path(fixed_video),
                title=metadata.title,
                performer=metadata.performer,
                width=width,
                height=height,
                duration=int(duration),
                cover=Path(thumbnail)
            )
        ]

    async def _process_photos(self, metadata: MediaMetadata) -> List[MediaContent]:
        logger.info(f"Processing as Photos: {metadata.url}")
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )
        image_urls = metadata.extra.get("image_urls", [])

        if not image_urls:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message="No images found",
                url=metadata.url,
                service=Services.TIKTOK,
                is_logged=True
            )

        image_tasks = []
        base_filename = f"{metadata.performer}_{int(time.time())}"

        for idx, img_url in enumerate(image_urls):
            filename = f"{base_filename}_{idx}.jpg"
            filepath = os.path.join(self.output_path, sanitize_filename(filename))
            image_tasks.append(await self.arq.enqueue_job('universal_download', url=img_url, destination=filepath, _queue_name='light'))

        # Music download
        music_url = metadata.extra.get("music_url")
        music_task = None
        music_cover_task = None

        if music_url:
            music_filename = f"{base_filename}_music.mp3"
            music_filepath = os.path.join(self.output_path, sanitize_filename(music_filename))
            music_task = await self.arq.enqueue_job('universal_download', url=music_url, destination=music_filepath, _queue_name='light')

            music_cover_url = metadata.extra.get("music_cover_url")
            if music_cover_url:
                music_cover_path = os.path.join(self.output_path, sanitize_filename(f"{base_filename}_music_cover.jpg"))
                music_cover_task = await self.arq.enqueue_job('universal_download', url=music_cover_url, destination=music_cover_path, _queue_name='light')

        # Run downloads
        tasks = list(image_tasks)
        if music_task:
            tasks.append(music_task)
        if music_cover_task:
            tasks.append(music_cover_task)

        results = await asyncio.gather(*[job.result() for job in tasks], return_exceptions=True)

        media_contents = []
        num_images = len(image_tasks)
        full_caption = f"{metadata.performer} - {metadata.description}"
        final_caption = truncate_string(full_caption, 1024)

        for i in range(num_images):
            res = results[i]
            if isinstance(res, BaseException):
                logger.error(f"Error downloading image {i}: {res}")
            elif res:
                media_contents.append(
                    MediaContent(
                        type=MediaType.PHOTO,
                        path=Path(res),
                        title=final_caption,
                        performer=metadata.performer
                    )
                )

        if music_task:
            music_res = results[num_images] # After images

            # Check for cover result if it was queued
            final_cover_file = None
            if music_cover_task:
                # Cover task is last if present
                cover_res = results[-1]
                if not isinstance(cover_res, BaseException) and cover_res:
                    final_cover_file = cover_res

            if isinstance(music_res, BaseException):
                logger.error(f"Error downloading music: {music_res}")
            elif music_res:
                music_title = metadata.extra.get("music_title", "Unknown Title")
                music_author = metadata.extra.get("music_author", "Unknown Artist")

                job = await self.arq.enqueue_job(
                    "universal_metadata_update",
                    str(music_res),
                    title=music_title,
                    artist=music_author,
                    cover_file=str(final_cover_file) if final_cover_file else None,
                    _queue_name='heavy'
                )
                await job.result()

                media_contents.append(
                    MediaContent(
                        type=MediaType.AUDIO,
                        path=Path(music_res),
                        title=music_title,
                        performer=music_author,
                        cover=Path(final_cover_file) if final_cover_file else None
                    )
                )

        if not media_contents:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message="Failed to download any content",
                url=metadata.url,
                is_logged=True,
                service=Services.TIKTOK,
            )

        return media_contents
