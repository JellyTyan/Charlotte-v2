import logging
import re

from curl_cffi.requests import AsyncSession

from core.config import Config
from models.errors import BotError, ErrorCode
from models.metadata import MediaMetadata, MetadataType
from models.service_list import Services
from utils.download_utils import download_file

from .auth import get_access_token, get_operation_hash

logger = logging.getLogger(__name__)


async def get_track_info(track_id: str, token_data: dict, session: AsyncSession):
    """Получение данных о треке через браузерный API"""
    logger.debug(f"Fetching track info from Spotify API: {track_id}")
    
    track_hash = await get_operation_hash(session, "getTrack")
    url = "https://api-partner.spotify.com/pathfinder/v2/query"
    
    headers = {
        'accept': 'application/json',
        'app-platform': 'WebPlayer',
        'authorization': f'Bearer {token_data["access_token"]}',
        'client-token': token_data["client_token"],
        'content-type': 'application/json;charset=UTF-8',
    }
    
    payload = {
        "variables": {"uri": f"spotify:track:{track_id}"},
        "operationName": "getTrack",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": track_hash
            }
        }
    }
    
    response = await session.post(url, headers=headers, json=payload)
    
    if response.status_code == 401:
        logger.debug("Token expired, refreshing...")
        token_data = await get_access_token(session)
        headers['authorization'] = f'Bearer {token_data["access_token"]}'
        headers['client-token'] = token_data["client_token"]
        response = await session.post(url, headers=headers, json=payload)
    
    if response.status_code != 200:
        logger.error(f"Failed to get track info: {response.status_code}, Response: {response.text[:500]}")
        raise BotError(
            code=ErrorCode.PLAYLIST_INFO_ERROR,
            message=f"Failed to get track info: {response.status_code}",
            service=Services.SPOTIFY,
            is_logged=True,
        )
    
    data = response.json()
    logger.debug(f"Track info received for: {track_id}")
    return data["data"]["trackUnion"]


async def get_spotify_author(track_id: str, token: str):
    logger.debug(f"Getting Spotify author for track: {track_id}")
    try:
        async with AsyncSession(impersonate="chrome124") as session:
            # Получаем новый токен с client_token
            token_data = await get_access_token(session)
            track_info = await get_track_info(track_id, token_data, session)

        # Парсим артистов из новой структуры: firstArtist + otherArtists
        artists = []
        
        # Добавляем первого артиста
        first_artist_items = track_info.get("firstArtist", {}).get("items", [])
        for artist_data in first_artist_items:
            name = artist_data.get("profile", {}).get("name")
            if name:
                artists.append(name)
        
        # Добавляем остальных артистов
        other_artists_items = track_info.get("otherArtists", {}).get("items", [])
        for artist_data in other_artists_items:
            name = artist_data.get("profile", {}).get("name")
            if name:
                artists.append(name)
        
        artist = ", ".join(artists) if artists else "Unknown Artist"
        title = track_info.get("name", "Unknown")
        cover_url = None
        
        album_cover = track_info.get("albumOfTrack", {}).get("coverArt", {}).get("sources", [])
        if album_cover:
            cover_url = album_cover[0]["url"]

        album_name = track_info.get("albumOfTrack", {}).get("name", "Uknown")
        date = track_info.get("albumOfTrack", {}).get("date", {}).get("isoString", "")[:10]
        
        logger.debug(f"Parsed track: {artist} - {title}")
        return {
            "artist": artist,
            "title": title,
            "cover_url": cover_url,
            "album_name": album_name,
            "date": date,

        }
        
    except Exception as e:
        logger.error(f"Error fetching track {track_id}: {e}", exc_info=True)
        raise BotError(
            code=ErrorCode.PLAYLIST_INFO_ERROR,
            message=f"Error fetching track {track_id}: {e}",
            service=Services.SPOTIFY,
            url=None,
            critical=True,
            is_logged=True
        )


async def get_set_list(set_id: str, type: str, token: str) -> MediaMetadata:
    """
    Get information about a Spotify playlist or album.

    Args:
        set_id (str): ID of the playlist or album
        type (str): Type of set - either 'album' or 'playlist'
        token (str): Spotify Bearer access token

    Returns:
        MediaMetadata: Metadata with list of tracks
    """
    logger.debug(f"Getting {type} tracks from: {set_id}")
    safe_set_id = re.sub(r'[^a-zA-Z0-9_-]', '', set_id)
    
    async with AsyncSession(impersonate="chrome124") as session:
        token_data = await get_access_token(session)
        
        if type == "album":
            return await _get_album_info(set_id, safe_set_id, token_data, session)
        elif type == "playlist":
            return await _get_playlist_info(set_id, safe_set_id, token_data, session)
        else:
            raise BotError(
                code=ErrorCode.PLAYLIST_INFO_ERROR,
                message=f"Invalid type: {type}",
                service=Services.SPOTIFY,
                url=set_id,
                critical=True,
                is_logged=True
            )


async def _get_album_info(album_id: str, safe_id: str, token_data: dict, session: AsyncSession) -> MediaMetadata:
    album_hash = await get_operation_hash(session, "getAlbum")
    url = "https://api-partner.spotify.com/pathfinder/v2/query"
    
    headers = {
        'accept': 'application/json',
        'app-platform': 'WebPlayer',
        'authorization': f'Bearer {token_data["access_token"]}',
        'client-token': token_data["client_token"],
        'content-type': 'application/json;charset=UTF-8',
    }
    
    payload = {
        "variables": {"uri": f"spotify:album:{album_id}", "locale": "", "offset": 0, "limit": 50},
        "operationName": "getAlbum",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": album_hash
            }
        }
    }
    
    response = await session.post(url, headers=headers, json=payload)
    if response.status_code != 200:
        raise BotError(
            code=ErrorCode.PLAYLIST_INFO_ERROR,
            message=f"Failed to get album: {response.status_code}",
            service=Services.SPOTIFY,
            is_logged=True,
        )
    
    data = response.json()["data"]["albumUnion"]
    
    # Получаем обложку альбома сразу
    album_cover_url = None
    cover_sources = data.get("coverArt", {}).get("sources", [])
    if cover_sources:
        album_cover_url = cover_sources[0]["url"]
    
    items = []
    # В альбоме треки находятся в tracksV2.items, и каждый элемент имеет поле track
    for track_item in data.get("tracksV2", {}).get("items", []):
        track = track_item.get("track")
        if not track:
            continue
        
        # Парсим артистов
        artists = []
        for artist in track.get("artists", {}).get("items", []):
            name = artist.get("profile", {}).get("name")
            if name:
                artists.append(name)
        artist = ", ".join(artists) if artists else "Unknown Artist"
        
        track_id = track["uri"].split(":")[-1]
        
        items.append(MediaMetadata(
            type=MetadataType.METADATA,
            url=f"https://open.spotify.com/track/{track_id}",
            title=track.get("name", "Unknown"),
            performer=artist,
            cover=album_cover_url,
            media_type="track",
            extra={
                "duration_ms": track.get("duration", {}).get("totalMilliseconds", 0),
                "track_number": track.get("trackNumber", 0),
                "disc_number": track.get("discNumber", 1)
            }
        ))
    
    # Получаем информацию об альбоме
    artists = []
    for artist in data.get("artists", {}).get("items", []):
        name = artist.get("profile", {}).get("name")
        if name:
            artists.append(name)
    artist_name = ", ".join(artists) if artists else "Unknown Artist"
    
    # Скачиваем обложку альбома для метаданных
    cover_url = None
    if album_cover_url:
        cover = await download_file(album_cover_url, f"storage/temp/spotify_album_{safe_id}.jpg")
        if cover:
            cover_url = str(cover)
    
    return MediaMetadata(
        type=MetadataType.METADATA,
        url=f"https://open.spotify.com/album/{album_id}",
        title=data.get("name", "Unknown Album"),
        performer=artist_name,
        cover=cover_url,
        media_type="album",
        extra={
            "release_date": data.get("date", {}).get("isoString"),
            "total_tracks": len(items)
        },
        items=items
    )


async def _get_playlist_info(playlist_id: str, safe_id: str, token_data: dict, session: AsyncSession) -> MediaMetadata:
    url = "https://api-partner.spotify.com/pathfinder/v2/query"
    
    headers = {
        'accept': 'application/json',
        'app-platform': 'WebPlayer',
        'authorization': f'Bearer {token_data["access_token"]}',
        'client-token': token_data["client_token"],
        'content-type': 'application/json;charset=UTF-8',
    }
    
    # Сначала получаем метаданные плейлиста
    playlist_payload = {
        "variables": {
            "uri": f"spotify:playlist:{playlist_id}",
            "offset": 0,
            "limit": 1,
            "enableWatchFeedEntrypoint": False
        },
        "operationName": "fetchPlaylist",
        "extensions": {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": "346811f856fb0b7e4f6c59f8ebea78dd081c6e2fb01b77c954b26259d5fc6763"
            }
        }
    }
    
    response = await session.post(url, headers=headers, json=playlist_payload)
    if response.status_code != 200:
        raise BotError(
            code=ErrorCode.PLAYLIST_INFO_ERROR,
            message=f"Failed to get playlist metadata: {response.status_code}",
            service=Services.SPOTIFY,
            is_logged=True,
        )
    
    playlist_meta = response.json()["data"]["playlistV2"]
    total_count = playlist_meta["content"]["totalCount"]
    
    # Теперь получаем треки
    items = []
    offset = 0
    limit = 50
    
    while offset < total_count:
        tracks_payload = {
            "variables": {
                "uri": f"spotify:playlist:{playlist_id}",
                "offset": offset,
                "limit": limit,
                "enableWatchFeedEntrypoint": False
            },
            "operationName": "fetchPlaylist",
            "extensions": {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": "346811f856fb0b7e4f6c59f8ebea78dd081c6e2fb01b77c954b26259d5fc6763"
                }
            }
        }
        
        response = await session.post(url, headers=headers, json=tracks_payload)
        if response.status_code != 200:
            logger.warning(f"Failed to fetch tracks at offset {offset}: {response.status_code}")
            break
        
        data = response.json()["data"]["playlistV2"]
        
        for item in data["content"]["items"]:
            track_data = None
            if "itemV2" in item and "data" in item["itemV2"]:
                track_data = item["itemV2"]["data"]

            if not track_data or not track_data.get("uri", "").startswith("spotify:track:"):
                continue
            
            track_id = track_data["uri"].split(":")[-1]
            
            # Парсим артистов
            artists = []
            for artist in track_data.get("artists", {}).get("items", []):
                name = artist.get("profile", {}).get("name")
                if name:
                    artists.append(name)
            artist = ", ".join(artists) if artists else "Unknown Artist"
            
            # Получаем обложку
            cover_url = None
            cover_sources = track_data.get("albumOfTrack", {}).get("coverArt", {}).get("sources", [])
            if cover_sources:
                cover_url = cover_sources[0]["url"]
            
            items.append(MediaMetadata(
                type=MetadataType.METADATA,
                url=f"https://open.spotify.com/track/{track_id}",
                title=track_data.get("name", "Unknown"),
                performer=artist,
                cover=cover_url,
                media_type="track",
                extra={
                    "duration_ms": track_data.get("trackDuration", {}).get("totalMilliseconds", 0)
                }
            ))
        
        offset += limit
    
    # Обрабатываем обложку плейлиста
    cover_url = None
    if playlist_meta.get("images", {}).get("items"):
        cover_sources = playlist_meta["images"]["items"][0].get("sources", [])
        if cover_sources:
            cover_url = cover_sources[0]["url"]
            cover = await download_file(cover_url, f"storage/temp/spotify_playlist_{safe_id}.jpg")
            if cover:
                cover_url = str(cover)
    
    return MediaMetadata(
        type=MetadataType.METADATA,
        url=f"https://open.spotify.com/playlist/{playlist_id}",
        title=playlist_meta.get("name", "Unknown Playlist"),
        description=playlist_meta.get("description", ""),
        performer=playlist_meta.get("ownerV2", {}).get("data", {}).get("name", "Unknown"),
        cover=cover_url,
        media_type="playlist",
        extra={"total_tracks": total_count},
        items=items
    )

async def fetch_spotify_token(config: Config):
    logger.debug("Fetching new Spotify browser access token")
    try:
        async with AsyncSession(impersonate="chrome124") as session:
            token_data = await get_access_token(session)
        logger.debug("Spotify token fetched successfully")
        return {"token": token_data["access_token"]}
    except Exception as e:
        logger.error(f"Failed to fetch Spotify token: {e}")
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to fetch Spotify token: {e}",
            service=Services.SPOTIFY,
            critical=True,
            is_logged=True
        )
