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
from storage.db.crud import get_media_cache, check_if_user_premium, get_chat_settings
from tasks.task_manager import task_manager
from utils import escape_html, truncate_string
from utils.statistics_helper import log_download_event

reddit_router = Router(name="reddit")

logger = logging.getLogger(__name__)

REDDIT_REGEX = r"https?:\/\/(?:www\.|old\.|new\.)?reddit\.com\/(?:r\/[A-Za-z0-9_]+\/)?(?:comments\/[A-Za-z0-9]+(?:\/[^\/\s?]+)?|s\/[A-Za-z0-9]+|gallery\/[A-Za-z0-9]+)(?:\/)?"


@reddit_router.message(F.text.regexp(REDDIT_REGEX))
async def reddit_handler(
    message: Message,
    db_session: AsyncSession,
    http_client: httpx.AsyncClient,
):
    if not message.text or not message.from_user:
        return

    url = message.text.strip()
    chat_id = message.chat.id
    user_id = message.from_user.id

    if "/s/" in url:
        try:
            res = await http_client.head(url, follow_redirects=True, timeout=5.0)
            url = str(res.url)
        except Exception:
            pass

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
                        service=Services.REDDIT,
                        message="NSFW content is only available to sponsors",
                        is_logged=False,
                        critical=False
                    )
                if not allow_nsfw:
                    raise BotError(
                        code=ErrorCode.NOT_ALLOWED,
                        url=url,
                        service=Services.REDDIT,
                        message="NSFW content is not allowed in this chat",
                        is_logged=False,
                        critical=False
                    )
            await send_manager.send(message, cached, service="reddit", db_session=db_session)
            return

    async with ChatActionSender.record_video_note(bot=message.bot, chat_id=chat_id):
        payload = {
            "url": url,
            "sponsor": sponsor,
            "nsfw": allow_nsfw
        }
        res = await task_manager.run_download(
            user_id=user_id,
            url=url,
            coro=http_client.post(
                "http://media-core:9546/download/reddit", json=payload,
            ),
        )

        if res.status_code == 400:
            raise BotError(
                code=ErrorCode.INVALID_URL,
                url=url,
                service=Services.REDDIT,
                message=f"Download Error:\n {res.text}",
                is_logged=True,
                critical=False,
            )

        if res.status_code == 403:
            raise BotError(
                code=ErrorCode.INVALID_URL if not sponsor else ErrorCode.NOT_ALLOWED,
                url=url,
                service=Services.REDDIT,
                message=f"Download Error:\n {res.text}",
                is_logged=False,
                critical=False,
            )

        if res.status_code == 413:
            raise BotError(
                code=ErrorCode.LARGE_FILE,
                url=url,
                service=Services.REDDIT,
                message=f"Download Error:\n {res.text}",
                is_logged=True,
                critical=False,
            )

        if res.status_code == 404:
            raise BotError(
                code=ErrorCode.NOT_FOUND,
                url=url,
                service=Services.REDDIT,
                message=f"Download Error:\n {res.text}",
                is_logged=True,
                critical=False,
            )

        if res.status_code != 200:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                url=url,
                service=Services.REDDIT,
                message=f"Download Error:\n {res.text}",
                is_logged=True,
                critical=True,
            )

        metadata = res.json()["data"]

        # Check NSFW status from response
        is_nsfw = (
            metadata.get('nsfw') or
            metadata.get('possibly_sensitive') or
            metadata.get('is_blurred') or
            any(
                item.get('nsfw') or
                item.get('possibly_sensitive') or
                item.get('is_blurred')
                for item in metadata.get('items', [])
            )
        )

        # If content is NSFW
        if is_nsfw:
            if not sponsor:
                raise BotError(
                    code=ErrorCode.INVALID_URL,
                    url=url,
                    service=Services.REDDIT,
                    message="NSFW content is not allowed",
                    is_logged=False,
                    critical=False
                )
            if not allow_nsfw:
                raise BotError(
                    code=ErrorCode.NOT_ALLOWED,
                    url=url,
                    service=Services.REDDIT,
                    message="NSFW content is not allowed",
                    is_logged=False,
                    critical=False
                )

        author_username = metadata.get('author_username')
        subreddit = metadata.get('subreddit')
        description = escape_html((metadata.get('caption') or "").strip())
        
        author_link = f"<a href='https://www.reddit.com/user/{author_username}'>{author_username}</a>" if author_username else ""
        subreddit_link = f"<a href='https://www.reddit.com/{subreddit}'>{subreddit}</a>" if subreddit else ""
        
        header = ""
        if author_link and subreddit_link:
            header = f"{author_link} on {subreddit_link}"
        elif author_link:
            header = author_link
        elif subreddit_link:
            header = subreddit_link
            
        parts = [p for p in [header, description] if p]
        caption = "\n".join(parts)

        media_content = []
        for media in metadata.get('items', []):
            m_type = media.get('type')
            if m_type == 'photo':
                type_val = MediaType.PHOTO
            elif m_type in ('gif', 'animated_gif'):
                type_val = MediaType.GIF
            else:
                type_val = MediaType.VIDEO

            media_content.append(
                MediaContent(
                    type=type_val,
                    path=Path(media.get('path')) if media.get('path') else None,
                    optimized_path=Path(media.get('optimized_path')) if media.get('optimized_path') else None,
                    title=truncate_string(caption, 1024),
                    width=media.get('width', None),
                    height=media.get('height', None),
                    duration=media.get('duration', None),
                    cover=Path(media.get('cover')) if media.get('cover') else None,
                    is_blurred=is_nsfw,
                    is_nsfw=is_nsfw,
                )
            )

    if media_content:
        await send_manager.send(message, media_content, service="reddit", cache_key=cache_key, db_session=db_session)


def get_cache_key(url: str) -> str:
    match = re.search(r"(?:comments|gallery)/([A-Za-z0-9_]+)", url)
    if match:
        return f"rd:{match.group(1)}"

    clean_url = url.split('?')[0].rstrip('/')
    hashed = hashlib.md5(clean_url.encode('utf-8')).hexdigest()
    return f"rd:{hashed}"


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
