import re
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from typing import Callable, Dict, Any, Awaitable
from storage.db.crud import get_chat_settings, get_global_settings
from models.settings import ChatSettingsJson

SERVICE_PATTERNS = {
    "applemusic": r"https?://music\.apple\.com/",
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
                settings = await get_chat_settings(session, event.chat.id)
                if isinstance(settings, ChatSettingsJson) and service in settings.profile.blocked_services:
                    return
        
        return await handler(event, data)
