import logging
import re
import os
from pathlib import Path
import pathlib
from typing import List
from curl_cffi.requests import AsyncSession

from aiofiles import os as aios

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from models.service_list import Services
from utils import search_music, transliterate, random_cookie_file, get_extra_audio_options, sanitize_filename
from utils.tidal import TidalUtil

from .utils import (
    get_track_info,
    get_album_info,
    get_playlist_info
)

logger = logging.getLogger(__name__)

class DeezerService:
    name = "Deezer"

    def __init__(self, output_path: str = "storage/temp/", arq=None) -> None:
        self.output_path = output_path
        self.arq = arq

    async def get_info(self, url: str, *args, **kwargs) -> MediaMetadata|None:
        logger.debug(f"Getting info for Deezer URL: {url}")

        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                service=Services.DEEZER,
                critical=True,
                is_logged=True
            )

        match_short = re.search(r"link\.deezer\.com/s/([A-Za-z0-9]+)", url)

        if match_short:
            async with AsyncSession(impersonate="chrome136") as session:
                response = await session.get(url, allow_redirects=True)
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

    async def download(self, media_metadata: MediaMetadata, lossless_mode: bool = False) -> List[MediaContent]:
        logger.debug(f"Starting download for: {media_metadata.performer} - {media_metadata.title} (Lossless: {lossless_mode})")

        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                service=Services.DEEZER,
                critical=True,
                is_logged=True
            )

        performer = media_metadata.performer
        title = media_metadata.title
        cover_url = media_metadata.cover
        full_cover_url = media_metadata.full_size_cover
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
                # Download covers
                cover_path = None
                full_cover_path = None
                base_path = os.path.join(self.output_path, pathlib.Path(tidal_downloaded_path).stem)

                # 1. Download standard cover (for Telegram preview & embedding)
                if cover_url:
                    try:
                        cover_path = f"{base_path}.jpg"
                        job = await self.arq.enqueue_job("universal_download", cover_url, cover_path)
                        try:
                            await job.result()
                            process_job = await self.arq.enqueue_job('process_audio_thumbnail', input_path=cover_path, _queue_name='light')
                            cover_path = await process_job.result()
                        except Exception as e:
                            logger.warning(f"Failed to download Tidal cover: {e}")
                            cover_path = None
                    except Exception as e:
                        logger.warning(f"Failed to download cover: {e}")
                        cover_path = None

                # 2. Download full cover (for sending as document)
                if full_cover_url:
                    try:
                        full_cover_path = f"{base_path}_full.png"
                        job = await self.arq.enqueue_job("universal_download", full_cover_url, full_cover_path)
                        try:
                            await job.result()
                        except Exception as e:
                            logger.warning(f"Failed to download Tidal full cover: {e}")
                            full_cover_path = None
                    except Exception as e:
                        logger.warning(f"Failed to download full cover: {e}")
                        full_cover_path = None

                # 3. Update Metadata
                try:
                    job = await self.arq.enqueue_job(
                        "universal_metadata_update",
                        tidal_downloaded_path,
                        title=title,
                        artist=performer,
                        cover_file=full_cover_path,
                        album_name=album_name,
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
                    full_cover=full_cover_file,
                    is_lossless=True
                )]

            # Tidal недоступен — не делаем YouTube-фоллбэк, пускаем хэндлер решать
            raise BotError(
                code=ErrorCode.LOSSLESS_UNAVAILABLE,
                message="Tidal is unavailable, lossless download skipped",
                service=Services.DEEZER,
                is_logged=False,
            )

        # Fallback to standard method
        logger.debug(f"Searching YouTube for: {performer} - {title}")
        video_link = await search_music(performer, title)
        if not video_link:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"No YouTube results found for: {performer} - {title}",
                service=Services.DEEZER,
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
                    service=Services.DEEZER,
                    message=f"Failed to download Deezer audio via YouTube fallback: {e}",
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
            cover_path = None
            full_cover_path = None

            if not cover_url:
                cover_url = info_dict.get("thumbnail")

            if cover_url:
                try:
                    cover_path = f"{base_path}.jpg"
                    logger.debug(f"Downloading cover: {cover_url}")
                    job = await self.arq.enqueue_job("universal_download", cover_url, cover_path)
                    try:
                        await job.result()
                        process_job = await self.arq.enqueue_job('process_audio_thumbnail', input_path=cover_path, _queue_name='light')
                        cover_path = await process_job.result()
                    except Exception as e:
                        logger.warning(f"Failed to download cover from YouTube fallback: {e}")
                        cover_path = None
                except Exception as e:
                    logger.warning(f"Failed to download cover: {e}")
                    cover_path = None

            # Download full size cover if available
            if full_cover_url:
                try:
                    full_cover_path = f"{base_path}_full.png"
                    logger.debug(f"Downloading full cover: {full_cover_url}")
                    job = await self.arq.enqueue_job("universal_download", full_cover_url, full_cover_path)
                    try:
                        await job.result()
                    except Exception as e:
                        logger.warning(f"Failed to download full cover from Deezer: {e}")
                        full_cover_path = None
                except Exception as e:
                    logger.warning(f"Failed to download full cover: {e}")
                    full_cover_path = None

            logger.debug("Updating metadata")
            job = await self.arq.enqueue_job(
                "universal_metadata_update",
                audio_path,
                title=title,
                artist=performer,
                cover_file=full_cover_path,
                album_name=album_name,
                date=release_date,
                track_number=track_number,
                _queue_name='heavy'
            )
            try:
                await job.result()
            except Exception as e:
                logger.error(f"Failed to update metadata for Deezer audio (YouTube fallback): {e}")
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
                    service=Services.DEEZER,
                    is_logged=True,
                )
        except BotError:
            raise
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Error downloading YouTube Audio: {e}",
                url=video_link,
                service=Services.DEEZER,
                critical=True,
                is_logged=True
            )
