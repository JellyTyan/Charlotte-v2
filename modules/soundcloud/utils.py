from curl_cffi.requests import AsyncSession
import re
from models.metadata import MediaMetadata, MetadataType
from storage.cache.redis_client import cache_get, cache_set

def get_cover_url(info_dict: dict):
    """
    Extracts the cover URL from the track's information.

    Parameters:
    ----------
    info_dict : dict
        The information dictionary for the SoundCloud track.

    Returns:
    -------
    str or None
        The URL of the cover image, or None if no appropriate image is found.
    """
    thumbnails = info_dict.get("thumbnails", [])
    return next(
        (
            thumbnail["url"]
            for thumbnail in thumbnails
            if thumbnail.get("width") == 500
        ),
        None,
    )

async def get_auth_token(session: AsyncSession) -> str:
    cached_token = await cache_get("soundcloud:token")
    if cached_token:
        token = cached_token.get("token")
        try:
            test_resp = await session.get(f"https://api-v2.soundcloud.com/tracks/1?client_id={token}")
            if test_resp.status_code != 401:
                return token
        except:
            pass

    resp = await session.get("https://soundcloud.com")
    html = resp.text
    script_urls = re.findall(r'src="(https://[a-z0-9-]+\.sndcdn\.com/assets/[^"]+\.js)"', html)

    if not script_urls:
        raise Exception("Scripts are not founded")

    for script_url in reversed(script_urls):
        try:
            js_code = await session.get(script_url)
            js_code = js_code.text

            match = re.search(r'client_id:"([a-zA-Z0-9]{32})"', js_code)

            if match:
                key = match.group(1)
                await cache_set("soundcloud:token", {"token": key}, ttl=86400)
                return key

        except Exception as e:
            print(f"Error when loading {script_url}: {e}")
            continue

    raise Exception("Key not founded")


async def get_song_info(id: int):
    async with AsyncSession(impersonate="chrome136") as session:
        token = await get_auth_token(session)
        params = {
            "client_id": token
        }
        url = f"https://api-v2.soundcloud.com/tracks/{id}?client_id={token}"
        response = await session.get(url, params=params)
        data = response.json()

        return MediaMetadata(
            type=MetadataType.METADATA,
            url=url,
            title=data.get('title'),
            description=data.get('description'),
            duration=data.get('full_duration', 0) // 1000,
            cover=data.get('artwork_url'),
            performer=data.get('publisher_metadata', {}).get('artist'),
            performer_url=data.get('user', {}).get('permalink_url'),
            media_type='track'
        )

async def get_playlist_info(id: int):
    async with AsyncSession(impersonate="chrome136") as session:
        token = await get_auth_token(session)
        params = {
            "client_id": token
        }
        url = f"https://api-v2.soundcloud.com/playlists/{id}?representation=full&client_id={token}"
        response = await session.get(url, params=params)
        data = response.json()
        items = []
        for track in data.get('tracks', []):
            if not track.get('permalink_url'):
                items.append(await get_song_info(track.get('id')))
            else:
                items.append(MediaMetadata(
                    type=MetadataType.METADATA,
                    url=track.get('permalink_url', ''),
                    title=track.get('title'),
                    duration=track.get('full_duration', 0) // 1000,
                    cover=track.get('artwork_url'),
                    performer=data.get('publisher_metadata', {}).get('artist'),
                    media_type='track'
                ))
        return MediaMetadata(
            type=MetadataType.METADATA,
            url=url,
            title=data.get('title'),
            description=data.get('description'),
            duration=data.get('duration', 0) // 1000,
            cover=data.get('artwork_url'),
            performer=data.get('user', {}).get('username'),
            performer_url=data.get('user', {}).get('permalink_url'),
            media_type='playlist',
            items=items,
        )
