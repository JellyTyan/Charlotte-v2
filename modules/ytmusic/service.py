import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

from aiofiles import os as aios
from ytmusicapi import YTMusic

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata, MetadataType
from models.service_list import Services
from storage.db.crud import get_media_cache
from utils import random_cookie_file, get_extra_audio_options, sanitize_filename

logger = logging.getLogger(__name__)

class YTMusicService:
    name = "YTMusic"
    _download_executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, output_path: str = "storage/temp/", arq=None) -> None:
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
        
        # Decode HTML entities in URL
        import html
        url = html.unescape(url)
        
        ytmsc = YTMusic()
        match_track = re.search(r"watch\?v=([^&]+)", url)
        match_playlist = re.search(r"playlist\?list=([^&]+)", url)

        if match_track:
            video_id = match_track.group(1)
            for attempt in range(3):
                try:
                    result = ytmsc.get_song(videoId=video_id)
                    video_details = result.get("videoDetails")
                    if video_details:
                        return MediaMetadata(
                            type=MetadataType.METADATA,
                            url=url,
                            title=video_details.get("title", "Unknown"),
                            performer=video_details.get("author", "Unknown"),
                            media_type="track",
                            cache_key=f"ytmusic:{video_id}"
                        )
                except Exception as e:
                    if attempt == 2:
                        logger.warning(f"ytmusicapi failed, using yt-dlp fallback: {e}")
                        # Fallback to yt-dlp
                        job = await self.arq.enqueue_job(
                            "universal_ytdlp_extract",
                            url=url,
                            extract_only=True,
                            cookies_file=random_cookie_file("youtube"),
                            _queue_name='light'
                        )
                        try:
                            info = await job.result()
                        except Exception as e:
                            raise BotError(
                                code=ErrorCode.METADATA_ERROR,
                                service=Services.YTMUSIC,
                                message=f"Failed to fetch YTMusic info via yt-dlp: {e}",
                                url=url,
                                critical=True,
                                is_logged=True
                            )
                        if info:
                            return MediaMetadata(
                                type=MetadataType.METADATA,
                                url=url,
                                title=info.get("title", "Unknown"),
                                performer=info.get("uploader", "Unknown"),
                                media_type="track",
                                cache_key=f"ytmusic:{video_id}"
                            )
                        raise
                    logger.warning(f"Attempt {attempt + 1} failed for {video_id}: {e}")
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Failed to retrieve video details after 3 attempts",
                url=url,
                service=Services.YTMUSIC,
                is_logged=True
            )

        elif match_playlist:
            playlist_id = match_playlist.group(1)
            for attempt in range(3):
                try:
                    result = ytmsc.get_playlist(playlistId=playlist_id)
                    break
                except Exception as e:
                    if attempt == 2:
                        raise BotError(
                            code=ErrorCode.PLAYLIST_INFO_ERROR,
                            message=f"Failed to get playlist after 3 attempts: {e}",
                            url=url,
                            service=Services.YTMUSIC,
                            is_logged=True
                        )
                    logger.warning(f"Attempt {attempt + 1} failed for playlist {playlist_id}: {e}")

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

                try:
                    cover_result = await job.result()
                except Exception as e:
                    logger.warning(f"Failed to download YTMusic playlist cover: {e}")
                    cover_result = None

                cover = str(cover_result) if cover_result else None

            items = []
            for track in result.get("tracks", []):
                video_id = track.get('videoId')
                items.append(MediaMetadata(
                    type=MetadataType.METADATA,
                    url=f"https://music.youtube.com/watch?v={video_id}",
                    title=track.get("title"),
                    performer=", ".join(artist["name"] for artist in track.get("artists", [])),
                    duration=track.get("duration_seconds"),
                    media_type="track",
                    cache_key=f"ytmusic:{video_id}" if video_id else None
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
                output_template=f"{self.output_path}%(id)s_%(title)s.%(ext)s",
                extra_opts=get_extra_audio_options(),
                _queue_name='heavy'
            )
            try:
                result = await job.result()
            except Exception as e:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    service=Services.YTMUSIC,
                    message=f"Failed to download YTMusic audio: {e}",
                    url=url,
                    critical=True,
                    is_logged=True
                )
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

                    try:
                        await job.result()
                        # Process audio thumbnail for Telegram
                        process_job = await self.arq.enqueue_job('process_audio_thumbnail', input_path=cover_path, _queue_name='light')
                        cover_path = await process_job.result()
                    except Exception as e:
                        logger.warning(f"Failed to download YTMusic cover: {e}")
                        cover_path = None
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

            try:
                await job.result()
            except Exception as e:
                logger.error(f"Failed to update YTMusic metadata: {e}")
                # Not critical since the file is already downloaded

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


async def cache_check(session, cache_key: str) -> MediaContent | None:
    """Check DB cache for a previously sent YTMusic track and return a MediaContent if found."""
    cached = await get_media_cache(session, cache_key)
    if cached:
        return MediaContent(
            type=MediaType.AUDIO,
            telegram_file_id=cached.telegram_file_id,
            telegram_document_file_id=cached.telegram_document_file_id,
            cover_file_id=cached.data.cover,
            full_cover_file_id=cached.data.full_cover,
            title=cached.data.title,
            performer=cached.data.author,
            duration=cached.data.duration
        )
    return None


def get_cache_key(url: str) -> str:
    """Generate a unique cache key based on the URL and the selected format (video quality or audio)."""
    match_track = re.search(r"watch\?v=([^&]+)", url)
    video_id = match_track.group(1) if match_track else url

    return f"ytmusic:{video_id}"