import logging
from typing import Optional, Any
from aiogram import Bot
from aiogram.types import Message, ReactionTypeEmoji

logger = logging.getLogger(__name__)


async def react_safe(message: Message, emoji: str) -> None:
    """Set a single emoji reaction on a message. Silently ignores any errors."""
    try:
        await message.react([ReactionTypeEmoji(emoji=emoji)])
    except Exception as e:
        logger.debug(f"Failed to set reaction {emoji!r}: {e}")

# Telegram Message Effect IDs (Bot API 7.4+)
# Supported in private chats.
EFFECT_FIREWORKS = "5044101728060834560"    # 🎆 Fireworks / Салют
EFFECT_CELEBRATION = "5046509860389126442"  # 🎉 Confetti / Праздничный салют
EFFECT_HEART = "5159385139981059251"        # ❤️ Heart
EFFECT_FLAME = "5104841245755180586"        # 🔥 Flame


async def answer_with_effect(
    message: Message,
    text: str,
    effect_id: str = EFFECT_FIREWORKS,
    fallback_effect_id: Optional[str] = EFFECT_CELEBRATION,
    **kwargs: Any,
) -> Message:
    """
    Send a response message with an animated message effect (e.g. fireworks).
    Gracefully falls back to fallback_effect_id or a plain message if the effect
    is rejected or unsupported (e.g. non-private chat, API limits, etc.).
    """
    effects_to_try = [effect_id]
    if fallback_effect_id and fallback_effect_id != effect_id:
        effects_to_try.append(fallback_effect_id)

    for eid in effects_to_try:
        try:
            return await message.answer(text, message_effect_id=eid, **kwargs)
        except Exception as e:
            logger.debug(f"Failed to send message with effect {eid}: {e}")

    return await message.answer(text, **kwargs)


async def send_message_with_effect(
    bot: Bot,
    chat_id: int,
    text: str,
    effect_id: str = EFFECT_FIREWORKS,
    fallback_effect_id: Optional[str] = EFFECT_CELEBRATION,
    **kwargs: Any,
) -> Message:
    """
    Send a message via bot with an animated message effect.
    Gracefully falls back to fallback_effect_id or a plain message if rejected.
    """
    effects_to_try = [effect_id]
    if fallback_effect_id and fallback_effect_id != effect_id:
        effects_to_try.append(fallback_effect_id)

    for eid in effects_to_try:
        try:
            return await bot.send_message(chat_id, text, message_effect_id=eid, **kwargs)
        except Exception as e:
            logger.debug(f"Failed to send message with effect {eid} to chat {chat_id}: {e}")

    return await bot.send_message(chat_id, text, **kwargs)
