import asyncio
import logging
import os
import re
import httpx
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import List

import yt_dlp
from aiofiles import os as aios

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata, MetadataType
from modules.base_service import BaseService
from utils import download_file, update_metadata
from utils.service_utils import get_audio_options
from .utils import get_cover_url

logger = logging.getLogger(__name__)

class SoundCloudService(BaseService):
    name = "SoundCloud"
    _download_executor = ThreadPoolExecutor(max_workers=10)

    def __init__(self, output_path: str = "storage/temp/") -> None:
        super().__init__()
        self.output_path = output_path

    async def get_info(self, url: str, *args, **kwargs) -> MediaMetadata|None:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(url)

        match = re.search(r'window\.__sc_hydration = (\[.*?\]);', response.text, re.DOTALL)
        if not match:
            return None

        import json
        data = json.loads(match.group(1))
        sound = next((item.get('data') for item in data if item.get('hydratable') == 'sound'), None)
        playlist = next((item.get('data') for item in data if item.get('hydratable') == 'playlist'), None)

        if sound:
            return MediaMetadata(
                type=MetadataType.METADATA,
                url=url,
                title=sound.get('title'),
                description=sound.get('description'),
                duration=sound.get('full_duration', 0) // 1000,
                cover=sound.get('artwork_url'),
                performer=sound.get('user', {}).get('username'),
                performer_url=sound.get('user', {}).get('permalink_url'),
                media_type='track'
            )

        if playlist:
            tracks = playlist.get('tracks', [])
            user = playlist.get('user', {})

            # Get cover: playlist artwork -> user visuals -> user avatar
            cover = playlist.get('artwork_url')
            if not cover:
                cover = user.get('avatar_url')

            return MediaMetadata(
                type=MetadataType.METADATA,
                url=url,
                title=playlist.get('title'),
                description=playlist.get('description'),
                duration=playlist.get('duration', 0) // 1000,
                cover=cover,
                performer=user.get('username'),
                performer_url=user.get('permalink_url'),
                media_type='album' if playlist.get('is_album') else 'playlist',
                items=[
                    MediaMetadata(
                        type=MetadataType.METADATA,
                        url=track.get('permalink_url', ''),
                        title=track.get('title'),
                        duration=track.get('full_duration', 0) // 1000,
                        cover=track.get('artwork_url'),
                        performer=track.get('user', {}).get('username'),
                        media_type='track'
                    ) for track in tracks if track.get('permalink_url')
                ]
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

                logger.debug("Downloading audio")
                await loop.run_in_executor(
                    self._download_executor,
                    lambda: ydl.download([url])
                )

                audio_path = ydl.prepare_filename(info_dict).rsplit('.', 1)[0] + '.mp3'
                base_path = audio_path.rsplit('.', 1)[0]

                logger.debug(f"Audio path: {audio_path}")

                cover_path = None
                cover_url = get_cover_url(info_dict)

                if cover_url:
                    try:
                        cover_path = f"{base_path}.jpg"
                        logger.debug(f"Downloading cover: {cover_url}")
                        await download_file(cover_url, cover_path)
                    except Exception as e:
                        logger.warning(f"Failed to download cover: {e}")
                        cover_path = None

                logger.debug("Updating metadata")
                title = info_dict.get('title', 'Unknown')
                performer = info_dict.get('uploader', 'Unknown')
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
                        duration=int(info_dict.get("duration", 0)) if info_dict.get("duration") else None,
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
                message=f"Error downloading SoundCloud Audio: {e}",
                url=url,
                critical=True,
                is_logged=True
            )
