import logging

from aiogram import F
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, Message

from core.config import Config
from modules.router import service_router as router
from tasks.task_manager import task_manager
from utils.download_utils import download_file
from utils.file_utils import delete_files

logger = logging.getLogger(__name__)


SOUNDCLOUD_REGEX = r"^https:\/\/(?:on\.soundcloud\.com\/[a-zA-Z0-9]+|soundcloud\.com\/[^\/]+\/(sets\/[^\/]+|[^\/\?\s]+))(?:\?.*)?$"

@router.message(F.text.regexp(SOUNDCLOUD_REGEX))
async def soundcloud_handler(message: Message, config: Config):
    if not message.text or not message.from_user:
        return

    logger.debug(f"Soundcloud handler triggered for URL: {message.text}")
    await task_manager.add_task(message.from_user.id, process_soundcloud_url(message, config))


async def process_soundcloud_url(message: Message, config: Config):
    if not message.bot or not message.text:
        return

    logger.debug(f"Processing Soundcloud URL: {message.text}")
    from models.errors import BotError, ErrorCode
    from senders.media_sender import MediaSender

    from .service import SoundCloudService

    service = SoundCloudService()

    logger.debug("Getting metadata from Soundcloud")
    media_metadata = await service.get_info(message.text, config=config)
    if not media_metadata:
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message="Failed to get metadata",
            url=message.text,
            is_logged=True
        )
    logger.debug(f"Metadata received: {media_metadata.title} by {media_metadata.performer}")

    if media_metadata.media_type == "track":
        if not media_metadata.performer or not media_metadata.title:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Failed to get metadata",
                url=message.text,
                is_logged=True
            )
        logger.debug("Starting track download")
        track = await service.download(
            media_metadata.url
        )
        logger.debug(f"Track downloaded: {track}")

        logger.debug("Sending media to user")
        send_manager = MediaSender()
        await send_manager.send(message, track, message.from_user.id)
        logger.debug("Media sent successfully")

    elif media_metadata.media_type == "album" or media_metadata.media_type == "playlist":
        logger.debug("Starting album download")
        text = f"{media_metadata.title} by <a href=\"{media_metadata.performer_url}\">{media_metadata.performer}</a>\n"
        file = await download_file(media_metadata.cover, f"storage/temp/{media_metadata.performer} - {media_metadata.title}.jpg")
        await message.answer_photo(
            photo=FSInputFile(file),
            caption = text,
            parse_mode=ParseMode.HTML
        )
        await delete_files([file])
        await message.reply("Downloading tracks...")
        send_manager = MediaSender()
        for track in media_metadata.items:
            track = await service.download(
                track.url
            )
            logger.debug("Sending music to user")
            await send_manager.send(message, track, message.from_user.id)

        await message.answer("All tracks downloaded successfully!")
