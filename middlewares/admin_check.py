from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from core.config import Config, settings

class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: User = data.get("event_from_user")
        config: Config = data.get("config") or settings
        admin_id = getattr(config, "ADMIN_ID", None)

        if not user or not admin_id or user.id != admin_id:
            return None

        return await handler(event, data)
