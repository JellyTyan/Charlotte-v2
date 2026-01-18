import asyncio
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pathlib
from typing import List, Optional

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
    get_playlist_info,
    get_album_info
)

logger = logging.getLogger(__name__)

class AppleMusicService(BaseService):
    name = "AppleMusic"
    _download_executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, output_path: str = "storage/temp/") -> None:
        super().__init__()
        self.output_path = output_path

    async def get_info(self, url: str, *args, **kwargs) -> MediaMetadata|None:
        logger.debug(f"Getting info for AppleMusic URL: {url}")
        config = kwargs.get('config')
        if not config:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Config is required",
                critical=True,
                is_logged=True
            )

        token = config.APPLE_MUSIC_TOKEN

        logger.debug("Token retrieved successfully")

        match_track = re.search(r"song/([^/?]+)", url)
        match_album_track = re.search(r"album\/[^\/\s]+\/\d+\?i=\d+$", url)
        match_playlist = re.search(r"playlist/([^/?]+)", url)
        match_album = re.search(r"album/([^/?]+)", url)
        if match_track:
            song_pattern = re.compile(
                r"^https?://music\.apple\.com/(?P<region>[a-z]{2})/song/(?:[^/]+/)?(?P<id>\d+)"
            )
            m = song_pattern.match(url)

            if m:
                return await get_track_info(m.group("id"), token, m.group("region"))
        elif match_album_track:
            album_track_pattern = re.compile(
                r"^https?://music\.apple\.com/(?P<region>[a-z]{2})/album/(?:[^/]+/)?(?P<album_id>\d+).*?[?&]i=(?P<track_id>\d+)"
            )
            m = album_track_pattern.match(url)

            if m:
                return await get_track_info(m.group("track_id"), token, m.group("region"))
        elif match_playlist:
            playlist_pattern = re.compile(
                r"^https?://music\.apple\.com/(?P<region>[a-z]{2})/playlist/(?:[^/]+/)?(?P<id>[^/?\s]+)"
            )
            m = playlist_pattern.match(url)

            if m:
                return await get_playlist_info(m.group("id"), token, m.group("region"))
        elif match_album:
            playlist_pattern = re.compile(
                r"^https?://music\.apple\.com/(?P<region>[a-z]{2})/album/(?:[^/]+/)?(?P<id>[^/?\s]+)"
            )
            m = playlist_pattern.match(url)

            if m:
                return await get_album_info(m.group("id"), token, m.group("region"))
        else:
            logger.warning(f"Unrecognized AppleMusic URL pattern: {url}")
            raise BotError(
                code=ErrorCode.INVALID_URL,
                message="Unrecognized AppleMusic URL format",
                url=url,
                is_logged=True
            )
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message=f"Failed to get parse data",
            url=url,
            is_logged=True
        )

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

                            # Download covers
                            cover_path = None
                            full_cover_path = None
                            base_path = os.path.join(self.output_path, pathlib.Path(downloaded_path).stem)

                            # 1. Download standard cover (for Telegram preview & embedding)
                            if cover_url:
                                try:
                                    cover_path = f"{base_path}.jpg"
                                    await download_file(cover_url, cover_path)
                                except Exception as e:
                                    logger.warning(f"Failed to download cover: {e}")
                                    cover_path = None

                            # 2. Download full cover (for sending as document)
                            if full_cover_url:
                                try:
                                    full_cover_path = f"{base_path}_full.png"
                                    await download_file(full_cover_url, full_cover_path)
                                except Exception as e:
                                    logger.warning(f"Failed to download full cover: {e}")
                                    full_cover_path = None

                            # 3. Update Metadata
                            try:
                                await asyncio.get_event_loop().run_in_executor(
                                    self._download_executor,
                                    lambda: update_metadata(
                                        downloaded_path,
                                        title=title,
                                        artist=performer,
                                        cover_file=cover_path
                                    )
                                )
                            except Exception as e:
                                logger.error(f"Failed to update metadata for Tidal track: {e}")

                            # Return MediaContent
                            duration = item.get('duration', 0)

                            cover_file = Path(cover_path) if cover_path and await aios.path.exists(cover_path) else None
                            full_cover_file = Path(full_cover_path) if full_cover_path and await aios.path.exists(full_cover_path) else None

                            return [MediaContent(
                                type=MediaType.AUDIO,
                                path=Path(downloaded_path),
                                duration=duration,
                                title=title,
                                performer=performer,
                                cover=cover_file,
                                full_cover=full_cover_file
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

                # Use yt-dlp's prepare_filename to get actual file path
                audio_path = ydl.prepare_filename(info_dict).rsplit('.', 1)[0] + '.mp3'
                base_path = audio_path.rsplit('.', 1)[0]
                logger.debug(f"Audio path: {audio_path}")

                # Download cover (prefer provided cover over YouTube thumbnail)
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

                # Download full size cover if available
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
