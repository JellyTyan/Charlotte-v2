import logging
import re


import httpx
from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.ext.asyncio import AsyncSession

from models.service_list import Services
from modules.services._shared import build_media_items, cache_check
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils import escape_html, build_caption, format_author_link, extract_url

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
    if not message.text or not message.from_user:
        return

    url = extract_url(PINTEREST_REGEX, message.text)
    if not url:
        return
    user_id = message.from_user.id

    from utils.effects import react_safe
    await react_safe(message, "👀")

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
            "user_id": user_id,
            "url": resolved_url,
            "sponsor": False,
            "nsfw": False,
        }
        metadata = await task_manager.run_media_download(
            user_id=user_id,
            url=resolved_url,
            service=Services.PINTEREST,
            payload=payload,
            http_client=http_client,
        )

        is_multi = (
            metadata.get("type") == "multi"
            or bool(metadata.get("children"))
            or (isinstance(metadata.get("extra"), dict) and metadata.get("extra", {}).get("type") == "multi")
        )

        sub_pins = metadata.get("children")
        if not sub_pins and is_multi:
            raw_items = metadata.get("items", [])
            if raw_items and isinstance(raw_items[0], dict) and ("items" in raw_items[0] or "author" in raw_items[0]):
                sub_pins = raw_items

        if is_multi and sub_pins:
            for i, sub_pin in enumerate(sub_pins):
                sub_author_data = sub_pin.get('author') if isinstance(sub_pin.get('author'), dict) else {}
                sub_author = sub_author_data.get('username') or sub_author_data.get('name') or sub_pin.get('author_username')
                sub_author_url = sub_author_data.get('url') or (f"https://www.pinterest.com/{sub_author}/" if sub_author else "")
                sub_author_link = format_author_link(sub_author, sub_author_url, icon="📌")
                sub_caption = escape_html((sub_pin.get('caption') or sub_pin.get('title') or "").strip())
                caption = build_caption(header=sub_author_link, description=sub_caption)

                sub_is_nsfw = bool(sub_pin.get('is_nsfw') or sub_pin.get('is_sensitive'))
                sub_is_blurred = bool(sub_pin.get('is_blurred') or sub_is_nsfw)

                raw_media_items = sub_pin.get('items', [])
                if not raw_media_items and sub_pin.get('path'):
                    raw_media_items = [sub_pin]

                sub_media_content = build_media_items(raw_media_items, caption, sub_is_blurred, sub_is_nsfw)

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
            author_data = metadata.get('author') if isinstance(metadata.get('author'), dict) else {}
            author = author_data.get('username') or author_data.get('name') or metadata.get('author_username')
            author_url = author_data.get('url') or (f"https://www.pinterest.com/{author}/" if author else "")
            author_link = format_author_link(author, author_url, icon="📌")
            caption_text = escape_html((metadata.get('caption') or metadata.get('title') or "").strip())
            caption = build_caption(header=author_link, description=caption_text)

            is_nsfw = bool(metadata.get('is_nsfw') or metadata.get('is_sensitive'))
            is_blurred = bool(metadata.get('is_blurred') or is_nsfw)

            media_content = build_media_items(metadata.get('items', []), caption, is_blurred, is_nsfw)

            final_pin_id = metadata.get("id") or pin_id
            final_cache_key = f"pin:{final_pin_id}" if final_pin_id else None

            if media_content:
                await send_manager.send(message, media_content, service="pinterest", cache_key=final_cache_key, db_session=db_session)
