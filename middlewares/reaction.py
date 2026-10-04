from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReactionTypeEmoji, TelegramObject


class ReactionMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        if isinstance(event, Message):
            state: FSMContext | None = data.get("state")
            current_state = await state.get_state() if state else None

            if not current_state:
                try:
                    await event.react([ReactionTypeEmoji(emoji="👍")])
                except TelegramBadRequest:
                    pass

        return await handler(event, data)
