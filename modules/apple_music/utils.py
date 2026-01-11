import logging

import httpx

from models.errors import BotError, ErrorCode
from models.metadata import MediaMetadata, MetadataType
from utils.download_utils import download_file

logger = logging.getLogger(__name__)


async def get_track_info(song_id: int, token: str, region_code: str = "us") -> MediaMetadata:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            f'https://amp-api.music.apple.com/v1/catalog/{region_code}/songs/{song_id}',
            headers={
                'authorization': f'Bearer {token}',
                'origin': 'https://music.apple.com',
                'referer': 'https://music.apple.com/',
            },
            timeout=10
        )

        if response.status_code != 200:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message=f"HTTP {response.status_code}",
                url=f"https://music.apple.com/{region_code}/song/{song_id}",
                is_logged=True
            )

        try:
            data = response.json()
        except Exception:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Invalid JSON response",
                url=f"https://music.apple.com/{region_code}/song/{song_id}",
                is_logged=True
            )

        if not data.get('data'):
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="No track data returned",
                url=f"https://music.apple.com/{region_code}/song/{song_id}",
                is_logged=True
            )

        track = data['data'][0]
        attrs = track.get('attributes', {})
        artwork = attrs.get('artwork', {})
        cover_url = artwork.get('url', '')

        small_cover = cover_url.replace('{w}x{h}', '400x400').replace('{f}', '.jpg') if cover_url else None
        full_cover = cover_url.replace('{w}x{h}', f"{artwork.get('width', 3000)}x{artwork.get('height', 3000)}").replace('{f}', '.png') if cover_url else None

        return MediaMetadata(
            type=MetadataType.METADATA,
            url=attrs.get('url'),
            title=attrs.get('name'),
            performer=attrs.get('artistName'),
            cover=small_cover,
            full_size_cover=full_cover,
            media_type="track",
        )


async def get_playlist_info(playlist_id: str, token: str, region_code: str = "us") -> MediaMetadata:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            f'https://amp-api.music.apple.com/v1/catalog/{region_code}/playlists/{playlist_id}',
            headers={
                'authorization': f'Bearer {token}',
                'origin': 'https://music.apple.com',
                'referer': 'https://music.apple.com/',
            },
            timeout=10
        )

        if response.status_code != 200:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message=f"HTTP {response.status_code}",
                url=f"https://music.apple.com/{region_code}/playlist/{playlist_id}",
                is_logged=True
            )

        data = response.json()
        playlist = data.get('data', [{}])[0]
        attrs = playlist.get('attributes', {})
        tracks_rel = playlist.get('relationships', {}).get('tracks', {})
        tracks_data = tracks_rel.get('data', [])
        next_url = tracks_rel.get('next')

        while next_url:
            response = await client.get(
                f'https://amp-api.music.apple.com{next_url}',
                headers={
                    'authorization': f'Bearer {token}',
                    'origin': 'https://music.apple.com',
                    'referer': 'https://music.apple.com/',
                },
                timeout=10
            )
            if response.status_code == 200:
                page_data = response.json()
                tracks_data.extend(page_data.get('data', []))
                next_url = page_data.get('next')
            else:
                break

        artwork = attrs.get('artwork', {})
        cover_url = artwork.get('url', '')
        full_cover_url = cover_url.replace('{w}x{h}', f"{artwork.get('width', 3000)}x{artwork.get('height', 3000)}").replace('{f}', '.png') if cover_url else None

        cover = None
        if full_cover_url:
            cover_path = await download_file(full_cover_url, f"storage/temp/apple_album_{playlist_id}.png")
            cover = str(cover_path) if cover_path else None

        items = []
        for track in tracks_data:
            if 'attributes' not in track or 'url' not in track['attributes']:
                continue
            track_attrs = track['attributes']
            track_artwork = track_attrs.get('artwork', {})
            track_cover_url = track_artwork.get('url', '')
            track_cover = track_cover_url.replace('{w}x{h}', '400x400').replace('{f}', '.jpg') if track_cover_url else None
            track_full_cover = track_cover_url.replace('{w}x{h}', f"{track_artwork.get('width', 3000)}x{track_artwork.get('height', 3000)}").replace('{f}', '.png') if track_cover_url else None

            items.append(MediaMetadata(
                type=MetadataType.METADATA,
                url=track_attrs['url'],
                title=track_attrs.get('name'),
                performer=track_attrs.get('artistName'),
                cover=track_cover,
                full_size_cover=track_full_cover,
                media_type='track'
            ))

        return MediaMetadata(
            type=MetadataType.METADATA,
            url=attrs.get('url'),
            title=attrs.get('name'),
            description=attrs.get('description', {}).get('standard'),
            performer=attrs.get('curatorName'),
            cover=cover,
            media_type='playlist',
            extra={
                'track_count': len(items)
            },
            items=items
        )


async def get_album_info(album_id: str, token: str, region_code: str = "us") -> MediaMetadata:
    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(
            f'https://amp-api.music.apple.com/v1/catalog/{region_code}/albums/{album_id}',
            headers={
                'authorization': f'Bearer {token}',
                'origin': 'https://music.apple.com',
                'referer': 'https://music.apple.com/',
            },
            timeout=10
        )

        if response.status_code != 200:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message=f"HTTP {response.status_code}",
                url=f"https://music.apple.com/{region_code}/album/{album_id}",
                is_logged=True
            )

        try:
            data = response.json()
        except Exception:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Invalid JSON response",
                url=f"https://music.apple.com/{region_code}/album/{album_id}",
                is_logged=True
            )

        if not data.get('data'):
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="No album data returned",
                url=f"https://music.apple.com/{region_code}/album/{album_id}",
                is_logged=True
            )

        album = data['data'][0]
        attrs = album.get('attributes', {})
        tracks_data = album.get('relationships', {}).get('tracks', {}).get('data', [])

        artwork = attrs.get('artwork', {})
        cover_url = artwork.get('url', '')
        full_cover_url = cover_url.replace('{w}x{h}', f"{artwork.get('width', 3000)}x{artwork.get('height', 3000)}").replace('{f}', '.png') if cover_url else None

        cover = None
        if full_cover_url:
            cover_path = await download_file(full_cover_url, f"storage/temp/apple_album_{album_id}.png")
            cover = str(cover_path) if cover_path else None

        items = []
        for track in tracks_data:
            if 'attributes' not in track or 'url' not in track['attributes']:
                continue
            track_attrs = track['attributes']
            track_artwork = track_attrs.get('artwork', {})
            track_cover_url = track_artwork.get('url', '')
            track_cover = track_cover_url.replace('{w}x{h}', '400x400').replace('{f}', '.jpg') if track_cover_url else None
            track_full_cover = track_cover_url.replace('{w}x{h}', f"{track_artwork.get('width', 3000)}x{track_artwork.get('height', 3000)}").replace('{f}', '.png') if track_cover_url else None

            items.append(MediaMetadata(
                type=MetadataType.METADATA,
                url=track_attrs['url'],
                title=track_attrs.get('name'),
                performer=track_attrs.get('artistName'),
                duration=track_attrs.get('durationInMillis', 0) // 1000,
                cover=track_cover,
                full_size_cover=track_full_cover,
                media_type='track'
            ))

        return MediaMetadata(
            type=MetadataType.METADATA,
            url=attrs.get('url'),
            title=attrs.get('name'),
            performer=attrs.get('artistName'),
            cover=cover,
            media_type='album',
            extra={
                'release_date': attrs.get('releaseDate'),
                'track_count': attrs.get('trackCount'),
                'record_label': attrs.get('recordLabel')
            },
            items=items
        )
