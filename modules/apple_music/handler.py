import logging

from aiogram import F
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, Message
from fluentogram import TranslatorRunner

from core.config import Config
from modules.router import service_router as router
from tasks.task_manager import task_manager
from utils.file_utils import delete_files

logger = logging.getLogger(__name__)


APPLE_REGEX = r"^https?:\/\/music\.apple\.com\/[a-z]{2}\/(album|playlist|song)\/[^\s]+$"

@router.message(F.text.regexp(APPLE_REGEX))
async def apple_handler(message: Message, config: Config, i18n: TranslatorRunner):
    if not message.text or not message.from_user:
        return

    await task_manager.add_task(message.from_user.id, process_apple_url(message, config, i18n), message)


async def process_apple_url(message: Message, config: Config, i18n: TranslatorRunner):
    if not message.text:
        return

    from models.errors import BotError, ErrorCode
    from senders.media_sender import MediaSender
    from utils.statistics_helper import log_download_event
    from storage.db.crud import get_user_settings

    from .service import AppleMusicService

    service = AppleMusicService()

    # Get user settings for lossless mode
    user_settings = await get_user_settings(message.from_user.id)
    lossless_mode = user_settings.lossless_mode if user_settings else False

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

        send_manager = MediaSender()
        await send_manager.send(message, track, message.from_user.id)
        await log_download_event(message.from_user.id, 'AppleMusic', 'success')

    elif media_metadata.media_type == "album" or media_metadata.media_type == "playlist":
        text = f"{media_metadata.title} by {media_metadata.performer}\n"
        if media_metadata.media_type == "playlist":
            text += f"<i>{media_metadata.description}</i>\n"
        text += i18n.get('total-tracks', count=media_metadata.extra.get('track_count', 'Unknown')) + "\n"
        if media_metadata.media_type == "album":
            text += i18n.get('release-date', date=media_metadata.extra.get('release_date', 'Unknown')) + "\n"
        await message.answer_photo(
            photo=FSInputFile(media_metadata.cover),
            caption = text,
            parse_mode=ParseMode.HTML
        )
        await delete_files([media_metadata.cover])
        await message.reply(i18n.get('downloading-tracks'))
        send_manager = MediaSender()
        success_count = 0
        failed_count = 0

        for track in media_metadata.items:
            if track.performer is None or track.title is None:
                logger.warning(f"Skipping track with missing metadata")
                continue
            if message.bot:
                await message.bot.send_chat_action(message.chat.id, "record_audio")
            try:
                track = await service.download(
                    track.performer,
                    track.title,
                    track.cover,
                    track.full_size_cover
                )
                await send_manager.send(message, track, message.from_user.id)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to download track {track.title}: {e}")
                failed_count += 1

        total = success_count + failed_count
        logger.info(f"Completed {media_metadata.media_type} download: {success_count}/{total} tracks for user {message.from_user.id}")

        if success_count > 0:
            await log_download_event(message.from_user.id, 'AppleMusic', 'success')

        if failed_count > 0:
            await message.answer(i18n.get('download-stats', success=success_count, failed=failed_count))
        else:
            await message.answer(i18n.get('all-tracks-success'))
