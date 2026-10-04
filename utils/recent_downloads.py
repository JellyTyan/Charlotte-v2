"""Recent downloads management via Redis (12-hour TTL)."""

import contextlib
import json
import logging

from aiogram.types import Message

from storage.cache import redis_client as r_module

logger = logging.getLogger(__name__)

RECENT_TTL = 12 * 3600  # 12 hours
MAX_STORED_RECENT = 15
ALLOWED_MEDIA_TYPES = ("video", "photo", "gif")


def extract_file_unique_id(message: Message) -> str | None:
    """file_unique_id того же медиа, что выбирает extract_media_from_message (порядок проверок совпадает).

    В отличие от file_id он одинаков для одного файла в любых сообщениях — годится для поиска дублей.
    """
    media = (
        message.video or message.animation or (message.photo[-1] if message.photo else None)
        or message.audio or message.voice or message.video_note or message.document
    )
    return media.file_unique_id if media else None


def extract_media_from_message(message: Message) -> tuple[str | None, str | None, str | None]:
    """
    Extract (telegram_file_id, media_type, title) from a Telegram message.
    media_type is one of: 'video', 'photo', 'audio', 'gif'
    """
    if message.video:
        return message.video.file_id, "video", message.video.file_name
    if message.animation:
        return message.animation.file_id, "gif", message.animation.file_name
    if message.photo:
        return message.photo[-1].file_id, "photo", None
    if message.audio:
        title = message.audio.title or "Audio"
        if message.audio.performer:
            title = f"{message.audio.performer} - {title}"
        return message.audio.file_id, "audio", title
    if message.voice:
        return message.voice.file_id, "audio", "Voice Message"
    if message.video_note:
        return message.video_note.file_id, "video", "Video Note"
    if message.document:
        mime = message.document.mime_type or ""
        if mime.startswith("video/"):
            return message.document.file_id, "video", message.document.file_name
        elif mime.startswith("image/"):
            return message.document.file_id, "photo", message.document.file_name
        elif mime.startswith("audio/"):
            return message.document.file_id, "audio", message.document.file_name
        return message.document.file_id, "video", message.document.file_name

    return None, None, None


async def push_recent_download(
    user_id: int,
    file_id: str,
    media_type: str,
    title: str | None = None,
    ttl: int = RECENT_TTL,
    max_items: int = MAX_STORED_RECENT,
) -> None:
    """
    Saves visual media into the user's recent downloads list in Redis (12h TTL).
    Audio media is deliberately ignored to keep inline visual feed clean.
    """
    client = r_module.redis_client
    if not client or media_type not in ALLOWED_MEDIA_TYPES:
        return

    try:
        key = f"recent:{user_id}"
        raw_items = await client.lrange(key, 0, max_items)
        items = []
        for r in raw_items:
            with contextlib.suppress(json.JSONDecodeError, TypeError, KeyError):
                parsed = json.loads(r)
                if parsed.get("file_id") != file_id:
                    items.append(parsed)

        new_item = {
            "file_id": file_id,
            "media_type": media_type,
            "title": title or "",
        }
        items.insert(0, new_item)
        items = items[:max_items]

        pipe = client.pipeline()
        pipe.delete(key)
        pipe.rpush(key, *[json.dumps(it) for it in items])
        pipe.expire(key, ttl)
        await pipe.execute()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Failed to push recent download for user {user_id}: {e}")


async def get_recent_downloads(user_id: int, limit: int = 5) -> list[dict]:
    """
    Retrieves recent visual downloads for user_id (up to limit).
    """
    client = r_module.redis_client
    if not client:
        return []

    try:
        key = f"recent:{user_id}"
        raw_items = await client.lrange(key, 0, limit - 1)
        results = []
        for r in raw_items:
            with contextlib.suppress(json.JSONDecodeError, TypeError, KeyError):
                results.append(json.loads(r))
        return results
    except Exception as e:  # noqa: BLE001
        logger.debug(f"Failed to get recent downloads for user {user_id}: {e}")
        return []
