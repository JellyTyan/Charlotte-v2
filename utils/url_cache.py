import time
from typing import Optional, Dict
from .hash_utils import url_hash

# Простой кеш в памяти: {hash: (url, timestamp)}
_url_cache: Dict[str, tuple[str, float]] = {}
CACHE_TTL = 3600  # 1 час

def store_url(url: str) -> str:
    """Сохраняет URL в кеше и возвращает его хеш"""
    hash_key = url_hash(url)
    _url_cache[hash_key] = (url, time.time())
    return hash_key

def get_url(hash_key: str) -> Optional[str]:
    """Получает URL по хешу, если он не истек"""
    if hash_key not in _url_cache:
        return None
    
    url, timestamp = _url_cache[hash_key]
    
    # Проверяем, не истек ли кеш
    if time.time() - timestamp > CACHE_TTL:
        del _url_cache[hash_key]
        return None
    
    return url

def cleanup_expired():
    """Очищает истекшие записи из кеша"""
    current_time = time.time()
    expired_keys = [
        key for key, (_, timestamp) in _url_cache.items()
        if current_time - timestamp > CACHE_TTL
    ]
    for key in expired_keys:
        del _url_cache[key]