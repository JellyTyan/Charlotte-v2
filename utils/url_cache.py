import time
import logging
from typing import Optional, Dict
from .hash_utils import url_hash
from storage.cache import redis_client as redis_module

logger = logging.getLogger(__name__)

# Fallback кеш в памяти: {hash: (url, timestamp)}
_url_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL = 3600  # 1 час

async def store_url(url: str) -> str:
    """Сохраняет URL в Redis кеше (с fallback в память) и возвращает его хеш"""
    hash_key = url_hash(url)
    client = redis_module.redis_client
    if client:
        try:
            await client.setex(f"url_cache:{hash_key}", CACHE_TTL, url)
            return hash_key
        except Exception as e:
            logger.warning(f"Failed to store url in redis: {e}")

    _url_cache[hash_key] = (url, time.time())
    return hash_key

async def get_url(hash_key: str) -> str | None:
    """Получает URL по хешу из Redis или fallback кеша"""
    client = redis_module.redis_client
    if client:
        try:
            val = await client.get(f"url_cache:{hash_key}")
            if val:
                return val
        except Exception as e:
            logger.warning(f"Failed to get url from redis: {e}")

    # Fallback to in-memory
    if hash_key in _url_cache:
        url, timestamp = _url_cache[hash_key]
        if time.time() - timestamp <= CACHE_TTL:
            return url
        del _url_cache[hash_key]

    return None

def cleanup_expired():
    """Очищает истекшие записи из локального fallback кеша"""
    current_time = time.time()
    expired_keys = [
        key for key, (_, timestamp) in _url_cache.items()
        if current_time - timestamp > CACHE_TTL
    ]
    for key in expired_keys:
        del _url_cache[key]