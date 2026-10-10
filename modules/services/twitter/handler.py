import logging


import httpx
from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Config
from models.errors import ErrorCode
from models.service_list import Services
from modules.services._shared import build_media_items, cache_check, ensure_nsfw_allowed, make_cache_key
from senders.media_sender import MediaSender
from storage.db.crud import check_if_user_premium, get_chat_settings
from tasks.task_manager import task_manager
from utils import escape_html, build_caption, format_author_link, extract_url

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

    url = extract_url(TWITTER_REGEX, message.text)
    if not url:
        return
    chat_id = message.chat.id
    user_id = message.from_user.id

    if task_manager.is_user_busy(user_id):
        from utils.ephemeral import notify_already_downloading_if_ephemeral
        await notify_already_downloading_if_ephemeral(message, user_id)

    from utils.effects import react_safe
    await react_safe(message, "👀")

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
            ensure_nsfw_allowed(is_nsfw, sponsor, allow_nsfw, url, Services.TWITTER, chat_code=ErrorCode.AGE_RESTRICTED)
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

        ensure_nsfw_allowed(is_nsfw, sponsor, allow_nsfw, url, Services.TWITTER)

        author_data = metadata.get('author') if isinstance(metadata.get('author'), dict) else {}
        author_username = author_data.get('username') or metadata.get('author_username')
        author_name = author_data.get('name')
        author_url = author_data.get('url') or (f"https://x.com/{author_username}" if author_username else "")
        author_display = author_name or author_username
        author_link = format_author_link(author_display, author_url, icon="👤")

        description = escape_html((metadata.get('caption') or metadata.get('title') or "").strip())
        caption = build_caption(header=author_link, description=description)

        media_content = build_media_items(metadata.get('items', []), caption, is_blurred, is_nsfw)

    if media_content:
        await send_manager.send(message, media_content, service="twitter", cache_key=cache_key, db_session=db_session)


def get_cache_key(url: str) -> str:
    return make_cache_key("tw", url, r"status/(\d+)")
