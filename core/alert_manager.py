"""Admin Alert Manager with Redis deduplication and cooldown."""

import hashlib
import html
import logging
from typing import Any

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError

from core.config import settings
from storage.cache import redis_client as r_module

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_SECONDS = 300  # 5 minutes


def _format_alert_text(
    title: str,
    message: str,
    context: dict[str, Any] | None = None,
    traceback_str: str | None = None,
) -> str:
    """Formats a structured HTML alert for Telegram within the 4096 character limit."""
    lines = [
        f"🚨 <b>{html.escape(title)}</b>\n",
        f"<b>Error:</b> <code>{html.escape(str(message)[:500])}</code>",
    ]

    if context:
        ctx_parts = []
        for k, v in context.items():
            if v:
                ctx_parts.append(f"<b>{html.escape(str(k))}:</b> <code>{html.escape(str(v)[:200])}</code>")
        if ctx_parts:
            lines.append("\n" + "\n".join(ctx_parts))

    if traceback_str:
        # Keep the most relevant end of the traceback (up to 1500 chars)
        tb_clean = traceback_str.strip()
        if len(tb_clean) > 1500:
            tb_clean = "..." + tb_clean[-1497:]
        lines.append(f"\n<pre language=\"python\">{html.escape(tb_clean)}</pre>")

    return "\n".join(lines)


async def send_admin_alert(
    bot: Bot,
    title: str,
    message: str,
    context: dict[str, Any] | None = None,
    traceback_str: str | None = None,
    alert_key: str | None = None,
    cooldown_seconds: int = DEFAULT_COOLDOWN_SECONDS,
) -> bool:
    """
    Sends an error alert to the bot admin in Telegram.
    Uses Redis to deduplicate alerts within the cooldown period (default: 5 min).
    Returns True if sent, False if throttled or disabled.
    """
    if not settings.ADMIN_ID:
        return False

    # Generate a unique key for deduplication if not explicitly provided
    if not alert_key:
        key_content = f"{title}:{message}"
        alert_key = hashlib.md5(key_content.encode()).hexdigest()[:16]

    client = r_module.redis_client
    if client:
        try:
            redis_key = f"alert_cooldown:{alert_key}"
            # Atomically set key with TTL only if it does not exist (NX=True)
            was_set = await client.set(redis_key, "1", ex=cooldown_seconds, nx=True)
            if not was_set:
                # Alert throttled; increment suppression counter
                await client.incr(f"alert_suppressed:{alert_key}")
                return False
        except Exception as err:  # noqa: BLE001
            logger.debug(f"Redis alert cooldown check failed: {err}")

    text = _format_alert_text(
        title=title,
        message=message,
        context=context,
        traceback_str=traceback_str,
    )

    try:
        await bot.send_message(settings.ADMIN_ID, text, parse_mode=ParseMode.HTML)
        return True
    except TelegramAPIError as e:
        logger.error(f"Failed to send admin alert: {e}")
        return False
