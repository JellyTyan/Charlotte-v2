import logging
from pathlib import Path

import httpx
from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, Message
from aiogram.utils.chat_action import ChatActionSender
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Config
from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.service_list import Services
from models.media_cache import MediaCacheDTO, CacheMetadata
from senders.media_sender import MediaSender
from storage.db.crud import get_chat_settings, get_user_settings, get_media_cache, upsert_media_cache
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.file_utils import delete_files
from utils.statistics_helper import log_download_event

deezer_router = Router(name="deezer")
logger = logging.getLogger(__name__)

async def cache_check(session: AsyncSession, cache_key: str) -> MediaContent | None:
    cached = await get_media_cache(session, cache_key)
    if cached:
        return MediaContent(
            type=MediaType.AUDIO,
            telegram_file_id=cached.telegram_file_id,
            telegram_document_file_id=cached.telegram_document_file_id,
            cover_file_id=cached.data.cover,
            full_cover_file_id=cached.data.full_cover,
            title=cached.data.title,
            performer=cached.data.author,
            duration=cached.data.duration
        )
    return None

DEEZER_REGEX = r"^https?:\/\/(?:www\.deezer\.com\/[a-z]{2}\/(track|album|playlist)\/\d+|link\.deezer\.com\/s\/[A-Za-z0-9]+)$"


async def fetch_core_download(
    http_client: httpx.AsyncClient, payload: dict, url: str
) -> dict:
    res = await http_client.post(
        "http://lossless-core:7856/download", json=payload, timeout=600
    )
    if res.status_code != 200:
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            url=url,
            message=f"Download Error:\n {res.text}",
            is_logged=True,
            critical=False,
        )
    return res.json()["data"]


async def process_track(
    track_meta: dict,
    message: Message,
    db_session: AsyncSession,
    http_client: httpx.AsyncClient,
    lossless_mode: bool,
    original_url: str,
    chat_id: int,
):
    isrc = track_meta["isrc"]
    cache_key_lossless = f"{isrc}:lossless"
    cache_key_default = f"{isrc}:default"
    send_manager = MediaSender()

    # Cache check: check corresponding requested quality first
    if lossless_mode:
        cached = await cache_check(db_session, cache_key_lossless)
        if cached:
            logger.info(f"Serving cached quality for {isrc}")
            await send_manager.send(
                message,
                content=[cached],
                skip_reaction=True,
                service="deezer",
                db_session=db_session,
            )
            return True
    else:
        cached = await cache_check(db_session, cache_key_default)
        if cached:
            logger.info(f"Serving cached quality for {isrc}")
            await send_manager.send(
                message,
                content=[cached],
                skip_reaction=True,
                service="deezer",
                db_session=db_session,
            )
            return True

    track_data = None
    current_lossless = lossless_mode
    search_query = f"{track_meta['artist']} - {track_meta['title']}"

    if current_lossless:
        try:
            payload = {"isrc": isrc, "search_query": search_query, "lossless": True}
            async with ChatActionSender.record_voice(bot=message.bot, chat_id=chat_id):
                track_data = await task_manager.run_download(
                    user_id=chat_id,
                    url=original_url,
                    coro=fetch_core_download(http_client, payload, original_url),
                )
        except BotError as e:
            if e.code == ErrorCode.DOWNLOAD_CANCELLED:
                raise e
            logger.info(
                f"Lossless unavailable for {isrc}, falling back to standard quality"
            )
            current_lossless = False

    if not current_lossless:
        cached_default = await cache_check(db_session, cache_key_default)
        if cached_default:
            await send_manager.send(
                message,
                content=[cached_default],
                skip_reaction=True,
                service="deezer",
                db_session=db_session,
            )
            return True

        payload = {"isrc": isrc, "search_query": search_query, "lossless": False}
        async with ChatActionSender.record_voice(bot=message.bot, chat_id=chat_id):
            track_data = await task_manager.run_download(
                user_id=chat_id,
                url=original_url,
                coro=fetch_core_download(http_client, payload, original_url),
            )

    media_content = MediaContent(
        type=MediaType.AUDIO,
        path=Path(track_data["audio_path"]),
        duration=int(track_meta["duration"]),
        title=track_meta["title"],
        performer=track_meta["artist"],
        cover=track_data["small_cover_path"],
        full_cover=track_data["large_cover_path"],
    )

    download_type = track_data.get("download_type", "standard")
    final_cache_key = (
        cache_key_lossless if download_type == "lossless" else cache_key_default
    )

    await send_manager.send(
        message,
        content=[media_content],
        skip_reaction=True,
        service="deezer",
        cache_key=final_cache_key,
        db_session=db_session,
    )
    return True


@deezer_router.message(F.text.regexp(DEEZER_REGEX))
async def deezer_handler(
    message: Message,
    config: Config,
    i18n: TranslatorRunner,
    db_session: AsyncSession,
    http_client: httpx.AsyncClient,
):
    if not message.text or not message.from_user:
        return

    url = message.text
    chat_id = message.chat.id
    user_id = message.from_user.id

    settings = (
        await get_chat_settings(db_session, chat_id)
        if chat_id < 0
        else await get_user_settings(db_session, chat_id)
    )
    lossless_mode = settings.services.deezer.lossless if settings else False

    async with ChatActionSender.choose_sticker(bot=message.bot, chat_id=chat_id):
        response = await http_client.post(
            "http://lossless-core:7856/metadata", json={"url": url}
        )
        if response.status_code != 200:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                url=url,
                message=f"Metadata Error:\n {response.text}",
                is_logged=True,
                critical=False,
            )
        metadata = response.json()["data"]

    if metadata["type"] == "song":
        await process_track(
            metadata, message, db_session, http_client, lossless_mode, url, chat_id
        )

    elif metadata["type"] in ["album", "playlist"]:
        if chat_id < 0 and not settings.profile.allow_playlists:
            raise BotError(
                code=ErrorCode.NOT_ALLOWED,
                message="Playlists are not allowed in this chat",
                service=Services.DEEZER,
            )

        text = f"{metadata['title']} by {metadata['author']}\n"
        if metadata.get("description"):
            text += f"<i>{metadata['description']}</i>\n"
        text += i18n.get("total-tracks", count=metadata["track_count"]) + "\n"
        if metadata.get("release_date"):
            text += i18n.get("release-date", date=metadata["release_date"]) + "\n"

        if metadata["cover"]:
            arq = await get_arq_pool("light")
            cover_job = await arq.enqueue_job(
                "universal_download",
                metadata["cover"],
                f"storage/temp/deezer_album_{metadata['id']}.png",
            )
            cover_path = await cover_job.result()
            await message.answer_photo(
                photo=FSInputFile(cover_path), caption=text, parse_mode=ParseMode.HTML
            )
            await delete_files([cover_path])

        await message.reply(i18n.get("downloading-tracks"))

        success_count, failed_count = 0, 0
        skipped_cancelled = False

        for track_meta in metadata["tracks"]:
            if task_manager.is_cancelled(user_id):
                await message.answer(i18n.get("playlist-stopped"))
                skipped_cancelled = True
                break

            if not track_meta.get("artist") or not track_meta.get("title"):
                failed_count += 1
                continue

            try:
                await process_track(
                    track_meta,
                    message,
                    db_session,
                    http_client,
                    lossless_mode,
                    track_meta.get("url", url),
                    chat_id,
                )
                success_count += 1
            except BotError as e:
                if e.code == ErrorCode.DOWNLOAD_CANCELLED:
                    await message.answer(i18n.get("playlist-stopped"))
                    skipped_cancelled = True
                    break
                logger.warning(f"Skipping track '{track_meta.get('title')}'")
                await log_download_event(
                    db_session, user_id, Services.DEEZER, "failed_download"
                )
                await message.answer(
                    i18n.get("skipped-track", title=track_meta.get("title"))
                )
                failed_count += 1

        if not skipped_cancelled:
            if failed_count == 0:
                await message.answer(i18n.get("all-tracks-success"))
            else:
                await message.answer(
                    i18n.get(
                        "download-stats", success=success_count, failed=failed_count
                    )
                )
    else:
        raise BotError(
            code=ErrorCode.NOT_FOUND,
            message="Unknown media type",
            service=Services.DEEZER,
        )
