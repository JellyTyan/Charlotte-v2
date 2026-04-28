import logging

from aiogram import F
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, Message
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Config
from models.errors import BotError, ErrorCode
from models.service_list import Services
from modules.router import service_router as router
from senders.media_sender import MediaSender
from storage.db.crud import get_chat_settings, get_user_settings
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.file_utils import delete_files
from utils.statistics_helper import log_download_event

from .service import SpotifyService
from .utils import cache_check

logger = logging.getLogger(__name__)


SPOTIFY_REGEX = r"https?://open\.spotify\.com/(track|playlist|album)/([\w-]+)"


@router.message(F.text.regexp(SPOTIFY_REGEX))
async def spotify_handler(message: Message, config: Config, i18n: TranslatorRunner, db_session: AsyncSession):
    if not message.text or not message.from_user:
        return

    url = message.text
    chat_id = message.chat.id
    user_id = message.from_user.id

    # --- Settings ---
    if chat_id < 0:
        settings = await get_chat_settings(db_session, chat_id)
    else:
        settings = await get_user_settings(db_session, chat_id)
    lossless_mode = settings.services.spotify.lossless if settings else False

    # --- Initialize service ---
    arq = await get_arq_pool('light')
    service = SpotifyService(arq=arq)

    # --- Fetch metadata ---
    media_metadata = await service.get_info(url, config=config)
    if not media_metadata:
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message="Failed to get metadata",
            url=url,
            service=Services.SPOTIFY,
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
                service=Services.SPOTIFY,
                is_logged=True
            )

        # Cache-first
        cache_key_lossless = (media_metadata.cache_key + ":lossless") if media_metadata.cache_key else None
        cache_key_default = (media_metadata.cache_key + ":default") if media_metadata.cache_key else None

        if lossless_mode and cache_key_lossless:
            cached = await cache_check(db_session, cache_key_lossless)
        elif cache_key_default:
            cached = await cache_check(db_session, cache_key_default)
        else:
            cached = None

        if cached:
            send_manager = MediaSender()
            await send_manager.send(message, [cached], service="spotify", db_session=db_session)
            return

        if message.bot:
            await message.bot.send_chat_action(chat_id, "record_audio")

        try:
            try:
                media_content = await task_manager.run_download(
                    user_id=user_id,
                    url=url,
                    coro=service.download(media_metadata, lossless_mode=lossless_mode)
                )
            except BotError as e:
                if e.code == ErrorCode.LOSSLESS_UNAVAILABLE:
                    # Tidal недоступен — проверяем дефолтный кэш
                    logger.info(f"Lossless unavailable for {media_metadata.cache_key}, checking default cache")
                    if cache_key_default:
                        default_cached = await cache_check(db_session, cache_key_default)
                        if default_cached:
                            logger.info(f"Serving default from cache for {media_metadata.cache_key}")
                            send_manager = MediaSender()
                            await send_manager.send(message, [default_cached], service="spotify", db_session=db_session)
                            return
                    # Дефолтного кэша нет — скачиваем стандарт
                    media_content = await task_manager.run_download(
                        user_id=user_id,
                        url=url,
                        coro=service.download(media_metadata, lossless_mode=False)
                    )
                else:
                    raise e

            if media_content:
                send_manager = MediaSender()
                if media_content and media_content[0].is_lossless and cache_key_lossless:
                    await send_manager.send(message, media_content, service="spotify",
                                            cache_key=cache_key_lossless, db_session=db_session)
                elif cache_key_default:
                    await send_manager.send(message, media_content, service="spotify",
                                            cache_key=cache_key_default, db_session=db_session)
                else:
                    await send_manager.send(message, media_content, service="spotify", db_session=db_session)

        except BotError as e:
            await log_download_event(db_session, user_id, Services.SPOTIFY, 'failed_download')
            raise e

    # =========================================================================
    # ALBUM / PLAYLIST
    # =========================================================================
    elif media_metadata.media_type in ("album", "playlist"):
        # Check if playlists are allowed in this chat
        if chat_id < 0 and not settings.profile.allow_playlists:
            raise BotError(
                code=ErrorCode.NOT_ALLOWED,
                message="Playlists are not allowed in this chat",
                service=Services.SPOTIFY,
            )

        # Build info message
        text = f"{media_metadata.title} by {media_metadata.performer}\n"
        if media_metadata.media_type == "playlist":
            text += f"<i>{media_metadata.description}</i>\n"
        text += i18n.get('total-tracks', count=media_metadata.extra.get('total_tracks', 'Unknown')) + "\n"
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

        for track_meta in media_metadata.items:
            # --- Cancellation check at top of every iteration ---
            if task_manager.is_cancelled(user_id):
                await message.answer(i18n.get('playlist-stopped'))
                break

            try:
                if not track_meta.performer or not track_meta.title:
                    logger.warning("Skipping track with missing metadata")
                    continue

                cache_key_lossless = (track_meta.cache_key + ":lossless") if track_meta.cache_key else None
                cache_key_default = (track_meta.cache_key + ":default") if track_meta.cache_key else None

                # Cache-first
                if lossless_mode and cache_key_lossless:
                    cached = await cache_check(db_session, cache_key_lossless)
                elif cache_key_default:
                    cached = await cache_check(db_session, cache_key_default)
                else:
                    cached = None

                if cached:
                    await send_manager.send(message, [cached], skip_reaction=True,
                                            service="spotify", db_session=db_session)
                    continue

                # Download the specific track URL (NOT the playlist URL)
                try:
                    media_content = await task_manager.run_download(
                        user_id=user_id,
                        url=track_meta.url,
                        coro=service.download(track_meta, lossless_mode=lossless_mode)
                    )
                except BotError as e:
                    if e.code == ErrorCode.LOSSLESS_UNAVAILABLE:
                        # Tidal недоступен — проверяем дефолтный кэш
                        logger.info(f"Lossless unavailable for {track_meta.cache_key}, checking default cache")
                        if cache_key_default:
                            default_cached = await cache_check(db_session, cache_key_default)
                            if default_cached:
                                logger.info(f"Serving default from cache for {track_meta.cache_key}")
                                await send_manager.send(message, [default_cached], skip_reaction=True,
                                                        service="spotify", db_session=db_session)
                                continue
                        # Дефолтного кэша нет — скачиваем стандарт
                        media_content = await task_manager.run_download(
                            user_id=user_id,
                            url=track_meta.url,
                            coro=service.download(track_meta, lossless_mode=False)
                        )
                    else:
                        raise e

                if media_content:
                    if media_content and media_content[0].is_lossless and cache_key_lossless:
                        await send_manager.send(message, media_content, skip_reaction=True,
                                                service="spotify", cache_key=cache_key_lossless, db_session=db_session)
                    elif cache_key_default:
                        await send_manager.send(message, media_content, skip_reaction=True,
                                                service="spotify", cache_key=cache_key_default, db_session=db_session)
                    else:
                        await send_manager.send(message, media_content, skip_reaction=True,
                                                service="spotify", db_session=db_session)

            except BotError as e:
                logger.warning(f"Skipping track '{track_meta.title}': {e}")
                await log_download_event(db_session, user_id, Services.SPOTIFY, 'failed_download')
                await message.answer(i18n.get('skipped-track', title=track_meta.title))
                continue
