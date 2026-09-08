import hashlib
import logging
import re
from pathlib import Path


import httpx
from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.ext.asyncio import AsyncSession

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.service_list import Services
from senders.media_sender import MediaSender
from storage.db.crud import get_media_cache, check_if_user_premium
from tasks.task_manager import task_manager
from utils import truncate_string, escape_html, build_caption, format_author_link
from utils.statistics_helper import log_download_event

insta_router = Router(name="instagram")

logger = logging.getLogger(__name__)

INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reels?|tv)/[\w-]+/?"

@insta_router.message(F.text.regexp(INSTAGRAM_REGEX))
async def instagram_handler(message: Message, db_session: AsyncSession, http_client: httpx.AsyncClient,):
    match = re.search(INSTAGRAM_REGEX, message.text)
    url = match.group(0) if match else message.text
    user_id = message.from_user.id

    sponsor = await check_if_user_premium(db_session, user_id)

    async with ChatActionSender.choose_sticker(bot=message.bot, chat_id=message.chat.id):
        send_manager = MediaSender()
        cache_key = get_cache_key(url, sponsor)

        cached = await cache_check(db_session, cache_key)
        if cached:
            await send_manager.send(message, cached, service="instagram", db_session=db_session)
            return

    async with ChatActionSender.record_video_note(bot=message.bot, chat_id=message.chat.id):
        payload = {
            "user_id": user_id,
            "url": url,
            "sponsor": sponsor,
            "nsfw": False,
        }
        metadata = await task_manager.run_media_download(
            user_id=user_id,
            url=url,
            service=Services.INSTAGRAM,
            payload=payload,
            http_client=http_client,
        )

        author_data = metadata.get('author') if isinstance(metadata.get('author'), dict) else {}
        author_username = author_data.get('username') or metadata.get('author_username')
        author_name = author_data.get('name')
        author_url = author_data.get('url') or (f"https://www.instagram.com/{author_username}/" if author_username else "")
        author_display = author_username or author_name
        author_link = format_author_link(author_display, author_url, icon="👤")

        description = escape_html((metadata.get('caption') or metadata.get('title') or "").strip())
        caption = build_caption(header=author_link, description=description)

        is_nsfw = bool(metadata.get('is_nsfw') or metadata.get('is_sensitive'))
        is_blurred = bool(metadata.get('is_blurred') or is_nsfw)

        media_content = []
        for media in metadata.get('items', []):
            cover_str = media.get('cover_path') or media.get('cover') or media.get('thumbnail')
            cover_path = Path(cover_str) if cover_str and Path(cover_str).exists() else None
            media_content.append(
                MediaContent(
                    type=MediaType.PHOTO if media.get('type') == 'photo' else MediaType.VIDEO,
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

    if media_content:
        await send_manager.send(message, media_content, service="instagram", cache_key=cache_key, db_session=db_session)


def get_cache_key(url: str, sponsor: bool) -> str:
    # Try to extract shortcode: /p/ABC/, /reel/ABC/, /reels/ABC/, /tv/ABC/
    match = re.search(r"/(?:p|reels?|tv)/([A-Za-z0-9_-]+)", url)
    if match:
        if sponsor:
            return f"ig:{match.group(1)}:sponsor"
        else:
            return f"ig:{match.group(1)}"

    # Fallback for other formats, but at least strip query parameters
    clean_url = url.split('?')[0].rstrip('/')
    hashed = hashlib.md5(clean_url.encode('utf-8')).hexdigest()
    if sponsor:
        return f"ig:{hashed}:sponsor"
    else:
        return f"ig:{hashed}"


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