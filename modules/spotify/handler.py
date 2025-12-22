import logging

from aiogram import F
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile, Message

from core.config import Config
from modules.router import service_router as router
from tasks.task_manager import task_manager
from utils.file_utils import delete_files

logger = logging.getLogger(__name__)


SPOTIFY_REGEX = r"https?://open\.spotify\.com/(track|playlist|album)/([\w-]+)"

@router.message(F.text.regexp(SPOTIFY_REGEX))
async def spotify_handler(message: Message, config: Config):
    if not message.text or not message.from_user:
        return

    logger.debug(f"Spotify handler triggered for URL: {message.text}")
    await task_manager.add_task(message.from_user.id, process_spotify_url(message, config))


async def process_spotify_url(message: Message, config: Config):
    if not message.bot or not message.text:
        return

    logger.debug(f"Processing Spotify URL: {message.text}")
    from models.errors import BotError, ErrorCode
    from senders.media_sender import MediaSender

    from .service import SpotifyService

    service = SpotifyService()

    logger.debug("Getting metadata from Spotify")
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
        if message.bot:
            await message.bot.send_chat_action(message.chat.id, "record_audio")
        track = await service.download(
            media_metadata.performer,
            media_metadata.title,
            media_metadata.cover
        )
        logger.debug(f"Track downloaded: {track}")

        logger.debug("Sending media to user")
        send_manager = MediaSender()
        await send_manager.send(message, track, message.from_user.id)
        logger.debug("Media sent successfully")

    elif media_metadata.media_type == "album" or media_metadata.media_type == "playlist":
        logger.debug("Starting album download")
        text = f"{media_metadata.title} by <a href=\"{media_metadata.performer_url}\">{media_metadata.performer}</a>\n"
        if media_metadata.media_type == "playlist":
            text += f"<i>{media_metadata.description}</i>\n"
        text += f"Total tracks: {media_metadata.extra.get('total_tracks', 'Unknown')}\n"
        if media_metadata.media_type == "album":
            text += f"Release Date: {media_metadata.extra.get('release_date', 'Unknown')}\n"
            # text += f"Genres: {media_metadata.extra["genres"]}\n"
        await message.answer_photo(
            photo=FSInputFile(media_metadata.cover),
            caption = text,
            parse_mode=ParseMode.HTML
        )
        await delete_files([media_metadata.cover])
        await message.reply("Downloading tracks...")
        send_manager = MediaSender()
        success_count = 0
        failed_count = 0

        for track in media_metadata.items:
            if track.performer is None or track.title is None:
                logger.warning(f"Skipping track with missing metadata")
                continue

            try:
                track = await service.download(
                    track.performer,
                    track.title,
                    track.cover
                )
                logger.debug("Sending music to user")
                await send_manager.send(message, track, message.from_user.id)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to download track {track.title}: {e}")
                failed_count += 1

        if failed_count > 0:
            await message.answer(f"Downloaded {success_count} tracks. {failed_count} failed.")
        else:
            await message.answer("All tracks downloaded successfully!")
