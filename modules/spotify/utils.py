import logging
import re

import httpx

from core.config import Config
from models.errors import BotError, ErrorCode
from models.metadata import MediaMetadata, MetadataType
from utils import get_ytdlp_options, random_cookie_file
from utils.download_utils import download_file

from .auth import get_access_token

logger = logging.getLogger(__name__)


def get_audio_options():
    opts = get_ytdlp_options()
    opts["format"] = "bestaudio"
    opts["outtmpl"] = "storage/temp/%(title)s.%(ext)s"
    opts["postprocessors"] = [
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
        }
    ]

    cookie_file = random_cookie_file("youtube")
    if cookie_file:
        opts["cookiefile"] = cookie_file

    return opts


async def get_track_info(track_id: str, token: str):
    """Получение данных о треке по его ID"""
    url = f"https://api.spotify.com/v1/tracks/{track_id}"
    logger.debug(f"Fetching track info from Spotify API: {track_id}")

    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.get(url, headers=headers)
        response.raise_for_status()
        logger.debug(f"Track info received for: {track_id}")
        return response.json()


async def get_spotify_author(track_id: str, token: str):
    logger.debug(f"Getting Spotify author for track: {track_id}")
    try:
        track_info = await get_track_info(track_id, token)

        artist = ", ".join(artist["name"] for artist in track_info.get("artists", []))
        title = track_info.get("name", "Unknown")
        cover_url = None
        if track_info.get("album") and track_info["album"].get("images"):
            cover_url = track_info["album"]["images"][0]["url"]
        logger.debug(f"Parsed track: {artist} - {title}")

        return artist, title, cover_url
    except Exception as e:
        logger.error(f"Error fetching track {track_id}: {e}")
        raise BotError(
            code=ErrorCode.PLAYLIST_INFO_ERROR,
            message=f"Error fetching track {track_id}: {e}",
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
        list[str]: List of track URLs from the playlist/album
    """
    logger.debug(f"Getting playlist tracks from: {set_id}")

    # Sanitize set_id to prevent path traversal
    safe_set_id = re.sub(r'[^a-zA-Z0-9_-]', '', set_id)

    headers = {"Authorization": f"Bearer {token}"}

    try:
        if type == "album":
            url = f"https://api.spotify.com/v1/albums/{set_id}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    raise BotError(
                        code=ErrorCode.PLAYLIST_INFO_ERROR,
                        message=f"Error fetching playlist tracks: {response.text}",
                        url=url,
                        critical=True,
                        is_logged=True
                    )

                data = response.json()

            items = []
            for track in data["tracks"]["items"]:
                items.append(MediaMetadata(
                    type=MetadataType.METADATA,
                    url=track["external_urls"]["spotify"],
                    title=track["name"],
                    performer=data["artists"][0]["name"],
                    cover=data["images"][0]["url"],
                    media_type="track",
                    extra={
                        "duration_ms": track["duration_ms"],
                        "track_number": track["track_number"],
                        "disc_number": track["disc_number"]
                    }
                ))

            cover = await download_file(data["images"][0]["url"], f"storage/temp/spotify_album_{safe_set_id}.jpg")
            if cover:
                cover = str(cover)

            return MediaMetadata(
                type=MetadataType.METADATA,
                url=data["external_urls"]["spotify"],
                title=data["name"],
                performer=data["artists"][0]["name"],
                performer_url=data["artists"][0]["external_urls"]["spotify"],
                cover=cover,
                media_type="album",
                extra={
                    "release_date": data["release_date"],
                    "genres": data["genres"],
                    "total_tracks": data["total_tracks"]
                },
                items=items
            )

        elif type == "playlist":
            url = f"https://api.spotify.com/v1/playlists/{set_id}"

            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                if response.status_code != 200:
                    raise BotError(
                        code=ErrorCode.PLAYLIST_INFO_ERROR,
                        message=f"Error fetching playlist tracks: {response.text}",
                        url=url,
                        critical=True,
                        is_logged=True
                    )

                data = response.json()

            items = []
            tracks_data = data["tracks"]

            # Fetch all pages of tracks
            while tracks_data:
                for item in tracks_data["items"]:
                    track = item["track"]
                    if not track:
                        continue

                    items.append(MediaMetadata(
                        type=MetadataType.METADATA,
                        url=track["external_urls"]["spotify"],
                        title=track["name"],
                        performer=", ".join(artist["name"] for artist in track["artists"]),
                        cover=track["album"]["images"][0]["url"] if track["album"]["images"] else None,
                        media_type="track",
                        extra={
                            "duration_ms": track["duration_ms"],
                            "track_number": track.get("track_number"),
                            "disc_number": track.get("disc_number")
                        }
                    ))

                # Fetch next page if available
                if tracks_data.get("next"):
                    async with httpx.AsyncClient() as client:
                        response = await client.get(tracks_data["next"], headers=headers)
                        if response.status_code == 200:
                            tracks_data = response.json()
                        else:
                            break
                else:
                    break

            cover = await download_file(data["images"][0]["url"], f"storage/temp/spotify_playlist_{safe_set_id}.jpg") if data["images"] else None
            if cover:
                cover = str(cover)

            return MediaMetadata(
                type=MetadataType.METADATA,
                url=data["external_urls"]["spotify"],
                title=data["name"],
                description=data.get("description"),
                performer=data["owner"]["display_name"],
                performer_url=data["owner"]["external_urls"]["spotify"],
                cover=cover,
                media_type="playlist",
                extra={
                    "total_tracks": data["tracks"]["total"]
                },
                items=items
            )
        else:
            raise BotError(
                code=ErrorCode.PLAYLIST_INFO_ERROR,
                message=f"Invalid playlist type: {type}",
                url=set_id,
                critical=True,
                is_logged=True
            )

    except BotError:
        raise
    except Exception as e:
        logger.error(f"Error fetching playlist tracks: {e}")
        raise BotError(
            code=ErrorCode.PLAYLIST_INFO_ERROR,
            message=f"Error fetching playlist tracks: {e}",
            url=set_id,
            critical=True,
            is_logged=True
        )

async def fetch_spotify_token(config: Config):
    logger.debug("Fetching new Spotify access token")
    try:
        async with httpx.AsyncClient() as client:
            token = await get_access_token(client, config.SPOTIFY_CLIENT_ID, config.SPOTIFY_SECRET)
        logger.debug("Spotify token fetched successfully")
        return {"token": token}
    except Exception as e:
        logger.error(f"Failed to fetch Spotify token: {e}")
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to fetch Spotify token: {e}",
            critical=True,
            is_logged=True
        )
