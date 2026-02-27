import re
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from typing import Callable, Dict, Any, Awaitable
from storage.db.crud import get_chat_settings
from models.settings import ChatSettingsJson

SERVICE_PATTERNS = {
    "youtube": r"https?://(?:www\.)?(?:m\.)?(?:youtu\.be/|youtube\.com/(?:shorts/|watch\?v=))",
    "tiktok": r"https?://(?:www\.)?(?:vm\.)?tiktok\.com/",
    "instagram": r"https?://(?:www\.)?instagram\.com/",
    "twitter": r"https?://(?:www\.)?(?:twitter\.com|x\.com)/",
    "reddit": r"https?://(?:www\.)?reddit\.com/",
    "soundcloud": r"https?://(?:www\.)?soundcloud\.com/",
    "spotify": r"https?://open\.spotify\.com/",
    "applemusic": r"https?://music\.apple\.com/",
    "deezer": r"https?://(?:www\.)?deezer\.com/",
    "pinterest": r"https?://(?:www\.)?pinterest\.com/",
    "pixiv": r"https?://(?:www\.)?pixiv\.net/",
    "ytmusic": r"https?://music\.youtube\.com/"
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
        
        if event.chat.id < 0:
            service = detect_service(event.text)
            if service:
                settings = await get_chat_settings(event.chat.id)
                if isinstance(settings, ChatSettingsJson) and service in settings.profile.blocked_services:
                    return
        
        return await handler(event, data)
