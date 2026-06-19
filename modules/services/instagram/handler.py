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
from utils import truncate_string, escape_html
from utils.statistics_helper import log_download_event

insta_router = Router(name="instagram")

logger = logging.getLogger(__name__)

INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reels?|tv)/[\w-]+/?"

@insta_router.message(F.text.regexp(INSTAGRAM_REGEX))
async def instagram_handler(message: Message, db_session: AsyncSession, http_client: httpx.AsyncClient,):
    url = message.text
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
            "url": url,
            "sponsor": sponsor,
        }
        res = await task_manager.run_download(
            user_id=user_id,
            url=url,
            coro=http_client.post(
                "http://media-core:9546/download/instagram", json=payload,
            ),
        )

        err_msg = res.text.lower() if res.text else ""
        if res.status_code == 451 or "geo" in err_msg or "country" in err_msg or "region" in err_msg:
            raise BotError(
                code=ErrorCode.REGION_RESTRICTED,
                url=url,
                service=Services.INSTAGRAM,
                message=f"Download Error:\n {res.text}",
                is_logged=False,
                critical=False,
            )

        if res.status_code == 401:
            raise BotError(
                code=ErrorCode.AGE_RESTRICTED,
                url=url,
                service=Services.INSTAGRAM,
                message=f"Download Error:\n {res.text}",
                is_logged=True,
                critical=False,
            )

        if res.status_code == 404:
            raise BotError(
                code=ErrorCode.NOT_FOUND,
                url=url,
                service=Services.INSTAGRAM,
                message=f"Download Error:\n {res.text}",
                is_logged=True,
                critical=False,
            )

        if res.status_code != 200:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                url=url,
                service=Services.INSTAGRAM,
                message=f"Download Error:\n {res.text}",
                is_logged=True,
                critical=True,
            )
        metadata = res.json()["data"]

        author_username = metadata.get('author_username')
        description = escape_html((metadata.get('caption') or "").strip())
        author_link = f"<a href='https://www.instagram.com/{author_username}/'>{author_username}</a>" if author_username else ""
        parts = [p for p in [author_link, description] if p]
        caption = " - ".join(parts)

        media_content = []
        for media in metadata.get('items', []):
            media_content.append(
                MediaContent(
                    type=MediaType.PHOTO if media.get('type') == 'photo' else MediaType.VIDEO,
                    path=Path(media.get('path')) if media.get('path') else None,
                    optimized_path=Path(media.get('optimized_path')) if media.get('optimized_path') else None,
                    title=truncate_string(caption, 1024),
                    width=media.get('width', None),
                    height=media.get('height', None),
                    duration=media.get('duration', None),
                    cover=Path(media.get('cover')) if media.get('cover') else None,
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