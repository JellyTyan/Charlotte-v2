import logging

from curl_cffi.requests import AsyncSession

from models.errors import BotError, ErrorCode
from models.metadata import MediaMetadata, MetadataType
from utils.download_utils import download_file

logger = logging.getLogger(__name__)

async def get_track_info(track_id: int) -> MediaMetadata:
    async with AsyncSession(impersonate="chrome136") as session:
        response = await session.get(f"https://api.deezer.com/track/{track_id}")

        if response.status_code != 200:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message=f"HTTP {response.status_code}",
                url=f"https://www.deezer.com/track/{track_id}",
                is_logged=True
            )

        data = response.json()

        if data.get('error'):
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message=data['error'].get('message', 'Unknown error'),
                url=f"https://www.deezer.com/track/{track_id}",
                is_logged=True
            )

        md5_image = data.get('md5_image')
        cover_url = f"https://cdn-images.dzcdn.net/images/cover/{md5_image}/400x400.jpg" if md5_image else None
        full_cover_url = f"https://cdn-images.dzcdn.net/images/cover/{md5_image}/1900x1900.png" if md5_image else None

        return MediaMetadata(
            type=MetadataType.METADATA,
            url=data.get('link'),
            title=data.get('title'),
            performer=data.get('artist', {}).get('name'),
            cover=cover_url,
            full_size_cover=full_cover_url,
            duration=data.get('duration'),
            media_type="track"
        )

async def get_album_info(album_id: int) -> MediaMetadata:
    async with AsyncSession(impersonate="chrome136") as session:
        response = await session.get(f"https://api.deezer.com/album/{album_id}")

        if response.status_code != 200:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message=f"HTTP {response.status_code}",
                url=f"https://www.deezer.com/album/{album_id}",
                is_logged=True
            )

        data = response.json()

        if data.get('error'):
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message=data['error'].get('message', 'Unknown error'),
                url=f"https://www.deezer.com/album/{album_id}",
                is_logged=True
            )

        md5_image = data.get('md5_image')
        cover = None
        if md5_image:
            cover_url = f"https://cdn-images.dzcdn.net/images/cover/{md5_image}/1900x1900.png"
            cover_path = await download_file(cover_url, f"storage/temp/deezer_album_{album_id}.png")
            cover = str(cover_path) if cover_path else None

        items = []
        for track in data.get('tracks', {}).get('data', []):
            track_md5 = track.get('md5_image')
            track_cover = f"https://cdn-images.dzcdn.net/images/cover/{track_md5}/400x400.jpg" if track_md5 else None
            track_full_cover = f"https://cdn-images.dzcdn.net/images/cover/{track_md5}/1900x1900.png" if track_md5 else None

            items.append(MediaMetadata(
                type=MetadataType.METADATA,
                url=track.get('link'),
                title=track.get('title'),
                performer=track.get('artist', {}).get('name'),
                cover=track_cover,
                full_size_cover=track_full_cover,
                duration=track.get('duration'),
                media_type='track'
            ))

        return MediaMetadata(
            type=MetadataType.METADATA,
            url=data.get('link'),
            title=data.get('title'),
            performer=data.get('artist', {}).get('name'),
            performer_url=data.get('artist', {}).get('link'),
            cover=cover,
            media_type='album',
            extra={
                'release_date': data.get('release_date'),
                'track_count': data.get('nb_tracks'),
                'record_label': data.get('label')
            },
            items=items
        )

async def get_playlist_info(playlist_id: int) -> MediaMetadata:
    async with AsyncSession(impersonate="chrome136") as session:
        response = await session.get(f"https://api.deezer.com/playlist/{playlist_id}")

        if response.status_code != 200:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message=f"HTTP {response.status_code}",
                url=f"https://www.deezer.com/playlist/{playlist_id}",
                is_logged=True
            )

        data = response.json()

        if data.get('error'):
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message=data['error'].get('message', 'Unknown error'),
                url=f"https://www.deezer.com/playlist/{playlist_id}",
                is_logged=True
            )

        cover = None
        cover_url = data.get('picture_xl') or data.get('picture_big')
        if cover_url:
            cover_path = await download_file(cover_url, f"storage/temp/deezer_playlist_{playlist_id}.jpg")
            cover = str(cover_path) if cover_path else None

        items = []
        for track in data.get('tracks', {}).get('data', []):
            track_md5 = track.get('album', {}).get('md5_image')
            track_cover = f"https://cdn-images.dzcdn.net/images/cover/{track_md5}/400x400.jpg" if track_md5 else None
            track_full_cover = f"https://cdn-images.dzcdn.net/images/cover/{track_md5}/1900x1900.png" if track_md5 else None

            items.append(MediaMetadata(
                type=MetadataType.METADATA,
                url=track.get('link'),
                title=track.get('title'),
                performer=track.get('artist', {}).get('name'),
                cover=track_cover,
                full_size_cover=track_full_cover,
                duration=track.get('duration'),
                media_type='track'
            ))

        return MediaMetadata(
            type=MetadataType.METADATA,
            url=data.get('link'),
            title=data.get('title'),
            description=data.get('description'),
            performer=data.get('creator', {}).get('name'),
            performer_url=data.get('creator', {}).get('link'),
            cover=cover,
            media_type='playlist',
            extra={
                'track_count': data.get('nb_tracks')
            },
            items=items
        )
