from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message
from typing import Callable, Dict, Any, Awaitable
from storage.db.crud import get_user


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

        if isinstance(event, Message) and event.from_user:
            from tasks.task_manager import task_manager
            task_manager.clear_cancel(event.from_user.id)

        # Check is banned
        session = data.get("db_session")
        if session and event.from_user:
            user = await get_user(session, event.from_user.id)
            if user and user.is_banned:
                return

        return await handler(event, data)
