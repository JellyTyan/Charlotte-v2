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


SOUNDCLOUD_REGEX = r"^https:\/\/(?:on\.soundcloud\.com\/[a-zA-Z0-9]+|soundcloud\.com\/[^\/]+\/(sets\/[^\/]+|[^\/\?\s]+))(?:\?.*)?$"

@router.message(F.text.regexp(SOUNDCLOUD_REGEX))
async def soundcloud_handler(message: Message, config: Config, i18n: TranslatorRunner):
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id
    download_task = await task_manager.add_task(
        user_id,
        download_coro=process_soundcloud_url(message, config, i18n),
        message=message
    )

    if download_task:
        async def send_when_ready():
            try:
                media_content = await download_task
                if media_content:
                    from senders.media_sender import MediaSender
                    send_manager = MediaSender()
                    await send_manager.send(message, media_content, user_id, service="soundcloud")
            except Exception:
                pass
        await task_manager.add_send_task(user_id, send_when_ready())


async def process_soundcloud_url(message: Message, config: Config, i18n: TranslatorRunner):
    if not message.text:
        return None

    user_id = message.from_user.id if message.from_user else message.chat.id

    from models.errors import BotError, ErrorCode
    from senders.media_sender import MediaSender
    from utils.statistics_helper import log_download_event
    from utils.arq_pool import get_arq_pool
    from .service import SoundCloudService

    arq = await get_arq_pool('light')

    # Send chat action for user feedback
    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "choose_sticker")

    service = SoundCloudService(arq=arq)

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
            media_metadata
        )

        await log_download_event(user_id, Services.SOUNDCLOUD, 'success')
        return track

    elif media_metadata.media_type == "album" or media_metadata.media_type == "playlist":
        text = f"{media_metadata.title} by <a href=\"{media_metadata.performer_url}\">{media_metadata.performer}</a>\n"
        if media_metadata.media_type == "playlist" and media_metadata.description:
            text += f"<i>{media_metadata.description}</i>\n"
        text += i18n.get('total-tracks', count=len(media_metadata.items)) + "\n"
        job = await arq.enqueue_job(
            "universal_download",
            url=media_metadata.cover,
            destination=f"storage/temp/{media_metadata.performer} - {media_metadata.title}.jpg",
            _queue_name='light'
        )
        album_cover = await job.result()
        if album_cover:
            await message.answer_photo(
                photo=FSInputFile(album_cover),
                caption = text,
                parse_mode=ParseMode.HTML
            )
            await delete_files([album_cover])
        await message.reply(i18n.get('downloading-tracks'))
        send_manager = MediaSender()

        for track_meta in media_metadata.items:
            async def download_track(metadata=track_meta):
                try:
                    return await service.download(metadata)
                except Exception as e:
                    logger.error(f"Failed to download track: {e}")
                    raise e

            track_download_task = await task_manager.add_task(
                user_id,
                download_coro=download_track(),
                message=None
            )

            if track_download_task:
                async def send_track(task=track_download_task):
                    try:
                        track_content = await task
                        if track_content:
                            await send_manager.send(message, track_content, user_id, skip_reaction=True, service="soundcloud")
                            return True
                        return False
                    except Exception:
                        return False

                await task_manager.add_send_task(user_id, send_track())

        await log_download_event(user_id, Services.SOUNDCLOUD, 'success')
        return None
