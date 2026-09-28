import asyncio
import logging
from typing import Any
from aiogram.types import Message, EphemeralMessageParameters
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError

logger = logging.getLogger(__name__)


def get_ephemeral_parameters(chat_id: int, user_id: int | None) -> EphemeralMessageParameters | None:
    """
    Returns EphemeralMessageParameters for group chats (chat_id < 0) when user_id is provided,
    otherwise None for private chats.
    """
    if chat_id < 0 and user_id:
        return EphemeralMessageParameters(receiver_user_id=user_id)
    return None


async def is_user_ephemeral_enabled(user_id: int | None) -> bool:
    """
    Checks if the user has enabled experimental ephemeral messages in their private settings.
    Defaults to False.
    """
    if not user_id:
        return False
    try:
        from storage.cache.redis_client import cache_get
        cached = await cache_get(f"user_settings:{user_id}")
        if cached and isinstance(cached, dict):
            exp = cached.get("experimental", {})
            return bool(exp.get("ephemeral_messages", False))

        from storage.db import database_manager
        from storage.db.crud import get_user_settings
        async with database_manager.async_session() as session:
            settings = await get_user_settings(session, user_id)
            if settings and hasattr(settings, "experimental") and settings.experimental:
                return bool(settings.experimental.ephemeral_messages)
    except Exception as e:
        logger.debug(f"Could not check ephemeral setting for user {user_id}: {e}")
    return False


async def _auto_delete_message(msg: Message, delay: int) -> None:
    """
    Sleeps for delay seconds and then safely deletes the message.
    """
    try:
        await asyncio.sleep(delay)
        await delete_smart_message(msg)
    except Exception as e:
        logger.debug(f"Failed to auto-delete message after {delay}s: {e}")


async def send_smart_message(
    message: Message,
    text: str,
    for_user_id: int | None = None,
    timeout: int | None = 45,
    force_ephemeral: bool = False,
    **kwargs: Any
) -> Message:
    """
    Sends message as ephemeral in groups (chat_id < 0) if the target user has enabled
    experimental ephemeral messages in their settings (or force_ephemeral is True).
    
    If ephemeral is disabled, unsupported or fails:
    Sends a standard message, and if in a group chat (chat_id < 0) with a timeout specified,
    automatically schedules message deletion after `timeout` seconds.
    """
    target_user_id = for_user_id or (message.from_user.id if message.from_user else None)
    chat_id = message.chat.id
    is_group = chat_id < 0

    if is_group and target_user_id:
        ephemeral_enabled = force_ephemeral or await is_user_ephemeral_enabled(target_user_id)
        if ephemeral_enabled:
            ephemeral_params = get_ephemeral_parameters(chat_id, target_user_id)
            if ephemeral_params is not None:
                try:
                    return await message.answer(
                        text,
                        ephemeral_message_parameters=ephemeral_params,
                        **kwargs
                    )
                except (TelegramBadRequest, TelegramAPIError) as e:
                    logger.debug(f"Ephemeral send failed, falling back to standard send with timeout: {e}")

    # Fallback to standard send
    sent = await message.answer(text, **kwargs)

    # If sent in group without ephemeral, schedule auto-deletion with timeout
    if is_group and timeout and timeout > 0:
        asyncio.create_task(_auto_delete_message(sent, timeout))

    return sent


async def delete_smart_message(message: Message) -> None:
    """
    Deletes an ephemeral or regular message safely.
    """
    try:
        if getattr(message, "ephemeral_message_id", None) is not None:
            await message.delete_ephemeral()
        else:
            await message.delete()
    except (TelegramBadRequest, TelegramAPIError, Exception) as e:
        logger.debug(f"Could not delete message: {e}")


async def send_ephemeral_only(
    message: Message,
    text: str,
    for_user_id: int | None = None,
    **kwargs: Any
) -> Message | None:
    """
    Sends message strictly as ephemeral in groups (chat_id < 0) ONLY IF the target user
    has enabled experimental ephemeral messages in settings.
    Does NOT fall back to public/regular message.
    """
    target_user_id = for_user_id or (message.from_user.id if message.from_user else None)
    chat_id = message.chat.id
    if chat_id < 0 and target_user_id:
        if await is_user_ephemeral_enabled(target_user_id):
            ephemeral_params = get_ephemeral_parameters(chat_id, target_user_id)
            if ephemeral_params is not None:
                try:
                    return await message.answer(
                        text,
                        ephemeral_message_parameters=ephemeral_params,
                        **kwargs
                    )
                except (TelegramBadRequest, TelegramAPIError) as e:
                    logger.debug(f"Ephemeral-only send failed: {e}")
    return None


async def notify_already_downloading_if_ephemeral(
    message: Message,
    user_id: int,
    i18n: Any = None,
) -> Message | None:
    """
    If the user has ephemeral messages enabled, notify them that a download is already in progress.
    Strictly ephemeral only (no fallback to regular message).
    """
    text = (i18n.get("already-downloading") if i18n else None) or "⏳ Already downloading for you! Please wait 🐾"
    return await send_ephemeral_only(message, text, for_user_id=user_id)
