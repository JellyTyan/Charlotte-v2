import re
from typing import List
from pathlib import Path
import logging
import pathlib
import asyncio
import os

from aiofiles import os as aios

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from models.service_list import Services

from .utils import get_album_info, get_track_info, get_playlist_info
from utils import search_music, transliterate, random_cookie_file, get_extra_audio_options, sanitize_filename

from utils.tidal import TidalUtil

logger = logging.getLogger(__name__)

class AppleMusicService:
    name = "AppleMusic"

    def __init__(self, output_path: str = "storage/temp/", arq=None) -> None:
        self.output_path = output_path
        self.arq = arq

    async def get_info(self, url: str, *args, **kwargs) -> MediaMetadata|None:
        logger.debug(f"Getting info for AppleMusic URL: {url}")
        config = kwargs.get('config')
        if not config:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Config is required",
                service=Services.APPLE_MUSIC,
                critical=True,
                is_logged=True
            )

        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                service=Services.APPLE_MUSIC,
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
                return await get_track_info(int(m.group("id")), token, m.group("region"))
        elif match_album_track:
            album_track_pattern = re.compile(
                r"^https?://music\.apple\.com/(?P<region>[a-z]{2})/album/(?:[^/]+/)?(?P<album_id>\d+).*?[?&]i=(?P<track_id>\d+)"
            )
            m = album_track_pattern.match(url)

            if m:
                return await get_track_info(int(m.group("track_id")), token, m.group("region"))
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
                service=Services.APPLE_MUSIC,
                url=url,
                is_logged=True
            )
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message=f"Failed to get parse data",
            service=Services.APPLE_MUSIC,
            url=url,
            is_logged=True
        )

    async def download(self, media_metadata: MediaMetadata, lossless_mode: bool = False) -> List[MediaContent]:
        logger.debug(f"Starting download for: {media_metadata.performer} - {media_metadata.title} (Lossless: {lossless_mode})")

        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                service=Services.APPLE_MUSIC,
                critical=True,
                is_logged=True
            )

        performer = media_metadata.performer
        title = media_metadata.title
        cover_url = media_metadata.cover
        full_cover_url = media_metadata.full_size_cover
        genres = media_metadata.extra.get("genres", [])
        release_date = media_metadata.extra.get("release_date", "")
        track_number = media_metadata.extra.get("track_number", 0)
        album_name = media_metadata.extra.get("album_name", "")


        # Experimental Tidal Lossless Download
        if lossless_mode:
            tidal_downloaded_path = None
            tidal_item = None
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
                            tidal_downloaded_path = downloaded_path
                            tidal_item = item
                        else:
                            logger.warning("Tidal download returned path but file missing or failed.")
                        break
            except Exception as e:
                logger.error(f"Tidal download failed: {e}. Falling back to standard method.")

            if tidal_downloaded_path and tidal_item:
                base_path = os.path.join(self.output_path, pathlib.Path(tidal_downloaded_path).stem)
                full_cover_path = f"{base_path}_full.png"
                cover_path = f"{base_path}.jpg"

                # 1. Download standard cover (for Telegram preview & embedding)
                download_tasks = []
                if cover_url:
                    download_tasks.append(
                        await self.arq.enqueue_job("universal_download", cover_url, cover_path))

                # 2. Download full cover (for sending as document)
                if full_cover_url:
                    download_tasks.append(
                        await self.arq.enqueue_job("universal_download", full_cover_url, full_cover_path))

                results = await asyncio.gather(*[job.result() for job in download_tasks])

                if cover_url and cover_path:
                    try:
                        process_job = await self.arq.enqueue_job('process_audio_thumbnail', input_path=cover_path, _queue_name='light')
                        cover_path = await process_job.result()
                    except Exception as e:
                        logger.warning(f"Failed to process Apple Music cover: {e}")
                        cover_path = None

                # 3. Update Metadata
                try:
                    job = await self.arq.enqueue_job(
                        "universal_metadata_update",
                        tidal_downloaded_path,
                        title=title,
                        artist=performer,
                        cover_file=full_cover_path,
                        album_name=album_name,
                        genre_name=genres,
                        date=release_date,
                        track_number=track_number,
                        _queue_name='heavy'
                    )
                    try:
                        await job.result()
                    except Exception as e:
                        logger.warning(f"Failed to update Tidal metadata: {e}")
                except Exception as e:
                    logger.warning(f"Failed to update Tidal metadata: {e}")

                duration = tidal_item.get('duration', 0)
                cover_file = Path(cover_path) if cover_path and await aios.path.exists(cover_path) else None
                full_cover_file = Path(full_cover_path) if full_cover_path and await aios.path.exists(full_cover_path) else None

                return [MediaContent(
                    type=MediaType.AUDIO,
                    path=Path(tidal_downloaded_path),
                    duration=duration,
                    title=title,
                    performer=performer,
                    cover=cover_file,
                    full_cover=full_cover_file
                )]

        # Fallback to standard method
        logger.debug(f"Searching YouTube for: {performer} - {title}")
        video_link = await search_music(performer, title)
        if not video_link:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"No YouTube results found for: {performer} - {title}",
                service=Services.APPLE_MUSIC,
                is_logged=True
            )
        logger.debug(f"Found YouTube link: {video_link}")
        try:
            job = await self.arq.enqueue_job(
                "universal_ytdlp_extract",
                video_link,
                extract_only = False,
                format_selector = None,
                output_template = f"storage/temp/{sanitize_filename(transliterate(title))}.%(ext)s",
                cookies_file = random_cookie_file("youtube"),
                extra_opts=get_extra_audio_options(),
                _queue_name='heavy'
            )
            try:
                result = await job.result()
            except Exception as e:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    service=Services.APPLE_MUSIC,
                    message=f"Failed to download Apple Music audio via YouTube fallback: {e}",
                    url=video_link,
                    critical=True,
                    is_logged=True
                )
            info_dict = result.get("info")
            audio_path = result.get("filepath")
            audio_path = os.path.splitext(audio_path)[0] + ".mp3"

            base_path = audio_path.rsplit('.', 1)[0]
            logger.debug(f"Audio path: {audio_path}")

            # Download cover (prefer provided cover over YouTube thumbnail)
            full_cover_path = f"{base_path}_full.png"
            cover_path = f"{base_path}.jpg"

            if not cover_url:
                cover_url = info_dict.get("thumbnail")

            download_tasks = []
            if cover_url:
                download_tasks.append(
                    await self.arq.enqueue_job("universal_download", cover_url, cover_path))

            if full_cover_url:
                download_tasks.append(
                    await self.arq.enqueue_job("universal_download", full_cover_url, full_cover_path))

            results = await asyncio.gather(*[job.result() for job in download_tasks])

            if cover_url and cover_path:
                try:
                    process_job = await self.arq.enqueue_job('process_audio_thumbnail', input_path=cover_path, _queue_name='light')
                    cover_path = await process_job.result()
                except Exception as e:
                    logger.warning(f"Failed to process Apple Music cover (fallback): {e}")
                    cover_path = None

            logger.debug("Updating metadata")
            job = await self.arq.enqueue_job(
                "universal_metadata_update",
                audio_path,
                title=title,
                artist=performer,
                cover_file=full_cover_path,
                album_name=album_name,
                genre_name=genres,
                date=release_date,
                track_number=track_number,
                _queue_name='heavy'
            )
            try:
                await job.result()
            except Exception as e:
                logger.error(f"Failed to update metadata for Apple Music audio (YouTube fallback): {e}")
                # Not critical since the file is already downloaded

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
                    service=Services.APPLE_MUSIC,
                    is_logged=True,
                )

        except BotError:
            raise
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Error downloading YouTube Audio: {e}",
                url=video_link,
                service=Services.APPLE_MUSIC,
                critical=True,
                is_logged=True
            )
