import asyncio
import logging
import os
from pathlib import Path
from typing import List, Optional
import re
from concurrent.futures import ThreadPoolExecutor

import httpx
import yt_dlp

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from modules.base_service import BaseService
from utils import download_file, truncate_string, get_user_agent, get_ytdlp_options
from .utils import sanitize_filename

logger = logging.getLogger(__name__)


class RedditService(BaseService):
    name = "Reddit"
    _download_executor = ThreadPoolExecutor(max_workers=5)

    def __init__(self, output_path: str = "storage/temp") -> None:
        super().__init__()
        self.output_path = output_path

    async def download(self, url: str) -> List[MediaContent]:
        # Extract clean URL using regex pattern
        match = re.match(r'(https://www\.reddit\.com/r/[^/]+/comments/[^/?]+(?:/[^/?]+)?)', url)
        if match:
            url = match.group(1)

        headers = {
            "User-Agent": get_user_agent(),
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://www.reddit.com/",
        }
        async with httpx.AsyncClient(headers=headers, follow_redirects=True) as client:
            try:
                response = await client.get(f"{url.rstrip('/')}.json?limit=1")
                if response.status_code != 200:
                    raise BotError(ErrorCode.INTERNAL_ERROR, "Invalid URL", url, is_logged=True)

                data = response.json()[0]["data"]["children"][0]["data"]
                caption = truncate_string(f"{data.get('author', '')} on {data.get('subreddit_name_prefixed', '')}\n{data.get('title', '')}", 1024)

                result = []
                tasks = []

                # Video post
                if data.get("is_video"):
                    return await self._download_video(url, data, caption)

                # Gallery post
                elif data.get("is_gallery"):
                    self._process_gallery(data, caption, result, tasks, client)

                # Single image or GIF
                elif data.get("post_hint") == "image" or data.get("url", "").endswith((".jpg", ".jpeg", ".png", ".gif")):
                    self._process_single_image(data, caption, result, tasks, client)

                else:
                    raise BotError(ErrorCode.NOT_FOUND, "Unsupported post type or no media found", url, is_logged=True)

                if not result:
                    raise BotError(ErrorCode.NOT_FOUND, "No media found in post", url, is_logged=True)

                await asyncio.gather(*tasks)
                return result

            except BotError:
                raise
            except Exception as e:
                logger.error(f"Error downloading Reddit media: {e}")
                raise BotError(ErrorCode.DOWNLOAD_FAILED, str(e), url, is_logged=True)

    async def _download_video(self, url: str, data: dict, caption: str) -> List[MediaContent]:
        options = get_ytdlp_options()
        options["outtmpl"] = os.path.join(self.output_path, f"{data['id']}.%(ext)s")

        loop = asyncio.get_running_loop()
        with yt_dlp.YoutubeDL(options) as ydl:
            info = await loop.run_in_executor(self._download_executor, lambda: ydl.extract_info(url, download=True))
            if not info:
                raise BotError(ErrorCode.DOWNLOAD_FAILED, "Failed to download video", url, is_logged=True)

            return [MediaContent(
                type=MediaType.VIDEO,
                path=Path(ydl.prepare_filename(info)),
                title=caption,
                performer=data.get("author"),
                width=info.get("width"),
                height=info.get("height")
            )]

    def _process_gallery(self, data: dict, caption: str, result: list, tasks: list, client) -> None:
        media_metadata = data.get("media_metadata", {})
        items = data.get("gallery_data", {}).get("items", [])

        for item in items:
            media_id = item.get("media_id")
            if not media_id or media_id not in media_metadata:
                continue

            meta = media_metadata[media_id]
            source = meta.get("s", {})
            if not source:
                continue

            media_url = None
            ext = "jpg"
            media_type_enum = MediaType.PHOTO

            # AnimatedImage (GIF)
            if meta.get("e") == "AnimatedImage":
                media_url = source.get("mp4") or source.get("gif")
                ext = "mp4" if source.get("mp4") else "gif"
                media_type_enum = MediaType.GIF
            # Regular Image
            else:
                media_url = source.get("u")
                mime = meta.get("m", "")
                if "png" in mime:
                    ext = "png"
                elif "gif" in mime:
                    ext = "gif"

            if not media_url:
                continue

            media_url = media_url.replace("&amp;", "&")
            filename = os.path.join(self.output_path, sanitize_filename(f"{media_id}.{ext}"))
            tasks.append(download_file(media_url, filename, client=client))
            result.append(MediaContent(
                type=media_type_enum,
                path=Path(filename),
                title=caption,
                performer=data.get("author"),
                width=source.get("x"),
                height=source.get("y")
            ))

    def _process_single_image(self, data: dict, caption: str, result: list, tasks: list, client) -> None:
        preview = data.get("preview", {})
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

        # Fallback
        if not img_url:
            img_url = data.get("url_overridden_by_dest") or data.get("url")

        if not img_url:
            raise BotError(ErrorCode.NOT_FOUND, "No media URL found", data.get("url", ""), is_logged=True)

        img_url = img_url.replace("&amp;", "&")
        is_gif = ".gif" in img_url

        # For GIFs, prefer MP4 version
        if is_gif and preview and "images" in preview and preview["images"]:
            mp4_url = preview["images"][0].get("variants", {}).get("mp4", {}).get("source", {}).get("url")
            if mp4_url:
                img_url = mp4_url.replace("&amp;", "&")
                is_gif = False  # MP4 format

        ext = "gif" if is_gif else ("mp4" if ".mp4" in img_url else "jpg")
        filename = os.path.join(self.output_path, sanitize_filename(f"{data['id']}.{ext}"))
        tasks.append(download_file(img_url, filename, client=client))
        result.append(MediaContent(
            type=MediaType.GIF if is_gif else (MediaType.VIDEO if ext == "mp4" else MediaType.PHOTO),
            path=Path(filename),
            title=caption,
            performer=data.get("author"),
            width=width,
            height=height
        ))

    async def get_info(self, url: str) -> Optional[MediaMetadata]:
        return None
