import logging
from typing import Any, Awaitable, Callable, Dict
import contextvars

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject, Message

from storage.cache.redis_client import cache_set, cache_get

logger = logging.getLogger(__name__)

# Context variable to hold the user_id that triggered the current update.
# This lets us propagate the user_id into helper functions without threading issues.
current_user_id: contextvars.ContextVar[int | None] = contextvars.ContextVar("current_user_id", default=None)


class UserContextMiddleware(BaseMiddleware):
    """
    Outer dispatcher middleware that extracts the user_id from the incoming
    Update and saves it to a ContextVar so downstream code can access it.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        from aiogram.types import Update
        user_id = None
        if isinstance(event, Update):
            if event.message and event.message.from_user:
                user_id = event.message.from_user.id
            elif event.callback_query and event.callback_query.from_user:
                user_id = event.callback_query.from_user.id
            elif event.inline_query and event.inline_query.from_user:
                user_id = event.inline_query.from_user.id

        token = None
        if user_id:
            token = current_user_id.set(user_id)

        try:
            return await handler(event, data)
        finally:
            if token is not None:
                current_user_id.reset(token)


async def register_message_owner(message: Message, owner_id: int) -> None:
    """
    Call this after sending/editing a message with an inline keyboard in a group chat.
    It saves the owner mapping to Redis so ButtonOwnerMiddleware can enforce it.
    """
    if message.chat.id >= 0:
        # Only meaningful in groups
        return
    redis_key = f"btn_owner:{message.chat.id}:{message.message_id}"
    await cache_set(redis_key, {"user_id": owner_id}, ttl=172800)  # 48 hours
    logger.debug(f"Registered button owner for {message.chat.id}:{message.message_id} -> {owner_id}")


class ButtonOwnerMiddleware(BaseMiddleware):
    """
    Dispatcher CallbackQuery middleware that asserts the current clicker is the
    owner stored in Redis. If not, shows an alert and drops the update.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        if not isinstance(event, CallbackQuery):
            return await handler(event, data)

        # Only enforce in group chats
        chat = getattr(getattr(event, 'message', None), 'chat', None)
        if not chat or chat.id >= 0:
            return await handler(event, data)

        message_id = getattr(event.message, 'message_id', None)
        if not message_id:
            return await handler(event, data)

        chat_id = chat.id
        clicker_id = event.from_user.id

        redis_key = f"btn_owner:{chat_id}:{message_id}"
        owner_data = await cache_get(redis_key)

        if owner_data and "user_id" in owner_data:
            owner_user_id = owner_data["user_id"]
            if owner_user_id != clicker_id:
                logger.warning(
                    f"User {clicker_id} tried to click button owned by {owner_user_id} "
                    f"in chat {chat_id} message {message_id}"
                )
                await event.answer("⚠️ You cannot interact with this menu.", show_alert=True)
                return  # Drop the update

        return await handler(event, data)
