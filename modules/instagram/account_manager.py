"""
Instagram Account Manager
Manages cookie-file accounts: ban detection, rate limiting, account rotation.
"""

import logging
import os
import time
from typing import Optional

from storage.cache.redis_client import redis_client

logger = logging.getLogger(__name__)

COOKIES_DIR = "storage/cookies/instagram"
MAX_REQUESTS_PER_MINUTE = 3  # per account
BAN_TTL = 3600  # 1 hour


def _all_cookie_files() -> list[str]:
    """Return all .txt cookie file paths."""
    if not os.path.exists(COOKIES_DIR):
        return []
    return [
        os.path.join(COOKIES_DIR, f)
        for f in sorted(os.listdir(COOKIES_DIR))
        if f.endswith(".txt")
    ]


def _ban_key(filepath: str) -> str:
    return f"ig:ban:{os.path.basename(filepath)}"


def _rate_key(filepath: str) -> str:
    minute = int(time.time() // 60)
    return f"ig:ratelimit:{os.path.basename(filepath)}:{minute}"


async def get_available_account() -> Optional[str]:
    """
    Return a cookie file path that is not banned and has not exceeded
    the per-minute rate limit. Tries accounts in order.
    Returns None if no account is available.
    """
    files = _all_cookie_files()
    if not files:
        logger.warning("No Instagram cookie files found in %s", COOKIES_DIR)
        return None

    if not redis_client:
        # Redis unavailable — just pick the first file, no tracking
        return files[0]

    for filepath in files:
        # Skip banned accounts
        banned = await redis_client.exists(_ban_key(filepath))
        if banned:
            logger.debug("Account %s is banned, skipping", os.path.basename(filepath))
            continue

        # Check rate limit
        rate_key = _rate_key(filepath)
        current = await redis_client.get(rate_key)
        if current and int(current) >= MAX_REQUESTS_PER_MINUTE:
            logger.debug(
                "Account %s hit rate limit (%s/%s req/min), skipping",
                os.path.basename(filepath), current, MAX_REQUESTS_PER_MINUTE
            )
            continue

        return filepath

    logger.error("All Instagram accounts are either banned or rate-limited")
    return None


async def record_request(filepath: str) -> None:
    """Increment the per-minute request counter for this account."""
    if not redis_client or not filepath:
        return
    rate_key = _rate_key(filepath)
    await redis_client.incr(rate_key)
    await redis_client.expire(rate_key, 90)  # keep key alive a bit beyond 1 minute


async def mark_account_banned(filepath: str, ttl: int = BAN_TTL) -> None:
    """Mark an account as banned for `ttl` seconds."""
    if not redis_client or not filepath:
        return
    name = os.path.basename(filepath)
    await redis_client.setex(_ban_key(filepath), ttl, "1")
    logger.warning("Instagram account marked as banned for %ds: %s", ttl, name)


async def is_banned(filepath: str) -> bool:
    if not redis_client:
        return False
    return bool(await redis_client.exists(_ban_key(filepath)))
