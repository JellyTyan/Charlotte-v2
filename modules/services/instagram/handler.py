import logging


import httpx
from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.ext.asyncio import AsyncSession

from models.service_list import Services
from modules.services._shared import build_media_items, cache_check, make_cache_key
from senders.media_sender import MediaSender
from storage.db.crud import check_if_user_premium
from tasks.task_manager import task_manager
from utils import escape_html, build_caption, format_author_link, extract_url

insta_router = Router(name="instagram")

logger = logging.getLogger(__name__)

INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reels?|tv)/[\w-]+/?"

@insta_router.message(F.text.regexp(INSTAGRAM_REGEX))
async def instagram_handler(message: Message, db_session: AsyncSession, http_client: httpx.AsyncClient):
    if not message.text or not message.from_user:
        return

    url = extract_url(INSTAGRAM_REGEX, message.text)
    if not url:
        return
    user_id = message.from_user.id

    if task_manager.is_user_busy(user_id):
        from utils.ephemeral import notify_already_downloading_if_ephemeral
        await notify_already_downloading_if_ephemeral(message, user_id)

    from utils.effects import react_safe
    await react_safe(message, "👀")

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

        media_content = build_media_items(metadata.get('items', []), caption, is_blurred, is_nsfw)

    if media_content:
        await send_manager.send(message, media_content, service="instagram", cache_key=cache_key, db_session=db_session)


def get_cache_key(url: str, sponsor: bool) -> str:
    return make_cache_key("ig", url, r"/(?:p|reels?|tv)/([A-Za-z0-9_-]+)", ":sponsor" if sponsor else "")
