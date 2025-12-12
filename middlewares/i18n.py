from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Chat, TelegramObject, User
from fluentogram import TranslatorHub
from storage.db.crud import get_user_settings, get_chat_settings

class TranslatorRunnerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        chat: Chat = data.get("event_chat")

        lang = "en"

        if chat and chat.type != "private":
            settings = await get_chat_settings(chat.id)
            if settings:
                lang = settings.lang

        elif user:
            settings = await get_user_settings(user.id)
            if settings:
                lang = settings.lang

        hub: TranslatorHub = data.get("_translator_hub")

        data["i18n"] = hub.get_translator_by_locale(lang)

        return await handler(event, data)
