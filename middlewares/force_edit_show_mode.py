from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from aiogram_dialog import DialogManager, ShowMode


class ForceEditShowModeMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        dialog_manager: DialogManager | None = data.get("dialog_manager")
        if dialog_manager is not None:
            dialog_manager.show_mode = ShowMode.EDIT

        return await handler(event, data)
