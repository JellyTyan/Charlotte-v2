import logging

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, Message
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Config
from models.errors import BotError, ErrorCode
from models.service_list import Services
from senders.media_sender import MediaSender
from storage.db.crud import get_chat_settings, get_user_settings
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.file_utils import delete_files
from utils.statistics_helper import log_download_event

from .service import SoundCloudService
from .utils import cache_check

soundcloud_router = Router(name='soundcloud')

logger = logging.getLogger(__name__)


SOUNDCLOUD_REGEX = r"^https:\/\/(?:on\.soundcloud\.com\/[a-zA-Z0-9]+|soundcloud\.com\/[^\/]+\/(sets\/[^\/]+|[^\/\?\s]+))(?:\?.*)?$"


@soundcloud_router.message(F.text.regexp(SOUNDCLOUD_REGEX))
async def soundcloud_handler(message: Message, config: Config, i18n: TranslatorRunner, db_session: AsyncSession):
    if not message.text or not message.from_user:
        return

    url = message.text
    chat_id = message.chat.id
    user_id = message.from_user.id

    # --- Settings (нужны только для проверки allow_playlists) ---
    if chat_id < 0:
        settings = await get_chat_settings(db_session, chat_id)
    else:
        settings = await get_user_settings(db_session, chat_id)

    # --- Initialize service ---
    arq = await get_arq_pool('light')
    service = SoundCloudService(arq=arq)

    # --- Fetch metadata ---
    media_metadata = await service.get_info(url, config=config)
    if not media_metadata:
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message="Failed to get metadata",
            url=url,
            service=Services.SOUNDCLOUD,
            is_logged=True
        )

    # =========================================================================
    # SINGLE TRACK
    # =========================================================================
    if media_metadata.media_type == "track":
        if not media_metadata.performer or not media_metadata.title:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Failed to get track metadata",
                url=url,
                service=Services.SOUNDCLOUD,
                is_logged=True
            )

        # Cache-first (один ключ без суффикса, т.к. лосслесс недоступен)
        cache_key = media_metadata.cache_key

        if cache_key:
            cached = await cache_check(db_session, cache_key)
            if cached:
                send_manager = MediaSender()
                await send_manager.send(message, [cached], service="soundcloud", db_session=db_session)
                return

        if message.bot:
            await message.bot.send_chat_action(chat_id, "record_audio")

        try:
            media_content = await task_manager.run_download(
                user_id=user_id,
                url=url,
                coro=service.download(media_metadata)
            )

            if media_content:
                send_manager = MediaSender()
                await send_manager.send(message, media_content, service="soundcloud",
                                        cache_key=cache_key, db_session=db_session)

        except BotError as e:
            await log_download_event(db_session, user_id, Services.SOUNDCLOUD, 'failed_download')
            raise e

    # =========================================================================
    # PLAYLIST (SoundCloud называет и альбомы, и сеты — playlist)
    # =========================================================================
    elif media_metadata.media_type == "playlist":
        if chat_id < 0 and not settings.profile.allow_playlists:
            raise BotError(
                code=ErrorCode.NOT_ALLOWED,
                message="Playlists are not allowed in this chat",
                service=Services.SOUNDCLOUD,
            )

        # Build info message
        text = f"<a href=\"{media_metadata.performer_url}\">{media_metadata.performer}</a> — {media_metadata.title}\n"
        if media_metadata.description:
            text += f"<i>{media_metadata.description}</i>\n"
        text += i18n.get('total-tracks', count=len(media_metadata.items)) + "\n"

        # Скачиваем обложку через arq (она хранится как URL, не как путь)
        if media_metadata.cover:
            job = await arq.enqueue_job(
                "universal_download",
                url=media_metadata.cover,
                destination=f"storage/temp/sc_{user_id}_{media_metadata.title[:20]}.jpg",
                _queue_name='light'
            )
            try:
                album_cover_path = await job.result()
            except Exception as e:
                logger.warning(f"Failed to download SoundCloud playlist cover: {e}")
                album_cover_path = None

            if album_cover_path:
                await message.answer_photo(
                    photo=FSInputFile(album_cover_path),
                    caption=text,
                    parse_mode=ParseMode.HTML
                )
                await delete_files([album_cover_path])
            else:
                await message.answer(text, parse_mode=ParseMode.HTML)
        else:
            await message.answer(text, parse_mode=ParseMode.HTML)

        await message.reply(i18n.get('downloading-tracks'))

        send_manager = MediaSender()

        for track_meta in media_metadata.items:
            # --- Cancellation check at top of every iteration ---
            if task_manager.is_cancelled(user_id):
                await message.answer(i18n.get('playlist-stopped'))
                break

            try:
                if not track_meta.title:
                    logger.warning("Skipping track with missing metadata")
                    continue

                track_cache_key = track_meta.cache_key

                # Cache-first
                if track_cache_key:
                    cached = await cache_check(db_session, track_cache_key)
                    if cached:
                        await send_manager.send(message, [cached], skip_reaction=True,
                                                service="soundcloud", db_session=db_session)
                        continue

                # Download the specific track URL (NOT the playlist URL)
                media_content = await task_manager.run_download(
                    user_id=user_id,
                    url=track_meta.url,
                    coro=service.download(track_meta)
                )

                if media_content:
                    await send_manager.send(message, media_content, skip_reaction=True,
                                            service="soundcloud", cache_key=track_cache_key,
                                            db_session=db_session)

            except BotError as e:
                logger.warning(f"Skipping track '{track_meta.title}': {e}")
                await log_download_event(db_session, user_id, Services.SOUNDCLOUD, 'failed_download')
                await message.answer(i18n.get('skipped-track', title=track_meta.title))
                continue
