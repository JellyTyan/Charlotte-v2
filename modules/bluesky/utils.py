import re
from urllib.parse import quote
from curl_cffi.requests import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as DbAsyncSession

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from storage.db.crud import get_media_cache

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

def get_cache_key(url: str) -> str | None:
    match = re.search(r"bsky\.app/profile/[^/]+/post/([a-z0-9]+)", url)
    if not match:
        return None
    return f"bsky:{match.group(1)}"

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