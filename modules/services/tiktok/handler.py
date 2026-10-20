import logging

import httpx
from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.ext.asyncio import AsyncSession

from models.service_list import Services
from modules.services._shared import build_post_media, cache_check, make_cache_key
from senders.media_sender import MediaSender
from storage.db.crud import check_if_user_premium
from tasks.task_manager import resolve_url, task_manager
from utils import format_author_link, extract_url

tiktok_router = Router(name="tiktok")

logger = logging.getLogger(__name__)

TIKTOK_REGEX = r"https?://(?:(?:www\.|m\.)?tiktok\.com/\S+|(?:vm|vt)\.tiktok\.com/\S+|(?:www\.)?tt\.site/\S+)"


@tiktok_router.message(F.text.regexp(TIKTOK_REGEX))
async def tiktok_handler(message: Message, db_session: AsyncSession, http_client: httpx.AsyncClient):
    raw_text = message.text or message.caption
    if not raw_text or not message.from_user:
        return

    url = extract_url(TIKTOK_REGEX, raw_text)
    if not url:
        return
    url = url.split("#")[0]
    user_id = message.from_user.id

    if task_manager.is_user_busy(user_id):
        from utils.ephemeral import notify_already_downloading_if_ephemeral
        await notify_already_downloading_if_ephemeral(message, user_id)

    from utils.effects import react_safe
    await react_safe(message, "👀")

    sponsor = await check_if_user_premium(db_session, user_id)

    async with ChatActionSender.choose_sticker(bot=message.bot, chat_id=message.chat.id):
        send_manager = MediaSender()
        resolved_url = url if "/video/" in url or "/photo/" in url else (await resolve_url(http_client, url)).split("#")[0]
        cache_key = get_cache_key(resolved_url, sponsor)

        cached = await cache_check(db_session, cache_key)
        if not cached and resolved_url != url:
            fallback_cache_key = get_cache_key(url, sponsor)
            cached = await cache_check(db_session, fallback_cache_key)

        if cached:
            await send_manager.send(message, cached, service="tiktok", db_session=db_session)
            return

    async with ChatActionSender.record_video_note(bot=message.bot, chat_id=message.chat.id):
        payload = {
            "user_id": user_id,
            "url": resolved_url,
            "sponsor": sponsor,
            "nsfw": False,
        }
        metadata = await task_manager.run_media_download(
            user_id=user_id,
            url=resolved_url,
            service=Services.TIKTOK,
            payload=payload,
            http_client=http_client,
        )

        author_data = metadata.get('author') if isinstance(metadata.get('author'), dict) else {}
        author_username = author_data.get('username') or metadata.get('author_username')
        author_name = author_data.get('name')
        author_url = author_data.get('url') or (f"https://www.tiktok.com/@{author_username}/" if author_username else "")
        author_display = author_username or author_name
        author_link = format_author_link(author_display, author_url, icon="👤")
        media_content = build_post_media(metadata, author_link)

    if media_content:
        await send_manager.send(message, media_content, service="tiktok", cache_key=cache_key, db_session=db_session)


def get_cache_key(url: str, sponsor: bool) -> str:
    return make_cache_key("tt", url, r"/(?:video|photo)/(\d+)", ":sponsor" if sponsor else "")

