from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from typing import Callable, Dict, Any, Awaitable


class ServiceUseMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Check is user
        if isinstance(event, Message) and not event.from_user:
            return

        # Check is banned

        return await handler(event, data)
