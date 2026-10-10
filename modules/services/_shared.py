"""Shared helpers for media services (tiktok, instagram, twitter, reddit, pixiv, pinterest)."""
import hashlib
import re
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.service_list import Services
from storage.db.crud import get_media_cache


def make_cache_key(prefix: str, url: str, id_regex: str, suffix: str = "") -> str:
    """`prefix:<id>` if id_regex matches url, else `prefix:<md5 of url without query>`."""
    match = re.search(id_regex, url)
    if match:
        key = match.group(1)
    else:
        clean_url = url.split('?')[0].rstrip('/')
        key = hashlib.md5(clean_url.encode('utf-8')).hexdigest()
    return f"{prefix}:{key}{suffix}"


async def cache_check(db_session: AsyncSession, key: str) -> list[MediaContent] | None:
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
                is_blurred=c_item.is_blurred if c_item.is_blurred is not None else cached.data.is_blurred,
                is_nsfw=c_item.is_nsfw if c_item.is_nsfw is not None else cached.data.is_nsfw
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
        is_blurred=cached.data.is_blurred,
        is_nsfw=cached.data.is_nsfw
    )]


def build_media_items(items: list[dict], caption: str, is_blurred: bool, is_nsfw: bool) -> list[MediaContent]:
    """Converts media-core `items` into MediaContent list."""
    media_content = []
    for media in items:
        m_type = media.get('type')
        if m_type == 'photo':
            type_val = MediaType.PHOTO
        elif m_type in ('gif', 'animated_gif'):
            type_val = MediaType.GIF
        else:
            type_val = MediaType.VIDEO

        cover_str = media.get('cover_path') or media.get('cover') or media.get('thumbnail')
        cover_path = Path(cover_str) if cover_str and Path(cover_str).exists() else None

        media_content.append(
            MediaContent(
                type=type_val,
                path=Path(media.get('path')) if media.get('path') else None,
                optimized_path=Path(media.get('optimized_path')) if media.get('optimized_path') else None,
                title=caption,
                width=media.get('width', None),
                height=media.get('height', None),
                duration=media.get('duration', None),
                cover=cover_path,
                is_blurred=is_blurred,
                is_nsfw=is_nsfw,
            )
        )
    return media_content


def ensure_nsfw_allowed(
    is_nsfw: bool,
    sponsor: bool,
    allow_nsfw: bool,
    url: str,
    service: Services,
    chat_code: ErrorCode = ErrorCode.NOT_ALLOWED,
) -> None:
    """NSFW is sponsor-only and must be allowed in the chat."""
    if not is_nsfw:
        return
    if not sponsor:
        raise BotError(
            code=ErrorCode.INVALID_URL,
            url=url,
            service=service,
            message="NSFW content is only available to sponsors",
            is_logged=False,
            critical=False
        )
    if not allow_nsfw:
        raise BotError(
            code=chat_code,
            url=url,
            service=service,
            message="NSFW content is not allowed in this chat",
            is_logged=False,
            critical=False
        )
