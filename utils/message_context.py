import json
import logging
from typing import Optional, Dict, Any
from storage.cache import redis_client as redis_module
from utils.hash_utils import url_hash

logger = logging.getLogger(__name__)

CONTEXT_TTL = 86400 * 3  # 3 days
PURGE_TTL = 86400 * 7    # 7 days


async def save_message_context(chat_id: int, message_id: int, data: Dict[str, Any]) -> None:
    """Saves metadata context for a message sent by the bot (URL, cache key, service, etc.)"""
    client = redis_module.redis_client
    if not client:
        return
    try:
        key = f"msg_ctx:{chat_id}:{message_id}"
        await client.setex(key, CONTEXT_TTL, json.dumps(data, default=str))
    except Exception as e:
        logger.debug(f"Failed to save message context for {chat_id}:{message_id}: {e}")


async def get_message_context(chat_id: int, message_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves metadata context for a message sent by the bot"""
    client = redis_module.redis_client
    if not client:
        return None
    try:
        key = f"msg_ctx:{chat_id}:{message_id}"
        raw = await client.get(key)
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.debug(f"Failed to get message context for {chat_id}:{message_id}: {e}")
    return None


async def store_purge_key(cache_key: str) -> str:
    """Returns a callback-safe token for cache purging (handles Telegram 64-byte limit)"""
    client = redis_module.redis_client
    # If short enough, we can use the key directly with prefix
    # "purge_cache:" is 12 bytes. If key <= 48 bytes, total <= 60 bytes.
    encoded_len = len(cache_key.encode("utf-8"))
    if encoded_len <= 48:
        return f"d:{cache_key}"

    # If too long, store in Redis with short 8-char hash
    token_hash = url_hash(cache_key)
    if client:
        try:
            await client.setex(f"purge_tok:{token_hash}", PURGE_TTL, cache_key)
        except Exception as e:
            logger.warning(f"Failed to store purge token: {e}")
    return f"h:{token_hash}"


async def resolve_purge_key(token: str) -> Optional[str]:
    """Resolves the original cache_key from token created by store_purge_key"""
    if token.startswith("d:"):
        return token[2:]
    if token.startswith("h:"):
        token_hash = token[2:]
        client = redis_module.redis_client
        if client:
            try:
                val = await client.get(f"purge_tok:{token_hash}")
                if val:
                    return val
            except Exception as e:
                logger.warning(f"Failed to resolve purge token {token_hash}: {e}")
    return None
