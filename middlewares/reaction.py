from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, ReactionTypeEmoji, TelegramObject
from aiogram_dialog import DialogManager


class ReactionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            dialog_manager: DialogManager | None = data.get("dialog_manager")
            in_active_dialog = dialog_manager is not None and dialog_manager.has_context()

            if not in_active_dialog:
                try:
                    await event.react([ReactionTypeEmoji(emoji="👍")])
                except TelegramBadRequest:
                    pass

        return await handler(event, data)
