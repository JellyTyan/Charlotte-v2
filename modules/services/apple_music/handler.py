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

from .service import AppleMusicService
from .utils import cache_check

apple_router = Router(name="applemusic")

logger = logging.getLogger(__name__)


APPLE_REGEX = r"^https?:\/\/music\.apple\.com\/[a-z]{2}\/(album|playlist|song)\/[^\s]+$"

@apple_router.message(F.text.regexp(APPLE_REGEX))
async def apple_handler(message: Message, config: Config, i18n: TranslatorRunner, db_session: AsyncSession):
    url = message.text
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Getting chat/user settings
    if chat_id < 0:
        settings = await get_chat_settings(db_session, chat_id)
    else:
        settings = await get_user_settings(db_session, chat_id)
    lossless_mode = settings.services.applemusic.lossless if settings else False

    # Initialize Apple Music Service
    arq = await get_arq_pool('light')
    service = AppleMusicService(arq=arq)

    # Getting info
    media_metadata = await service.get_info(message.text, config=config)
    if not media_metadata:
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message="Failed to get metadata",
            url=message.text,
            service=Services.APPLE_MUSIC,
            is_logged=True
        )

    if media_metadata.media_type in ["album", "playlist"]:
        # Check if playlists are allowed in chat
        if chat_id < 0 and not settings.profile.allow_playlists:
            raise BotError(
                code=ErrorCode.NOT_ALLOWED,
                message="Playlists are not allowed in this chat",
                service=Services.APPLE_MUSIC,
            )

        # Build playlist info message
        text = f"{media_metadata.title} by {media_metadata.performer}\n"
        if media_metadata.media_type == "playlist":
            text += f"<i>{media_metadata.description}</i>\n"
        text += i18n.get('total-tracks', count=media_metadata.extra.get('track_count', 'Unknown')) + "\n"
        if media_metadata.media_type == "album":
            text += i18n.get('release-date', date=media_metadata.extra.get('release_date', 'Unknown')) + "\n"
        if media_metadata.cover:
            await message.answer_photo(
                photo=FSInputFile(media_metadata.cover),
                caption=text,
                parse_mode=ParseMode.HTML
            )
            await delete_files([media_metadata.cover])
        await message.reply(i18n.get('downloading-tracks'))

        send_manager = MediaSender()

        # Downloading
        for track_meta in media_metadata.items:
            if task_manager.is_cancelled(user_id):
                await message.answer(i18n.get('playlist-stopped'))
                break
            try:
                if track_meta.performer is None or track_meta.title is None:
                    logger.warning("Skipping track with missing metadata")
                    continue

                cache_key_lossless = track_meta.cache_key + ":lossless"
                cache_key_default = track_meta.cache_key + ":default"

                if lossless_mode:
                    cached = await cache_check(db_session, cache_key_lossless)
                else:
                    cached = await cache_check(db_session, cache_key_default)

                if cached:
                    await send_manager.send(message, [cached], skip_reaction=True, service="applemusic", db_session=db_session)
                    continue

                try:
                    media_content = await task_manager.run_download(
                        user_id=chat_id,
                        url=track_meta.url,
                        coro=service.download(track_meta, lossless_mode=lossless_mode)
                    )
                except BotError as e:
                    if e.code == ErrorCode.LOSSLESS_UNAVAILABLE:
                        # Tidal недоступен — проверяем дефолтный кэш без лишней скачки
                        logger.info(f"Lossless unavailable for {track_meta.cache_key}, checking default cache")
                        default_cached = await cache_check(db_session, cache_key_default)
                        if default_cached:
                            logger.info(f"Serving default from cache for {track_meta.cache_key}")
                            await send_manager.send(message, [default_cached], skip_reaction=True, service="applemusic", db_session=db_session)
                            continue
                        # Дефолтного кэша нет — скачиваем стандарт
                        media_content = await task_manager.run_download(
                            user_id=chat_id,
                            url=track_meta.url,
                            coro=service.download(track_meta, lossless_mode=False)
                        )
                    else:
                        raise e

                if media_content:
                    if media_content.is_lossless:
                        await send_manager.send(message, [media_content], skip_reaction=True, service="applemusic", cache_key=cache_key_lossless, db_session=db_session)
                    else:
                        await send_manager.send(message, [media_content], skip_reaction=True, service="applemusic", cache_key=cache_key_default, db_session=db_session)
            except BotError as e:
                logger.warning(f"Skipping track '{track_meta.title}': {e}")
                await log_download_event(db_session, user_id, Services.APPLE_MUSIC, 'failed_download')
                await message.answer(i18n.get('skipped-track', title=track_meta.title))
                continue
    else:
        # Single track download
        try:
            cache_key_lossless = media_metadata.cache_key + ":lossless"
            cache_key_default = media_metadata.cache_key + ":default"

            if lossless_mode:
                cached = await cache_check(db_session, cache_key_lossless)
            else:
                cached = await cache_check(db_session, cache_key_default)

            if cached:
                send_manager = MediaSender()
                await send_manager.send(message, [cached], skip_reaction=True, service="applemusic", db_session=db_session)
            else:
                try:
                    media_content = await task_manager.run_download(
                        user_id=chat_id,
                        url=url,
                        coro=service.download(media_metadata, lossless_mode=lossless_mode)
                    )
                except BotError as e:
                    if e.code == ErrorCode.LOSSLESS_UNAVAILABLE:
                        # Tidal недоступен — проверяем дефолтный кэш без лишней скачки
                        logger.info(f"Lossless unavailable for {media_metadata.cache_key}, checking default cache")
                        default_cached = await cache_check(db_session, cache_key_default)
                        if default_cached:
                            logger.info(f"Serving default from cache for {media_metadata.cache_key}")
                            send_manager = MediaSender()
                            await send_manager.send(message, [default_cached], skip_reaction=True, service="applemusic", db_session=db_session)
                            return
                        # Дефолтного кэша нет — скачиваем стандарт
                        media_content = await task_manager.run_download(
                            user_id=chat_id,
                            url=url,
                            coro=service.download(media_metadata, lossless_mode=False)
                        )
                    else:
                        raise e

                if media_content:
                    send_manager = MediaSender()
                    if media_content.is_lossless:
                        await send_manager.send(message, [media_content], skip_reaction=True, service="applemusic",
                                            cache_key=cache_key_lossless, db_session=db_session)
                    else:
                        await send_manager.send(message, [media_content], skip_reaction=True, service="applemusic",
                                            cache_key=cache_key_default, db_session=db_session)

        except BotError as e:
            await log_download_event(db_session, user_id, Services.APPLE_MUSIC, 'failed_download')
            raise e