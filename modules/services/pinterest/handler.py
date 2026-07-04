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
from storage.db.crud import get_media_cache
from tasks.task_manager import task_manager
from utils import escape_html, truncate_string
from utils.statistics_helper import log_download_event

pinterest_router = Router(name="pinterest")

logger = logging.getLogger(__name__)

PINTEREST_REGEX = r"https?://(?:www\.)?(?:pinterest\.com/[\w/-]+|pin\.it/[A-Za-z0-9]+)"


async def resolve_pinterest_url(url: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            res = await client.get(url, headers=headers, follow_redirects=True, timeout=10)
            return str(res.url)
    except Exception as e:
        logger.warning(f"Failed to resolve Pinterest URL {url}: {e}")
        return url


@pinterest_router.message(F.text.regexp(PINTEREST_REGEX))
async def pinterest_handler(message: Message, db_session: AsyncSession, http_client: httpx.AsyncClient):
    url = message.text
    user_id = message.from_user.id

    async with ChatActionSender.choose_sticker(bot=message.bot, chat_id=message.chat.id):
        send_manager = MediaSender()
        resolved_url = await resolve_pinterest_url(url)
        pin_id = None
        match = re.search(r"/pin/(\d+)", resolved_url)
        if match:
            pin_id = match.group(1)

        cache_key = f"pin:{pin_id}" if pin_id else None
        if cache_key:
            cached = await cache_check(db_session, cache_key)
            if cached:
                await send_manager.send(message, cached, service="pinterest", db_session=db_session)
                return

    async with ChatActionSender.record_video_note(bot=message.bot, chat_id=message.chat.id):
        payload = {
            "url": resolved_url,
        }
        res = await task_manager.run_download(
            user_id=user_id,
            url=url,
            coro=http_client.post(
                "http://media-core:9546/download/pinterest", json=payload,
            ),
        )

        err_msg = res.text.lower() if res.text else ""
        is_error = res.status_code >= 400
        if res.status_code == 451 or (is_error and ("geo" in err_msg or "country" in err_msg or "region" in err_msg)):
            raise BotError(
                code=ErrorCode.REGION_RESTRICTED,
                url=url,
                service=Services.PINTEREST,
                message=f"Download Error:\n {res.text}",
                is_logged=False,
                critical=False,
            )

        if res.status_code == 400:
            raise BotError(
                code=ErrorCode.INVALID_URL,
                url=url,
                service=Services.PINTEREST,
                message=f"Download Error:\n {res.text}",
                is_logged=True,
                critical=False,
            )

        if res.status_code == 403:
            raise BotError(
                code=ErrorCode.NOT_ALLOWED,
                url=url,
                service=Services.PINTEREST,
                message=f"Download Error:\n {res.text}",
                is_logged=True,
                critical=False,
            )

        if res.status_code == 413:
            raise BotError(
                code=ErrorCode.LARGE_FILE,
                url=url,
                service=Services.PINTEREST,
                message=f"Download Error:\n {res.text}",
                is_logged=True,
                critical=False,
            )

        if res.status_code == 404:
            raise BotError(
                code=ErrorCode.NOT_FOUND,
                url=url,
                service=Services.PINTEREST,
                message=f"Download Error:\n {res.text}",
                is_logged=True,
                critical=False,
            )

        if res.status_code != 200:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                url=url,
                service=Services.PINTEREST,
                message=f"Download Error:\n {res.text}",
                is_logged=True,
                critical=True,
            )

        metadata = res.json()["data"]

        if metadata.get("type") == "multi":
            for i, sub_pin in enumerate(metadata.get('items', [])):
                sub_author = sub_pin.get('author_username')
                sub_caption = escape_html((sub_pin.get('caption') or "").strip())
                sub_author_link = f"<a href='https://www.pinterest.com/{sub_author}/'>{sub_author}</a>" if sub_author else ""
                parts = [p for p in [sub_author_link, sub_caption] if p]
                caption = " - ".join(parts)

                sub_media_content = []
                for media in sub_pin.get('items', []):
                    sub_media_content.append(
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

                sub_pin_id = sub_pin.get("id")
                sub_cache_key = f"pin:{sub_pin_id}" if sub_pin_id else None

                if sub_media_content:
                    await send_manager.send(
                        message,
                        sub_media_content,
                        service="pinterest",
                        cache_key=sub_cache_key,
                        db_session=db_session,
                        skip_reaction=(i > 0),
                        skip_notification=(i > 0),
                    )
        else:
            author = metadata.get('author_username')
            caption_text = escape_html((metadata.get('caption') or "").strip())
            author_link = f"<a href='https://www.pinterest.com/{author}/'>{author}</a>" if author else ""
            parts = [p for p in [author_link, caption_text] if p]
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

            final_pin_id = metadata.get("id") or pin_id
            final_cache_key = f"pin:{final_pin_id}" if final_pin_id else None

            if media_content:
                await send_manager.send(message, media_content, service="pinterest", cache_key=final_cache_key, db_session=db_session)


def get_cache_key(url: str) -> str:
    match = re.search(r"/pin/(\d+)", url)
    if match:
        return f"pin:{match.group(1)}"

    clean_url = url.split('?')[0].rstrip('/')
    hashed = hashlib.md5(clean_url.encode('utf-8')).hexdigest()
    return f"pin:{hashed}"


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
