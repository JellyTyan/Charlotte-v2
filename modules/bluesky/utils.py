import logging
import re
import asyncio
import yt_dlp

from curl_cffi.requests import AsyncSession
from concurrent.futures import ThreadPoolExecutor
from models.errors import BotError, ErrorCode
from urllib.parse import quote

logger = logging.getLogger(__name__)

download_executor = ThreadPoolExecutor(max_workers=10)

async def get_post_info(post_id: str, author_username: str, client: AsyncSession) -> dict:
    headers = {
        'Origin': 'https://bsky.app',
        'Referer': 'https://bsky.app/',
    }

    at_uri = f'at://{author_username}/app.bsky.feed.post/{post_id}'
    encoded_uri = quote(at_uri, safe='')

    post_info_url = f'https://public.api.bsky.app/xrpc/app.bsky.unspecced.getPostThreadV2?anchor={encoded_uri}'

    response = await client.get(post_info_url, headers=headers)

    if response.status_code == 200:
        return response.json()
    else:
        raise BotError(
            code=ErrorCode.DOWNLOAD_FAILED,
            message=f"Failed to get bluesky info: response status {response.status_code}",
            url=str(encoded_uri),
            critical=True,
        )

async def download_m3u8_video(url: str, filename: str) -> None:
    try:
        ydl_opts = {'outtmpl': filename}
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await loop.run_in_executor(
                download_executor,
                lambda: ydl.download([url])
            )
    except Exception as e:
        raise BotError(
            code=ErrorCode.DOWNLOAD_FAILED,
            message=f"Failed to download M3U8 video: {e}",
            url=url,
            critical=True,
            is_logged=True,
        )

def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", filename)
