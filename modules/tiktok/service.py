import asyncio
import logging
import os
import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List, Optional

import httpx
import yt_dlp
from yt_dlp.utils import sanitize_filename

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from modules.base_service import BaseService
from utils import download_file, truncate_string, update_metadata

from .utils import get_ytdlp_options, get_gallery_dl_info

logger = logging.getLogger(__name__)


class TiktokService(BaseService):
    name = "TikTok"
    _download_executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, output_path: str = "storage/temp/") -> None:
        super().__init__()
        self.output_path = output_path

    async def download(self, url: str) -> List[MediaContent]:
        expanded_url = await self._resolve_url(url)
        logger.info(f"Resolved URL: {url} -> {expanded_url}")

        if "/photo/" in expanded_url:
            return await self._process_photos(expanded_url)
        else:
            return await self._process_video(expanded_url)

    async def _resolve_url(self, url: str) -> str:
        """
        Follows redirects to get the full URL.
        """
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.head(url)
                if response.status_code >= 400:
                    response = await client.get(url)
                return str(response.url)
        except Exception as e:
            logger.warning(f"Failed to resolve URL {url}: {e}")
            return url

    async def _process_video(self, url: str) -> List[MediaContent]:
        logger.info(f"Processing as Video: {url}")

        options = get_ytdlp_options()
        options["outtmpl"] = f"{self.output_path}/%(id)s_%(title)s.%(ext)s"

        with yt_dlp.YoutubeDL(options) as ydl:
            loop = asyncio.get_running_loop()

            info = await loop.run_in_executor(
                self._download_executor,
                lambda: ydl.extract_info(url, download=True)
            )

            if not info:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message="Failed to download video",
                    url=url,
                    is_logged=True
                )

            video_path = Path(ydl.prepare_filename(info))

            author = info.get("uploader", "Unknown")
            description = info.get("description", "") or ""
            full_caption = f"{author} - {description}"
            final_caption = truncate_string(full_caption, 1024)

            return [
                MediaContent(
                    type=MediaType.VIDEO,
                    path=video_path,
                    width=info.get("width"),
                    height=info.get("height"),
                    duration=info.get("duration"),
                    title=final_caption,
                    performer=author
                )
            ]

    async def _process_photos(self, url: str) -> List[MediaContent]:
        logger.info(f"Processing as Photos: {url}")

        info_list = await get_gallery_dl_info(url)
        if not info_list:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Failed to get photo info from gallery-dl",
                url=url,
                is_logged=True
            )

        first_item = info_list[0] if isinstance(info_list, list) and info_list else {}

        if isinstance(first_item, list):
            for item in info_list:
                if isinstance(item, (list, tuple)) and len(item) > 1 and isinstance(item[1], dict) and "author" in item[1]:
                    first_item = item[1]
                    break
                elif isinstance(item, dict) and "author" in item:
                    first_item = item
                    break

        if not isinstance(first_item, dict):
            logger.warning(f"Could not find valid metadata dict in info_list: {info_list[:1]}")
            first_item = {}

        author_data = first_item.get("author", {})
        author = author_data.get("nickname") or author_data.get("uniqueId") or "Unknown"
        description = first_item.get("desc") or first_item.get("description") or ""

        full_caption = f"{author} - {description}"
        final_caption = truncate_string(full_caption, 1024)

        image_tasks = []
        base_id = first_item.get("id", "unknown_id")

        images_list = first_item.get("imagePost", {}).get("images", [])

        if not images_list:
            images_list = first_item.get("images", [])

        if images_list:
            for idx, img_data in enumerate(images_list):
                url_list = img_data.get("imageURL", {}).get("urlList", [])
                target_url = url_list[-1] if url_list else None

                if target_url:
                    filename = f"{base_id}_{idx}.jpg"
                    filepath = os.path.join(self.output_path, sanitize_filename(filename))

                    image_tasks.append(
                        download_file(target_url, filepath)
                    )

        if not image_tasks:
            logger.warning("No images found in TikTok post.")

        music_task = None
        music_data = first_item.get("music", {})
        play_url = music_data.get("playUrl")

        if music_data:
            logger.info(f"Found music metadata: Title='{music_data.get('title')}', Author='{music_data.get('authorName')}', PlayUrl='{play_url}'")
        else:
            logger.warning("No 'music' key found in metadata.")

        if play_url:
            music_title = music_data.get("title", "Unknown Title")
            music_author = music_data.get("authorName", "Unknown Artist")
            music_cover_url = music_data.get("coverLarge") or music_data.get("coverMedium")
            music_duration = music_data.get("duration", 0)

            music_filename = f"{base_id}_music.mp3"
            music_filepath = os.path.join(self.output_path, sanitize_filename(music_filename))
            music_cover_path = os.path.join(self.output_path, sanitize_filename(f"{base_id}_music_cover.jpg"))

            music_task = self._download_and_process_music(
                play_url, music_filepath, music_cover_url, music_cover_path, music_title, music_author, music_duration
            )
        else:
            logger.warning("No 'playUrl' found for music, skipping download.")

        tasks = list(image_tasks)
        if music_task:
            tasks.append(music_task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        media_contents = []

        num_images = len(image_tasks)
        for i in range(num_images):
            res = results[i]
            if isinstance(res, BaseException):
                logger.error(f"Error downloading image {i}: {res}")
            elif res:
                media_contents.append(
                    MediaContent(
                        type=MediaType.PHOTO,
                        path=res,
                        title=final_caption,
                        performer=author
                    )
                )

        if music_task:
            music_res = results[num_images]
            if isinstance(music_res, BaseException):
                logger.error(f"Error downloading music: {music_res}")
            elif music_res:
                media_contents.append(music_res)

        if not media_contents:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message="Failed to download any content",
                url=url
            )

        return media_contents

    async def _download_and_process_music(
        self,
        url: str,
        filepath: str,
        cover_url: str,
        cover_path: str,
        title: str,
        artist: str,
        duration: int = 0
    ) -> Optional[MediaContent]:
        try:
            audio_path = await download_file(url, filepath)
            if not audio_path or not os.path.exists(str(audio_path)):
                return None

            try:
                with open(audio_path, 'rb') as f:
                    header = f.read(12)
                    if header[4:8] == b'ftyp':
                        new_path = str(audio_path).rsplit('.', 1)[0] + ".m4a"
                        shutil.move(str(audio_path), new_path)
                        audio_path = Path(new_path)
                        logger.info(f"Renamed audio to M4A: {audio_path.name}")
            except Exception as e:
                logger.error(f"Error checking file type: {e}")

            final_cover_path = None
            if cover_url:
                final_cover_path = await download_file(cover_url, cover_path)

            await asyncio.to_thread(
                update_metadata,
                str(audio_path),
                title=title,
                artist=artist,
                cover_file=str(final_cover_path) if final_cover_path else None
            )

            return MediaContent(
                type=MediaType.AUDIO,
                path=audio_path,
                title=title,
                performer=artist,
                duration=duration,
                cover=final_cover_path
            )
        except Exception as e:
            logger.error(f"Failed to process music: {e}")
            return None

    async def get_info(self, url: str) -> Optional['MediaMetadata']:
        return None
