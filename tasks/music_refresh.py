"""Slow background re-download of cached music, so lossless-core fixes (wrong-track matching, better covers)
reach tracks downloaded before them. One track at a time, newest first; mediacache.refreshed_at marks it done.
The row keeps its key, title and artist: inline search and repeat requests simply get the new file.

Off unless MUSIC_REFRESH=true. Only `:default` keys: lossless downloads are switched off in lossless-core,
so `:lossless` rows would only fail.
"""
import asyncio
import logging
from pathlib import Path

import httpx
from aiogram import Bot
from sqlalchemy import func, select, update

from core.config import settings
from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.media_cache import MediaCacheDTO
from models.service_list import Services
from senders.media_sender import MediaSender
from storage.db import database_manager
from storage.db.models import MediaCache
from tasks.task_manager import task_manager
from utils import delete_files

logger = logging.getLogger(__name__)

PLATFORMS = ("applemusic", "spotify", "deezer", "soundcloud", "ytmusic")
PAUSE = 30  # s between tracks: ~6.7k tracks ≈ 3–4 days, and YouTube doesn't see a burst
REFRESH_USER = 0  # task_manager's per-user lock keeps refreshes strictly one at a time
# The track itself is gone or can't be had (deleted, private, region-locked, only a preview left): retrying is
# pointless, so it is skipped for good and the old cached file stays. Everything else (backend down, YouTube
# bot-check, rate limits) is external and retried on the next pass.
GONE = {ErrorCode.NOT_FOUND, ErrorCode.PRIVATE_CONTENT, ErrorCode.REGION_RESTRICTED, ErrorCode.PREVIEW_ONLY,
        ErrorCode.INVALID_URL, ErrorCode.NOT_SUPPORTED, ErrorCode.LARGE_FILE, ErrorCode.AGE_RESTRICTED}
MAX_FAILS_IN_ROW = 5  # lossless-core / YouTube is down, not the tracks: wait instead of rushing through the queue


async def _next(before: int | None) -> tuple[int, MediaCacheDTO] | None:
    """Newest not-yet-refreshed track below the cursor (media_id grows with inserts)."""
    async with database_manager.async_session() as s:
        q = select(MediaCache).where(
            MediaCache.media_type == "audio", MediaCache.platform.in_(PLATFORMS),
            MediaCache.cache_key.like("%:default"), MediaCache.refreshed_at.is_(None),
        )
        if before is not None:
            q = q.where(MediaCache.media_id < before)
        row = (await s.execute(q.order_by(MediaCache.media_id.desc()).limit(1))).scalar_one_or_none()
        return (row.media_id, MediaCacheDTO.model_validate(row, from_attributes=True)) if row else None


async def refresh_one(bot: Bot, http_client: httpx.AsyncClient, row: MediaCacheDTO) -> None:
    """Download the track again and swap the file_ids in its cache row. Raises on failure."""
    isrc = row.cache_key.rsplit(":", 1)[0]
    meta = row.data
    payload = {"isrc": isrc, "search_query": f"{meta.author} - {meta.title}", "lossless": False, "user_id": REFRESH_USER}
    track = await task_manager.run_media_download(
        user_id=REFRESH_USER, url=row.cache_key, service=Services.SPOTIFY, payload=payload,
        http_client=http_client, base_url=settings.LOSSLESS_CORE_URL,
    )
    item = MediaContent(
        type=MediaType.AUDIO, path=Path(track["audio_path"]), duration=meta.duration, title=meta.title,
        performer=meta.author, description=meta.description,
        cover=track.get("small_cover_path"), full_cover=track.get("large_cover_path"),
    )
    try:
        sender = MediaSender()
        if not await sender._dump_media_to_cache_channel(bot, [item]):
            raise RuntimeError("dump to the cache channel failed")
        async with database_manager.async_session() as s:
            await sender._save_to_cache([item], row.cache_key, row.platform, None, s)
    finally:
        await delete_files([p for p in (item.path, item.cover, item.full_cover) if p])


async def music_refresh_loop(bot: Bot) -> None:
    if not settings.MUSIC_REFRESH:
        return
    await asyncio.sleep(300)  # let the bot settle after a restart
    async with httpx.AsyncClient() as http_client:
        # An externally failed track stays unmarked (NULL) and the cursor moves past it, so one bad track can't
        # stall the queue; those are retried on the next pass, a day later. Stops once nothing is left.
        while await _next(None):
            cursor, fails, ok, gone, failed = None, 0, 0, 0, 0
            while nxt := await _next(cursor):
                cursor, row = nxt
                mark = None
                try:
                    await refresh_one(bot, http_client, row)
                    fails, ok, mark = 0, ok + 1, {"refreshed_at": func.now()}
                    logger.info(f"Music refresh: {row.cache_key} ({row.data.author} - {row.data.title}) updated")
                except BotError as e:
                    if e.code in GONE and "Task not found" not in (e.message or ""):  # not the core losing our task
                        gone += 1
                        # skipped for good; find them with: select cache_key, data->>'refresh_error' from mediacache where data ? 'refresh_error'
                        mark = {"refreshed_at": func.now(),
                                "data": MediaCache.data.op("||")(func.jsonb_build_object("refresh_error", str(e)))}
                        logger.info(f"Music refresh: {row.cache_key} is gone, keeping the old file: {e}")
                    else:
                        fails, failed = fails + 1, failed + 1
                        logger.warning(f"Music refresh: {row.cache_key} failed: {e}")
                except Exception as e:
                    fails, failed = fails + 1, failed + 1
                    logger.warning(f"Music refresh: {row.cache_key} failed: {e}")
                if mark:
                    async with database_manager.async_session() as s:
                        await s.execute(update(MediaCache).where(MediaCache.cache_key == row.cache_key).values(**mark))
                        await s.commit()
                if fails >= MAX_FAILS_IN_ROW:
                    logger.error("Music refresh: too many failures in a row, pausing for an hour")
                    await asyncio.sleep(3600)
                    fails = 0
                await asyncio.sleep(PAUSE)
            logger.info(f"Music refresh: pass done, {ok} updated, {gone} gone (skipped), {failed} failed (retried tomorrow)")
            await asyncio.sleep(86400)
    logger.info("Music refresh: all cached tracks refreshed")
