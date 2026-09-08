import hashlib
import logging
import re
from pathlib import Path


import httpx
from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Config
from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.service_list import Services
from senders.media_sender import MediaSender
from storage.db.crud import get_media_cache, check_if_user_premium, get_chat_settings
from tasks.task_manager import task_manager
from utils import escape_html, truncate_string, build_caption, format_author_link
from utils.statistics_helper import log_download_event

twitter_router = Router(name="twitter")

logger = logging.getLogger(__name__)

TWITTER_REGEX = r"https?://(?:twitter|x)\.com/\w+/status/\d+"


@twitter_router.message(F.text.regexp(TWITTER_REGEX))
async def twitter_handler(
    message: Message,
    db_session: AsyncSession,
    http_client: httpx.AsyncClient,
    config: Config,
):
    if not message.text or not message.from_user:
        return

    match = re.search(TWITTER_REGEX, message.text)
    url = match.group(0) if match else message.text.strip()
    chat_id = message.chat.id
    user_id = message.from_user.id

    sponsor = await check_if_user_premium(db_session, user_id)

    async with ChatActionSender.choose_sticker(bot=message.bot, chat_id=chat_id):
        send_manager = MediaSender()
        cache_key = get_cache_key(url)

        allow_nsfw = True
        if chat_id < 0:
            settings = await get_chat_settings(db_session, chat_id)
            allow_nsfw = settings.profile.allow_nsfw

        cached = await cache_check(db_session, cache_key)
        if cached:
            is_nsfw = any(item.is_nsfw for item in cached)
            if is_nsfw:
                if not sponsor:
                    raise BotError(
                        code=ErrorCode.INVALID_URL,
                        url=url,
                        service=Services.TWITTER,
                        message="NSFW content is only available to sponsors",
                        is_logged=False,
                        critical=False
                    )
                if not allow_nsfw:
                    raise BotError(
                        code=ErrorCode.NOT_ALLOWED,
                        url=url,
                        service=Services.TWITTER,
                        message="NSFW content is not allowed in this chat",
                        is_logged=False,
                        critical=False
                    )
            await send_manager.send(message, cached, service="twitter", db_session=db_session)
            return

    async with ChatActionSender.record_video_note(bot=message.bot, chat_id=chat_id):
        payload = {
            "user_id": user_id,
            "url": url,
            "sponsor": sponsor,
            "nsfw": allow_nsfw,
        }
        metadata = await task_manager.run_media_download(
            user_id=user_id,
            url=url,
            service=Services.TWITTER,
            payload=payload,
            http_client=http_client,
        )

        # Check NSFW status from response
        is_nsfw = bool(metadata.get('is_nsfw') or metadata.get('is_sensitive'))
        is_blurred = bool(metadata.get('is_blurred') or is_nsfw)

        # If content is NSFW
        if is_nsfw:
            if not sponsor:
                raise BotError(
                    code=ErrorCode.INVALID_URL,
                    url=url,
                    service=Services.TWITTER,
                    message="NSFW content is not allowed",
                    is_logged=False,
                    critical=False
                )
            if not allow_nsfw:
                raise BotError(
                    code=ErrorCode.NOT_ALLOWED,
                    url=url,
                    service=Services.TWITTER,
                    message="NSFW content is not allowed",
                    is_logged=False,
                    critical=False
                )

        author_data = metadata.get('author') if isinstance(metadata.get('author'), dict) else {}
        author_username = author_data.get('username') or metadata.get('author_username')
        author_name = author_data.get('name')
        author_url = author_data.get('url') or (f"https://x.com/{author_username}" if author_username else "")
        author_display = author_name or author_username
        author_link = format_author_link(author_display, author_url, icon="👤")

        description = escape_html((metadata.get('caption') or metadata.get('title') or "").strip())
        caption = build_caption(header=author_link, description=description)

        media_content = []
        for media in metadata.get('items', []):
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

    if media_content:
        await send_manager.send(message, media_content, service="twitter", cache_key=cache_key, db_session=db_session)


def get_cache_key(url: str) -> str:
    match = re.search(r"status/(\d+)", url)
    if match:
        return f"tw:{match.group(1)}"

    clean_url = url.split('?')[0].rstrip('/')
    hashed = hashlib.md5(clean_url.encode('utf-8')).hexdigest()
    return f"tw:{hashed}"


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
