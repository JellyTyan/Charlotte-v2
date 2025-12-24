import logging

from aiogram import F
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, Message

from core.config import Config
from modules.router import service_router as router
from tasks.task_manager import task_manager
from utils.file_utils import delete_files

logger = logging.getLogger(__name__)


YTMUSIC_REGEX = r"https:\/\/music\.youtube\.com\/(watch\?v=[\w-]+(&[\w=-]+)*|playlist\?list=[\w-]+(&[\w=-]+)*)"

@router.message(F.text.regexp(YTMUSIC_REGEX))
async def ytmusic_handler(message: Message, config: Config):
    if not message.text or not message.from_user:
        return

    await task_manager.add_task(message.from_user.id, process_ytmusic_url(message, config), message)


async def process_ytmusic_url(message: Message, config: Config):
    if not message.text:
        return

    from models.errors import BotError, ErrorCode
    from senders.media_sender import MediaSender
    from utils.statistics_helper import log_download_event

    from .service import YTMusicService

    service = YTMusicService()

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
        track = await service.download(media_metadata.url)

        send_manager = MediaSender()
        await send_manager.send(message, track, message.from_user.id)
        await log_download_event(message.from_user.id, 'YTMusic', 'success')

    elif media_metadata.media_type == "playlist":
        text = f"{media_metadata.title} by {media_metadata.performer}\n"
        if media_metadata.description:
            text += f"<i>{media_metadata.description}</i>\n"
        text += f"Total tracks: {media_metadata.extra.get('track_count', 'Unknown')}\n"
        if media_metadata.extra.get('year'):
            text += f"Year: {media_metadata.extra.get('year')}\n"
        
        if media_metadata.cover:
            await message.answer_photo(
                photo=FSInputFile(media_metadata.cover),
                caption = text,
                parse_mode=ParseMode.HTML
            )
            await delete_files([media_metadata.cover])
        else:
            await message.answer(text, parse_mode=ParseMode.HTML)
        
        await message.reply("Downloading tracks...")
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
                track_content = await service.download(track.url)
                await send_manager.send(message, track_content, message.from_user.id)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to download track {track.title}: {e}")
                failed_count += 1

        total = success_count + failed_count
        logger.info(f"Completed {media_metadata.media_type} download: {success_count}/{total} tracks for user {message.from_user.id}")

        if success_count > 0:
            await log_download_event(message.from_user.id, 'YTMusic', 'success')

        if failed_count > 0:
            await message.answer(f"Downloaded {success_count} tracks. {failed_count} failed.")
        else:
            await message.answer("All tracks downloaded successfully!")
