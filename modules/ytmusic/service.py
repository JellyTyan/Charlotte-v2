import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

from aiofiles import os as aios
from ytmusicapi import YTMusic
from yt_dlp.utils import sanitize_filename

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata, MetadataType
from modules.base_service import BaseService
from models.service_list import Services
from utils import random_cookie_file, get_extra_audio_options

logger = logging.getLogger(__name__)

class YTMusicService(BaseService):
    name = "YTMusic"
    _download_executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, output_path: str = "storage/temp/", arq=None) -> None:
        super().__init__()
        self.output_path = output_path
        self.arq = arq

    async def get_info(self, url: str, *args, **kwargs) -> MediaMetadata|None:
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )
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

                job = await self.arq.enqueue_job('universal_download', url=cover_url, destination=f"{self.output_path}ytmusic_playlist_{playlist_id}.jpg", _queue_name='light')

                cover_result = await job.result()

                cover = str(cover_result) if cover_result else None

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
                url=url,
                extract_only = False,
                extract_audio=True,
                cookies_file=random_cookie_file("youtube"),
                output_template=f"{self.output_path}%(id)s_{sanitize_filename('%(title)s')}.%(ext)s",
                extra_opts=get_extra_audio_options(),
                _queue_name='heavy'
            )
            result = await job.result()
            clean_info = result["info"]
            filepath = result["filepath"]

            if not clean_info:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message="Failed to get audio info",
                    url=url,
                    service=Services.YTMUSIC,
                    is_logged=True
                )

            title = clean_info.get("title", "Unknown")
            performer = clean_info.get("uploader", "Unknown")

            base_path = filepath.rsplit('.', 1)[0]
            logger.debug(f"Audio path: {filepath}")

            cover_path = None
            thumbnail_url = clean_info.get("thumbnail", None)

            # Try to find square thumbnail from thumbnails list
            thumbnails = clean_info.get("thumbnails", [])
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
                    job = await self.arq.enqueue_job('universal_download', url=thumbnail_url, destination=cover_path, _queue_name='light')

                    await job.result()
                except Exception as e:
                    logger.warning(f"Failed to download cover: {e}")
                    cover_path = None

            logger.debug("Updating metadata")
            job = await self.arq.enqueue_job(
                "universal_metadata_update",
                filepath,
                title=title,
                artist=performer,
                cover_file=cover_path,
                _queue_name='heavy'
            )

            await job.result()

            if await aios.path.exists(filepath):
                logger.debug(f"Download completed: {filepath}")
                cover_file = None
                if cover_path and await aios.path.exists(cover_path):
                    cover_file = Path(cover_path)
                return [MediaContent(
                    type=MediaType.AUDIO,
                    path=Path(filepath),
                    duration=clean_info.get("duration", None),
                    title=title,
                    performer=performer,
                    cover=cover_file
                )]
            else:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message="Audio file not found after download",
                    url=url,
                    service=Services.YTMUSIC,
                    is_logged=True,
                )

        except BotError as ebot:
            ebot.service = Services.YTMUSIC
            raise ebot
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Error downloading YTMusic Audio: {e}",
                url=url,
                service=Services.YTMUSIC,
                critical=True,
                is_logged=True
            ) from e
