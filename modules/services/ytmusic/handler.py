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
from senders.media_sender import MediaSender
from storage.db.crud import get_chat_settings, get_user_settings
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.file_utils import delete_files
from utils.statistics_helper import log_download_event

from .utils import cache_check

ytmusic_router = Router(name="ytmusic")
logger = logging.getLogger(__name__)

YTMUSIC_REGEX = r"https:\/\/music\.youtube\.com\/(watch\?v=[\w-]+(&[\w=-]+)*|playlist\?list=[\w-]+(&[\w=-]+)*)"


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
    original_url: str,
    chat_id: int,
):
    isrc = track_meta["isrc"]
    cache_key = f"{isrc}:default"
    send_manager = MediaSender()

    cached = await cache_check(db_session, cache_key)
    if cached:
        logger.info(f"Serving cached quality for {isrc}")
        await send_manager.send(
            message,
            content=[cached],
            skip_reaction=True,
            service="ytmusic",
            db_session=db_session,
        )
        return True

    payload = {"isrc": isrc, "search_query": f"{track_meta['artist']} - {track_meta['title']}", "lossless": False}
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

    await send_manager.send(
        message,
        content=[media_content],
        skip_reaction=True,
        service="ytmusic",
        cache_key=cache_key,
        db_session=db_session,
    )
    return True


@ytmusic_router.message(F.text.regexp(YTMUSIC_REGEX))
async def ytmusic_handler(
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
            metadata, message, db_session, http_client, url, chat_id
        )

    elif metadata["type"] in ["album", "playlist"]:
        if chat_id < 0 and not settings.profile.allow_playlists:
            raise BotError(
                code=ErrorCode.NOT_ALLOWED,
                message="Playlists are not allowed in this chat",
                service=Services.YTMUSIC,
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
                f"storage/temp/ytmusic_album_{metadata['id']}.png",
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
                    db_session, user_id, Services.YTMUSIC, "failed_download"
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
            service=Services.YTMUSIC,
        )
