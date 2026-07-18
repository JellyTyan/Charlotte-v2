from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, ReactionTypeEmoji, TelegramObject


class ReactionMiddleware(BaseMiddleware):
    """
    Middleware to automatically add a reaction to a message when it's accepted for processing.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if isinstance(event, Message):
            try:
                await event.react([ReactionTypeEmoji(emoji="👍")])
            except TelegramBadRequest:
                # Silently ignore if reactions are not supported or bot lacks permissions
                pass
        
        return await handler(event, data)
