import asyncio
import logging
import re
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pathlib
from typing import List, Optional
import httpx

import yt_dlp
from yt_dlp.utils import sanitize_filename
from aiofiles import os as aios

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from modules.base_service import BaseService
from utils import download_file, search_music, update_metadata
from utils.tidal import TidalUtil

from utils.service_utils import get_audio_options
from .utils import (
    get_track_info,
    get_album_info,
    get_playlist_info
)

logger = logging.getLogger(__name__)

class DeezerService(BaseService):
    name = "Deezer"
    _download_executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, output_path: str = "storage/temp/") -> None:
        super().__init__()
        self.output_path = output_path

    async def get_info(self, url: str, *args, **kwargs) -> MediaMetadata|None:
        logger.debug(f"Getting info for Deezer URL: {url}")

        match_short = re.search(r"link\.deezer\.com/s/([A-Za-z0-9]+)", url)

        if match_short:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    url = str(response.url)
                    logger.debug(f"Redirected URL: {url}")

        match_track = re.search(r"/track/(\d+)", url)
        match_album = re.search(r"/album/(\d+)", url)
        match_playlist = re.search(r"/playlist/(\d+)", url)

        if match_track:
            track_id = int(match_track.group(1))
            logger.debug(f"Extracting track info for ID: {track_id}")
            return await get_track_info(track_id)
        elif match_album:
            album_id = int(match_album.group(1))
            logger.debug(f"Extracting album info for ID: {album_id}")
            return await get_album_info(album_id)
        elif match_playlist:
            playlist_id = int(match_playlist.group(1))
            logger.debug(f"Extracting album info for ID: {playlist_id}")
            return await get_playlist_info(playlist_id)

    async def download(self, performer: str, title: str, cover_url: Optional[str] = None, full_cover_url: Optional[str] = None, lossless_mode: bool = False) -> List[MediaContent]:
        logger.debug(f"Starting download for: {performer} - {title} (Lossless: {lossless_mode})")

        # Experimental Tidal Lossless Download
        if lossless_mode:
            try:
                logger.debug(f"Attempting Tidal download for: {performer} - {title}")
                tidal = TidalUtil()
                search_query = f"{performer} - {title}"
                results = await tidal.search(search_query, limit=10)

                for item in results:
                    tidal_artist = item.get('artist', {}).get('name', '').lower()
                    tidal_title = item.get('title', '').lower()

                    target_artist = performer.lower()
                    target_title = title.lower()

                    if (target_artist in tidal_artist or tidal_artist in target_artist) and \
                       (target_title in tidal_title or tidal_title in target_title):

                        logger.info(f"Found Tidal match: {item['artist']['name']} - {item['title']} (ID: {item['id']})")
                        filename = sanitize_filename(f"{performer} - {title}.flac")
                        filepath = os.path.join(self.output_path, filename)

                        downloaded_path = await tidal.download(item['id'], filepath)

                        if downloaded_path and await aios.path.exists(downloaded_path):
                            logger.info(f"Successfully downloaded from Tidal: {downloaded_path}")

                            # Download cover if needed
                            cover_file = None
                            # Prefer full cover if available
                            target_cover_url = full_cover_url or cover_url

                            if target_cover_url:
                                try:
                                    cover_path = os.path.join(self.output_path, f"{pathlib.Path(downloaded_path).stem}.jpg")
                                    await download_file(target_cover_url, cover_path)
                                    if await aios.path.exists(cover_path):
                                        cover_file = Path(cover_path)
                                except Exception as e:
                                    logger.warning(f"Failed to download cover: {e}")

                            # Return MediaContent
                            duration = item.get('duration', 0)

                            return [MediaContent(
                                type=MediaType.AUDIO,
                                path=Path(downloaded_path),
                                duration=duration,
                                title=title,
                                performer=performer,
                                cover=cover_file
                            )]
                        else:
                            logger.warning("Tidal download returned path but file missing or failed.")
            except Exception as e:
                logger.error(f"Tidal download failed: {e}. Falling back to standard method.")

        # Fallback to standard method
        options = get_audio_options(f"{performer} - {title}")
        logger.debug(f"Searching YouTube for: {performer} - {title}")
        video_link = await search_music(performer, title)
        if not video_link:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"No YouTube results found for: {performer} - {title}",
                is_logged=True
            )
        logger.debug(f"Found YouTube link: {video_link}")
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                loop = asyncio.get_event_loop()

                logger.debug("Extracting audio info")
                info_dict = await loop.run_in_executor(
                    self._download_executor,
                    lambda: ydl.extract_info(video_link, download=False)
                )
                if not info_dict:
                    raise BotError(
                        code=ErrorCode.DOWNLOAD_FAILED,
                        message="Failed to get audio info",
                        url=video_link,
                        is_logged=True
                    )

                logger.debug("Downloading audio")
                await loop.run_in_executor(
                    self._download_executor,
                    lambda: ydl.download([video_link])
                )

                audio_path = ydl.prepare_filename(info_dict).rsplit('.', 1)[0] + '.mp3'
                base_path = audio_path.rsplit('.', 1)[0]
                logger.debug(f"Audio path: {audio_path}")

                cover_path = None
                full_cover_path = None

                if not cover_url:
                    cover_url = info_dict.get("thumbnail")

                if cover_url:
                    try:
                        cover_path = f"{base_path}.jpg"
                        logger.debug(f"Downloading cover: {cover_url}")
                        await download_file(cover_url, cover_path)
                    except Exception as e:
                        logger.warning(f"Failed to download cover: {e}")
                        cover_path = None

                if full_cover_url:
                    try:
                        full_cover_path = f"{base_path}_full.png"
                        logger.debug(f"Downloading full cover: {full_cover_url}")
                        await download_file(full_cover_url, full_cover_path)
                    except Exception as e:
                        logger.warning(f"Failed to download full cover: {e}")
                        full_cover_path = None

                logger.debug("Updating metadata")
                await loop.run_in_executor(
                    self._download_executor,
                    lambda: update_metadata(
                        audio_path,
                        title=title,
                        artist=performer,
                        cover_file=cover_path
                    )
                )

                if await aios.path.exists(audio_path):
                    logger.debug(f"Download completed: {audio_path}")
                    cover_file = Path(cover_path) if cover_path and await aios.path.exists(cover_path) else None
                    full_cover_file = Path(full_cover_path) if full_cover_path and await aios.path.exists(full_cover_path) else None

                    return [MediaContent(
                        type=MediaType.AUDIO,
                        path=Path(audio_path),
                        duration=int(info_dict.get("duration", 0)) if info_dict.get("duration") else None,
                        title=title,
                        performer=performer,
                        cover=cover_file,
                        full_cover=full_cover_file
                    )]
                else:
                    raise BotError(
                        code=ErrorCode.DOWNLOAD_FAILED,
                        message="Audio file not found after download",
                        url=video_link,
                        is_logged=True,
                    )

        except BotError:
            raise
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Error downloading YouTube Audio: {e}",
                url=video_link,
                critical=True,
                is_logged=True
            )
