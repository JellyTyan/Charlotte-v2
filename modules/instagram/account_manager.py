"""
Instagram Account Manager
Manages cookie-file accounts: ban detection, rate limiting, LRU account rotation.
"""

import logging
import os
import random
import time
from typing import Optional

from storage.cache.redis_client import redis_client

logger = logging.getLogger(__name__)

COOKIES_DIR = "storage/cookies/instagram"
MAX_REQUESTS_PER_MINUTE = 3  # per account
BAN_TTL = 3600               # 1 hour ban
LRU_JITTER_TOP_N = 2


def _all_cookie_files() -> list[str]:
    """Return all .txt cookie file paths."""
    if not os.path.exists(COOKIES_DIR):
        return []
    return [
        os.path.join(COOKIES_DIR, f)
        for f in os.listdir(COOKIES_DIR)
        if f.endswith(".txt")
    ]


def _ban_key(filepath: str) -> str:
    return f"ig:ban:{os.path.basename(filepath)}"


def _rate_key(filepath: str) -> str:
    minute = int(time.time() // 60)
    return f"ig:ratelimit:{os.path.basename(filepath)}:{minute}"


def _last_used_key(filepath: str) -> str:
    return f"ig:last_used:{os.path.basename(filepath)}"


async def get_available_account() -> Optional[str]:
    """
    Return a cookie file path that is not banned and has not exceeded
    the per-minute rate limit.

    Selection strategy: LRU (least-recently-used) with jitter.
    Among all eligible accounts, sort by the last-used timestamp (oldest first)
    and randomly pick from the top-N to avoid always hammering the same account.
    Returns None if no account is available.
    """
    files = _all_cookie_files()
    if not files:
        logger.warning("No Instagram cookie files found in %s", COOKIES_DIR)
        return None

    if not redis_client:
        # Redis unavailable — shuffle and return first to at least vary accounts
        shuffled = list(files)
        random.shuffle(shuffled)
        logger.debug("Redis unavailable, returning random account (no tracking)")
        return shuffled[0]

    # ── Filter: skip banned and rate-limited accounts ─────────────────────────
    eligible: list[str] = []
    for filepath in files:
        name = os.path.basename(filepath)

        if await redis_client.exists(_ban_key(filepath)):
            logger.debug("[%s] Skipping — marked as banned in Redis", name)
            continue

        rate_key = _rate_key(filepath)
        current = await redis_client.get(rate_key)
        if current and int(current) >= MAX_REQUESTS_PER_MINUTE:
            logger.debug(
                "[%s] Skipping — rate limit reached (%s/%s req/min)",
                name, current, MAX_REQUESTS_PER_MINUTE,
            )
            continue

        eligible.append(filepath)

    if not eligible:
        logger.error(
            "All %d Instagram account(s) are banned or rate-limited. "
            "Total files found: %d",
            len(files), len(files),
        )
        return None

    # ── Sort eligible accounts by last-used timestamp (LRU first) ────────────
    async def _last_used(filepath: str) -> float:
        val = await redis_client.get(_last_used_key(filepath))
        return float(val) if val else 0.0

    scored = [(await _last_used(fp), fp) for fp in eligible]
    scored.sort(key=lambda x: x[0])  # oldest timestamp = least recently used

    # Pick randomly from the top-N least-recently-used to add jitter
    top_n = min(LRU_JITTER_TOP_N, len(scored))
    chosen_ts, chosen = random.choice(scored[:top_n])

    idle_seconds = time.time() - chosen_ts if chosen_ts > 0 else -1
    logger.debug(
        "Account rotation: chose [%s] (idle %.0fs) from %d eligible account(s). "
        "LRU pool size: top-%d of %d.",
        os.path.basename(chosen),
        idle_seconds,
        len(eligible),
        top_n,
        len(scored),
    )

    return chosen


async def record_request(filepath: str) -> None:
    """
    Increment the per-minute request counter and update last-used timestamp
    so LRU ordering stays accurate.
    """
    if not redis_client or not filepath:
        return

    now = time.time()

    rate_key = _rate_key(filepath)
    await redis_client.incr(rate_key)
    await redis_client.expire(rate_key, 90)  # keep alive a bit beyond 1 minute

    await redis_client.set(_last_used_key(filepath), str(now))

    logger.debug(
        "[%s] Request recorded. last_used updated to %.0f",
        os.path.basename(filepath), now,
    )


async def mark_account_banned(filepath: str, ttl: int = BAN_TTL) -> None:
    """Mark an account as banned for `ttl` seconds."""
    if not redis_client or not filepath:
        return
    name = os.path.basename(filepath)
    await redis_client.setex(_ban_key(filepath), ttl, "1")
    logger.error(
        "Instagram account [%s] marked as BANNED for %ds (%dm). "
        "Will be retried after ban expires.",
        name, ttl, ttl // 60,
    )


async def is_banned(filepath: str) -> bool:
    if not redis_client:
        return False
    return bool(await redis_client.exists(_ban_key(filepath)))


async def get_accounts_status() -> list[dict]:
    """
    Return a status summary of all accounts for debugging/admin use.
    Each entry: {name, banned, ban_ttl_remaining, requests_this_minute, last_used}
    """
    files = _all_cookie_files()
    if not redis_client:
        return [{"name": os.path.basename(f), "redis": "unavailable"} for f in files]

    result = []
    for filepath in files:
        name = os.path.basename(filepath)

        ban_ttl = await redis_client.ttl(_ban_key(filepath))
        banned = ban_ttl > 0

        rate_key = _rate_key(filepath)
        req_count = await redis_client.get(rate_key)

        last_used_raw = await redis_client.get(_last_used_key(filepath))
        last_used_ts = float(last_used_raw) if last_used_raw else None
        idle_s = int(time.time() - last_used_ts) if last_used_ts else None

        result.append({
            "name": name,
            "banned": banned,
            "ban_ttl_remaining_s": ban_ttl if banned else 0,
            "requests_this_minute": int(req_count) if req_count else 0,
            "last_used_ts": last_used_ts,
            "idle_seconds": idle_s,
        })

    result.sort(key=lambda x: x.get("idle_seconds") or 999999, reverse=True)
    return result
