import asyncio
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Tuple, Optional

import instaloader

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from modules.base_service import BaseService
from utils import truncate_string, random_cookie_file
from models.service_list import Services

logger = logging.getLogger(__name__)


class InstagramService(BaseService):
    name = "Instagram"
    _download_executor = ThreadPoolExecutor(max_workers=5)

    # Path to instaloader session file (usually "session-yourusername")
    # Created via command: instaloader -l username
    SESSION_FILE_PATH = "session-charlottelopster"

    def __init__(self, output_path: str = "storage/temp", arq = None) -> None:
        super().__init__()
        self.output_path = output_path
        self.arq = arq

        self.L = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            iphone_support=True
        )

        self._load_session()

    def _load_session(self):
        """Load session for accessing 18+ and private content if available."""
        if os.path.exists(self.SESSION_FILE_PATH):
            try:
                # Load session from file.
                # Filename format is usually "session-username"
                username = self.SESSION_FILE_PATH.replace("session-", "")
                self.L.load_session_from_file(username=username, filename=self.SESSION_FILE_PATH)
                logger.info(f"Instagram session loaded for {username} from {self.SESSION_FILE_PATH}")
            except Exception as e:
                logger.error(f"Failed to load Instagram session: {e}")
        else:
            logger.warning(f"Instagram session file not found at {self.SESSION_FILE_PATH}")

    async def download(self, url: str) -> List[MediaContent]:
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )
        try:
            # 1. Get direct links via Instaloader
            try:
                media_items, filenames, caption, author = await self._get_post_metadata(url)
            except Exception as e:
                logger.warning(f"Instaloader failed for {url}: {e}. Trying fallback to yt-dlp...")
                return await self._process_fallback_ytdlp(url)

            # 2. Download files using project utility
            download_tasks = []
            for link, name in zip(media_items, filenames):
                filepath = os.path.join(self.output_path, name)
                download_tasks.append(await self.arq.enqueue_job('universal_download', url=link, destination=filepath, _queue_name='light'))

            results = await asyncio.gather(*[job.result() for job in download_tasks], return_exceptions=True)

            media_contents = []
            for i, res in enumerate(results):
                if isinstance(res, BaseException):
                    logger.error(f"Error downloading instagram item {i}: {res}")
                    continue

                if res and os.path.exists(str(res)):
                    path_obj = Path(res)
                    ext = path_obj.suffix.lower()
                    m_type = MediaType.VIDEO if ext == '.mp4' else MediaType.PHOTO

                    media_contents.append(MediaContent(
                        type=m_type,
                        path=path_obj,
                        title=truncate_string(caption, 1024),
                        performer=author
                    ))

            if not media_contents:
                 raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    service=Services.INSTAGRAM,
                    message="Failed to download any media files",
                    url=url
                )

            return media_contents

        except BotError as e:
            raise e
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Instagram error: {e}",
                url=url,
                is_logged=True,
            )

    async def _get_post_metadata(self, url: str) -> Tuple[List[str], List[str], str, str]:
        pattern = r'https://www\.instagram\.com/(?:p|reel|tv)/([A-Za-z0-9_-]+)'
        match = re.search(pattern, url)
        if match:
            shortcode = match.group(1)
        else:
            # Try to handle stories if needed, or just throw error for now as regex above is strictly posts
            raise BotError(ErrorCode.INVALID_URL, message="Invalid Instagram URL", service=Services.INSTAGRAM, url=url, is_logged=False)

        loop = asyncio.get_running_loop()

        try:
            post = await loop.run_in_executor(
                self._download_executor,
                lambda: instaloader.Post.from_shortcode(self.L.context, shortcode)
            )
        except Exception as e:
            raise BotError(ErrorCode.INVALID_URL, message=f"Post not found or private: {e}", service=Services.INSTAGRAM, url=url, is_logged=True)

        images_urls = []
        filenames = []

        # Logic for types
        if post.typename == 'GraphSidecar':
            # Carousel
            for i, node in enumerate(post.get_sidecar_nodes(), start=1):
                if node.is_video:
                    images_urls.append(node.video_url)
                    filenames.append(f"{shortcode}_{i}.mp4")
                else:
                    images_urls.append(node.display_url)
                    filenames.append(f"{shortcode}_{i}.jpg")

        elif post.is_video:
            # Reels or Video
            images_urls.append(post.video_url)
            filenames.append(f"{shortcode}.mp4")

        else:
            # Photo
            images_urls.append(post.url)
            filenames.append(f"{shortcode}.jpg")

        caption = post.caption or ""
        author = post.owner_username or "Instagram User"

        return images_urls, filenames, caption, author

    async def _process_fallback_ytdlp(self, url: str) -> List[MediaContent]:
        logger.info(f"Fallback processing with yt-dlp: {url}")
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
                url,
                extract_only = False,
                format_selector = None,
                output_template = f"{self.output_path}/%(id)s_%(title)s.%(ext)s",
                cookies_file = random_cookie_file("instagram"),
                _queue_name='heavy'
            )

            result = await job.result()
            path = Path(result['path'])
            info = result['info']

            author = info.get("uploader", "Unknown")
            description = info.get("description", "") or ""
            final_caption = truncate_string(f"{author} - {description}", 1024)

            return [
                MediaContent(
                    type=MediaType.VIDEO if info.get('ext') == 'mp4' else MediaType.PHOTO,
                    path=path,
                    title=final_caption,
                    performer=author
                )
            ]
        except Exception as e:
            raise BotError(
                ErrorCode.DOWNLOAD_FAILED,
                service=Services.INSTAGRAM,
                message=f"All methods failed. yt-dlp error: {e}",
                critical=True,
                is_logged=True
                )

    async def get_info(self, url: str) -> Optional[MediaMetadata]:
        return None
