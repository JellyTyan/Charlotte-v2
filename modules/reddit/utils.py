import logging
import hashlib
import re
from curl_cffi.requests import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as DbAsyncSession
from storage.db.crud import get_media_cache
from models.media import MediaContent, MediaType
from models.errors import BotError, ErrorCode
from models.service_list import Services

logger = logging.getLogger(__name__)

async def get_post_info(url: str):
    """Get post information from URL."""
    async with AsyncSession(impersonate="chrome136") as session:
        # Remove query params, trailing slash, and any existing .json, then add .json?limit=1
        response = await session.get(url)
        clean_url = response.url.split('?')[0].rstrip('/')
        if clean_url.endswith('.json'):
            clean_url = clean_url[:-5]
        api_url = clean_url + '.json?limit=1'


        headers = {
            "Accept": "application/json, text/plain, */*",
        }

        response = await session.get(api_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Reddit API returned status {response.status_code} for {api_url}")
            raise BotError(ErrorCode.INTERNAL_ERROR, message="Invalid URL", service=Services.REDDIT, url=url, is_logged=True)

        data = response.json()
        if not data or not isinstance(data, list) or len(data) == 0:
            logger.error(f"Invalid Reddit response structure: {data}")
            raise BotError(ErrorCode.INTERNAL_ERROR, message="Invalid response", service=Services.REDDIT, url=url, is_logged=True)

        return data[0]["data"]["children"][0]["data"]

def get_cache_key(url: str) -> str:
    # Try to extract Post ID: /comments/ABC or /gallery/ABC or /s/ABC
    match = re.search(r"/(?:comments|gallery|s)/([A-Za-z0-9_-]+)", url)
    if match:
        return f"rd:{match.group(1)}"
        
    # Fallback and parameter stripping
    clean_url = url.split('?')[0].rstrip('/')
    hashed = hashlib.md5(clean_url.encode('utf-8')).hexdigest()
    return f"rd:{hashed}"

async def cache_check(db_session: DbAsyncSession, key: str) -> list[MediaContent] | None:
    cached = await get_media_cache(db_session, key)
    if not cached:
        return None

    if cached.media_type == "gallery":
        results = []
        for c_item in cached.data.items:
            t_type = MediaType(c_item.media_type) if c_item.media_type else MediaType.PHOTO
            results.append(MediaContent(
                type=t_type,
                telegram_file_id=c_item.file_id,
                telegram_document_file_id=c_item.raw_file_id,
                cover_file_id=c_item.cover,
                full_cover_file_id=cached.data.full_cover,
                title=cached.data.title,
                performer=cached.data.author,
                duration=c_item.duration or cached.data.duration,
                width=c_item.width or cached.data.width,
                height=c_item.height or cached.data.height,
                is_blurred=c_item.is_blurred if c_item.is_blurred is not None else cached.data.is_blurred
            ))
        return results

    try:
        media_type = MediaType(cached.media_type)
    except ValueError:
        media_type = MediaType.VIDEO if cached.data.width else MediaType.PHOTO
        
    return [MediaContent(
        type=media_type,
        telegram_file_id=cached.telegram_file_id,
        telegram_document_file_id=cached.telegram_document_file_id,
        cover_file_id=cached.data.cover,
        full_cover_file_id=cached.data.full_cover,
        title=cached.data.title,
        performer=cached.data.author,
        duration=cached.data.duration,
        width=cached.data.width,
        height=cached.data.height,
        is_blurred=cached.data.is_blurred
    )]
