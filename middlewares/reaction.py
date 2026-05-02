from aiogram import BaseMiddleware
from aiogram.types import Message, ReactionTypeEmoji, TelegramObject
from typing import Callable, Dict, Any, Awaitable

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
                # Add 👍 reaction to indicate the link is accepted
                await event.react([ReactionTypeEmoji(emoji="👍")])
            except Exception:
                # Silently ignore if reactions are not supported or bot lacks permissions
                pass
        
        return await handler(event, data)
