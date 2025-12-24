import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

import yt_dlp
from aiofiles import os as aios
from ytmusicapi import YTMusic

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata, MetadataType
from modules.base_service import BaseService
from utils import download_file, update_metadata

from .utils import get_audio_options

logger = logging.getLogger(__name__)

class YTMusicService(BaseService):
    name = "YTMusic"
    _download_executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, output_path: str = "storage/temp/") -> None:
        super().__init__()
        self.output_path = output_path

    async def get_info(self, url: str, *args, **kwargs) -> MediaMetadata|None:
        ytmsc = YTMusic()
        match_track = re.search(r"watch\?v=([^&]+)", url)
        match_playlist = re.search(r"playlist\?list=([^&]+)", url)

        if match_track:
            result = ytmsc.get_song(videoId=match_track.group(1))
            return MediaMetadata(
                type=MetadataType.METADATA,
                url=url,
                title=result["videoDetails"]["title"],
                performer=result["videoDetails"]["author"],
                media_type="track",
            )

        elif match_playlist:
            playlist_id = match_playlist.group(1)
            result = ytmsc.get_playlist(playlistId=playlist_id)

            cover = None
            if result.get("thumbnails"):
                thumbnails = result["thumbnails"]
                square_thumb = None

                for thumb in thumbnails:
                    if thumb.get("width") == thumb.get("height"):
                        square_thumb = thumb
                        break

                if not square_thumb:
                    cover_url = thumbnails[-1]["url"]
                    if "=" in cover_url:
                        cover_url = cover_url.split("=")[0]
                    cover_url = f"{cover_url}=s544-c"
                else:
                    cover_url = square_thumb["url"]

                cover_path = await download_file(cover_url, f"storage/temp/ytmusic_playlist_{playlist_id}.jpg")
                cover = str(cover_path) if cover_path else None

            items = []
            for track in result.get("tracks", []):
                items.append(MediaMetadata(
                    type=MetadataType.METADATA,
                    url=f"https://music.youtube.com/watch?v={track['videoId']}",
                    title=track.get("title"),
                    performer=", ".join(artist["name"] for artist in track.get("artists", [])),
                    duration=track.get("duration_seconds"),
                    media_type="track"
                ))

            return MediaMetadata(
                type=MetadataType.METADATA,
                url=url,
                title=result["title"],
                description=result.get("description"),
                performer=result.get("author", {}).get("name") if isinstance(result.get("author"), dict) else result.get("author"),
                cover=cover,
                media_type="playlist",
                extra={
                    "track_count": result.get("trackCount"),
                    "duration": result.get("duration"),
                    "year": result.get("year")
                },
                items=items
            )

    async def download(self, url: str) -> List[MediaContent]:
        logger.debug(f"Starting download for: {url}")
        options = get_audio_options()
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                loop = asyncio.get_event_loop()

                logger.debug("Extracting audio info")
                info_dict = await loop.run_in_executor(
                    self._download_executor,
                    lambda: ydl.extract_info(url, download=False)
                )
                if not info_dict:
                    raise BotError(
                        code=ErrorCode.DOWNLOAD_FAILED,
                        message="Failed to get audio info",
                        url=url,
                        is_logged=True
                    )

                title = info_dict.get("title", "Unknown")
                performer = info_dict.get("uploader", "Unknown")

                logger.debug("Downloading audio")
                await loop.run_in_executor(
                    self._download_executor,
                    lambda: ydl.download([url])
                )

                audio_path = ydl.prepare_filename(info_dict).rsplit('.', 1)[0] + '.mp3'
                base_path = audio_path.rsplit('.', 1)[0]
                logger.debug(f"Audio path: {audio_path}")

                cover_path = None
                thumbnail_url = info_dict.get("thumbnail", None)

                # Try to find square thumbnail from thumbnails list
                thumbnails = info_dict.get("thumbnails", [])
                square_thumb = None
                for thumb in thumbnails:
                    if thumb.get("width") == thumb.get("height") and thumb.get("width", 0) >= 300:
                        square_thumb = thumb
                        break

                if square_thumb:
                    thumbnail_url = square_thumb["url"]

                if thumbnail_url:
                    try:
                        cover_path = f"{base_path}.jpg"
                        logger.debug(f"Downloading cover: {thumbnail_url}")
                        await download_file(thumbnail_url, cover_path)
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
                        url=url,
                        is_logged=True,
                    )

        except BotError:
            raise
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Error downloading YTMusic Audio: {e}",
                url=url,
                critical=True,
                is_logged=True
            )
