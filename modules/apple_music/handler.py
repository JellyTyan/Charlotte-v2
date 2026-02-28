import logging

from aiogram import F
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, Message
from fluentogram import TranslatorRunner

from core.config import Config
from modules.router import service_router as router
from tasks.task_manager import task_manager
from utils.file_utils import delete_files
from models.service_list import Services

logger = logging.getLogger(__name__)


APPLE_REGEX = r"^https?:\/\/music\.apple\.com\/[a-z]{2}\/(album|playlist|song)\/[^\s]+$"

@router.message(F.text.regexp(APPLE_REGEX))
async def apple_handler(message:Message, config: Config, i18n: TranslatorRunner):
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id

    download_task = await task_manager.add_task(
        user_id,
        download_coro=process_apple_url(message, config, i18n),
        message=message
    )

    if download_task:
        async def send_when_ready():
            try:
                media_content = await download_task
                if media_content:
                    from senders.media_sender import MediaSender
                    send_manager = MediaSender()
                    await send_manager.send(message, media_content, user_id, service="apple_music")
            except Exception:
                pass
        await task_manager.add_send_task(user_id, send_when_ready())


async def process_apple_url(message: Message, config: Config, i18n: TranslatorRunner):
    if not message.text:
        return None
    user = message.from_user
    if not user:
        return None

    from models.errors import BotError, ErrorCode
    from senders.media_sender import MediaSender
    from utils.statistics_helper import log_download_event
    from storage.db.crud import get_user_settings
    from utils.arq_pool import get_arq_pool
    from .service import AppleMusicService

    # Initialize ARQ pool
    arq = await get_arq_pool('light')
    service = AppleMusicService(arq=arq)

    # Get user settings for lossless mode
    user_settings = await get_user_settings(user.id)
    lossless_mode = user_settings.services.applemusic.lossless if user_settings else False

    media_metadata = await service.get_info(message.text, config=config)
    if not media_metadata:
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message="Failed to get metadata",
            url=message.text,
            is_logged=True
        )

    if media_metadata.media_type == "track":
        if not media_metadata.performer or not media_metadata.title:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Failed to get metadata",
                url=message.text,
                is_logged=True
            )
        track = await service.download(
            media_metadata.performer,
            media_metadata.title,
            media_metadata.cover,
            media_metadata.full_size_cover,
            lossless_mode=lossless_mode
        )

        await log_download_event(user.id, Services.APPLE_MUSIC, 'success')
        return track

    elif media_metadata.media_type == "album" or media_metadata.media_type == "playlist":
        text = f"{media_metadata.title} by {media_metadata.performer}\n"
        if media_metadata.media_type == "playlist":
            text += f"<i>{media_metadata.description}</i>\n"
        text += i18n.get('total-tracks', count=media_metadata.extra.get('track_count', 'Unknown')) + "\n"
        if media_metadata.media_type == "album":
            text += i18n.get('release-date', date=media_metadata.extra.get('release_date', 'Unknown')) + "\n"
        if media_metadata.cover:
            await message.answer_photo(
                photo=FSInputFile(media_metadata.cover),
                caption = text,
                parse_mode=ParseMode.HTML
            )
            await delete_files([media_metadata.cover])
        await message.reply(i18n.get('downloading-tracks'))
        send_manager = MediaSender()

        for track_meta in media_metadata.items:
            if track_meta.performer is None or track_meta.title is None:
                logger.warning(f"Skipping track with missing metadata")
                continue
            async def download_track(performer=track_meta.performer, title=track_meta.title, cover=track_meta.cover, full_cover=track_meta.full_size_cover, lossless_mode=lossless_mode):
                try:
                    return await service.download(performer, title, cover, full_cover, lossless_mode=lossless_mode)
                except Exception as e:
                    logger.error(f"Failed to download track {title}: {e}")
                    raise e

            track_download_task = await task_manager.add_task(
                user.id,
                download_coro=download_track(),
                message=None
            )

            if track_download_task:
                async def send_track(task=track_download_task):
                    try:
                        track_content = await task
                        if track_content:
                            await send_manager.send(message, track_content, user.id, skip_reaction=True, service="apple_music")
                            return True
                        return False
                    except Exception:
                        return False

                await task_manager.add_send_task(user.id, send_track())

        await log_download_event(user.id, Services.APPLE_MUSIC, 'success')
        return None
