import logging

from aiogram import F
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, Message
from fluentogram import TranslatorRunner

from core.config import Config
from modules.router import service_router as router
from tasks.task_manager import task_manager
from utils.download_utils import download_file
from utils.file_utils import delete_files

logger = logging.getLogger(__name__)


SOUNDCLOUD_REGEX = r"^https:\/\/(?:on\.soundcloud\.com\/[a-zA-Z0-9]+|soundcloud\.com\/[^\/]+\/(sets\/[^\/]+|[^\/\?\s]+))(?:\?.*)?$"

@router.message(F.text.regexp(SOUNDCLOUD_REGEX))
async def soundcloud_handler(message: Message, config: Config, i18n: TranslatorRunner):
    if not message.text or not message.from_user:
        return

    await task_manager.add_task(message.from_user.id, process_soundcloud_url(message, config, i18n), message)


async def process_soundcloud_url(message: Message, config: Config, i18n: TranslatorRunner):
    if not message.text:
        return

    from models.errors import BotError, ErrorCode
    from senders.media_sender import MediaSender
    from utils.statistics_helper import log_download_event

    from .service import SoundCloudService

    service = SoundCloudService()

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
        if message.bot:
            await message.bot.send_chat_action(message.chat.id, "record_audio")
        track = await service.download(
            media_metadata.url
        )

        send_manager = MediaSender()
        await send_manager.send(message, track, message.from_user.id)
        await log_download_event(message.from_user.id, 'SoundCloud', 'success')

    elif media_metadata.media_type == "album" or media_metadata.media_type == "playlist":
        text = f"{media_metadata.title} by <a href=\"{media_metadata.performer_url}\">{media_metadata.performer}</a>\n"
        file = await download_file(media_metadata.cover, f"storage/temp/{media_metadata.performer} - {media_metadata.title}.jpg")
        await message.answer_photo(
            photo=FSInputFile(file),
            caption = text,
            parse_mode=ParseMode.HTML
        )
        await delete_files([file])
        await message.reply(i18n.get('downloading-tracks'))
        send_manager = MediaSender()
        success_count = 0
        failed_count = 0

        for track in media_metadata.items:
            try:
                track = await service.download(
                    track.url
                )
                await send_manager.send(message, track, message.from_user.id)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to download track: {e}")
                failed_count += 1

        total = success_count + failed_count
        logger.info(f"Completed {media_metadata.media_type} download: {success_count}/{total} tracks for user {message.from_user.id}")

        if success_count > 0:
            await log_download_event(message.from_user.id, 'SoundCloud', 'success')

        if failed_count > 0:
            await message.answer(i18n.get('download-stats', success=success_count, failed=failed_count))
        else:
            await message.answer(i18n.get('all-tracks-success'))
