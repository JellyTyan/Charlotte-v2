import asyncio
import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pathlib
from typing import List, Optional

import yt_dlp
from aiofiles import os as aios
from yt_dlp.utils import sanitize_filename

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata, MetadataType
from modules.base_service import BaseService
from storage.cache.redis_client import get_or_cache
from utils import download_file, search_music, update_metadata

from utils.service_utils import get_audio_options
from .utils import (
    fetch_spotify_token,
    get_spotify_author,
    get_set_list
)

from utils.tidal import TidalUtil

logger = logging.getLogger(__name__)

class SpotifyService(BaseService):
    name = "Spotify"
    _download_executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, output_path: str = "storage/temp/") -> None:
        super().__init__()
        self.output_path = output_path

    async def get_info(self, url: str, *args, **kwargs) -> MediaMetadata|None:
        logger.debug(f"Getting info for Spotify URL: {url}")
        config = kwargs.get('config')
        if not config:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Config is required",
                critical=True,
                is_logged=True
            )

        logger.debug("Fetching Spotify access token")
        data = await get_or_cache(
            "spotify_bearer_token",
            lambda: fetch_spotify_token(config),
            ttl=3500
        )
        token = data["token"]
        logger.debug("Token retrieved successfully")

        match_track = re.search(r"track/([^/?]+)", url)
        match_playlist = re.search(r"playlist/([^/?]+)", url)
        match_album = re.search(r"album/([^/?]+)", url)
        if match_track:
            track_id = match_track.group(1)
            logger.debug(f"Extracting track info for ID: {track_id}")
            performer, title, cover_url = await get_spotify_author(track_id, token)
            logger.debug(f"Track info: {performer} - {title}")

            return MediaMetadata(
                type=MetadataType.METADATA,
                url=url,
                title=title,
                performer=performer,
                cover=cover_url,
                media_type="track",
            )
        elif match_playlist:
            playlist_id = match_playlist.group(1)
            logger.debug(f"Extracting playlist info for ID: {playlist_id}")
            return await get_set_list(playlist_id, "playlist", token)
        elif match_album:
            album_id = match_album.group(1)
            logger.debug(f"Extracting album info for ID: {album_id}")
            return await get_set_list(album_id, "album", token)
        else:
            logger.warning(f"Unrecognized Spotify URL pattern: {url}")
            raise BotError(
                code=ErrorCode.INVALID_URL,
                message="Unrecognized Spotify URL format",
                url=url,
                is_logged=True
            )

    async def download(self, performer: str, title: str, cover_url: Optional[str] = None, lossless_mode: bool = False) -> List[MediaContent]:
        logger.debug(f"Starting download for: {performer} - {title} (Lossless: {lossless_mode})")

        # Experimental Tidal Lossless Download
        if lossless_mode:
            try:
                logger.debug(f"Attempting Tidal download for: {performer} - {title}")
                tidal = TidalUtil()
                search_query = f"{performer} - {title}"
                results = await tidal.search(search_query, limit=10)

                for item in results:
                    # Simple fuzzy match replacement: clean strings and compare
                    tidal_artist = item.get('artist', {}).get('name', '').lower()
                    tidal_title = item.get('title', '').lower()

                    target_artist = performer.lower()
                    target_title = title.lower()

                    # Check if strings are contained or equal (ignoring case)
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
                            if cover_url:
                                try:
                                    cover_path = os.path.join(self.output_path, f"{pathlib.Path(downloaded_path).stem}.jpg")
                                    await download_file(cover_url, cover_path)
                                    if await aios.path.exists(cover_path):
                                        cover_file = Path(cover_path)
                                except Exception as e:
                                    logger.warning(f"Failed to download cover: {e}")

                            # Return MediaContent
                            # Note: Duration might be missing if not parsed from file, but we can try to get it from Tidal result
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

        # Fallback to standard YouTube/yt-dlp method
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
                print(audio_path)
                base_path = audio_path.rsplit('.', 1)[0]
                print(base_path)
                logger.debug(f"Audio path: {audio_path}")

                # Use cover from get_info if available, otherwise download from YouTube
                cover_path = None
                if not cover_url:
                    thumbnail_url = info_dict.get("thumbnail", None)
                    if thumbnail_url:
                        cover_url = thumbnail_url
                else:
                    logger.debug(f"Using existing cover: {cover_url}")

                if cover_url:
                    try:
                        cover_path = f"{base_path}.jpg"
                        logger.debug(f"Downloading cover: {cover_url}")
                        await download_file(cover_url, cover_path)
                    except Exception as e:
                        logger.warning(f"Failed to download cover: {e}")
                        cover_path = None

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
                    cover_file = None
                    if cover_path and await aios.path.exists(cover_path):
                        cover_file = Path(cover_path)
                    return [MediaContent(
                        type=MediaType.AUDIO,
                        path=Path(audio_path),
                        duration=info_dict.get("duration", None),
                        title=title,
                        performer=performer,
                        cover=cover_file
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
