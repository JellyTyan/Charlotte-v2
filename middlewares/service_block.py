import re
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from typing import Callable, Dict, Any, Awaitable
from storage.db.crud import get_chat_settings, get_global_settings, get_user_settings, remember_bot_status
from models.settings import ChatSettingsJson
from sqlalchemy.ext.asyncio import AsyncSession

from storage.cache.redis_client import cache_get
from utils.progress import current_context

SERVICE_PATTERNS = {
    "applemusic": r"https?://music\.apple\.com/",
    "douyin": r"https?://(?:(?:www\.|v\.)?douyin\.com|(?:www\.)?iesdouyin\.com)/",
    "deezer": r"https?:\/\/(?:www\.|link\.)?deezer\.com/",
    "instagram": r"https?://(?:www\.)?instagram\.com/",
    "pinterest": r"https?://(?:www\.)?pinterest\.com/",
    "pixiv": r"https?://(?:www\.)?pixiv\.net/",
    "reddit": r"https?://(?:www\.)?reddit\.com/",
    "soundcloud": r"https?://(?:www\.)?soundcloud\.com/",
    "spotify": r"https?://open\.spotify\.com/",
    "tiktok": r"https?://(?:www\.)?(?:vm\.)?tiktok\.com/",
    "twitter": r"https?://(?:www\.)?(?:twitter\.com|x\.com)/",
    "youtube": r"https?://(?:www\.)?(?:m\.)?(?:youtu\.be/|youtube\.com/(?:shorts/|watch\?v=))",
    "ytmusic": r"https?://music\.youtube\.com/",
}

def detect_service(text: str) -> str | None:
    for service, pattern in SERVICE_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return service
    return None

async def bot_can_post(event: Message, session: AsyncSession) -> bool:
    """False if the bot is muted in this group: downloading would only end in a pile of failed sends.
    Usually answered from the cache that my_chat_member events keep fresh (handlers/membership.py);
    on a miss asks Telegram and stores the answer in `chats` too. On any API error assume it can."""
    cached = await cache_get(f"bot_can_post:{event.chat.id}")
    if cached is not None:
        return cached["ok"]
    try:
        me = await event.bot.me()
        member = await event.bot.get_chat_member(event.chat.id, me.id)
    except Exception:
        return True
    ok = await remember_bot_status(session, event.chat.id, member, owner_id=event.from_user.id if event.from_user else 0)
    await session.commit()  # the muted path returns before any handler would commit
    return ok


class ServiceBlockMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, Message) or not event.text:
            return await handler(event, data)

        service = detect_service(event.text)
        settings = None
        session = data.get("db_session")
        if service and session:
            # Blocked globally by the admin: tell the user, otherwise the bot looks broken
            global_settings = await get_global_settings(session)
            if service in global_settings.get("blocked_services", []):
                i18n = data.get("i18n")
                if i18n:
                    await event.reply(i18n.get("service-disabled"))
                return

            if event.chat.id < 0:
                if not await bot_can_post(event, session):
                    return
                settings = await get_chat_settings(session, event.chat.id)
                if isinstance(settings, ChatSettingsJson) and service in settings.profile.blocked_services:
                    return
            elif event.from_user:
                settings = await get_user_settings(session, event.from_user.id)

            # "links in text" off: react only to messages that are just a link
            if settings and not settings.profile.detect_links_anywhere and len(event.text.split()) > 1:
                return
        
        if data.get("i18n"):
            current_context.set((event, data["i18n"]))
        return await handler(event, data)
