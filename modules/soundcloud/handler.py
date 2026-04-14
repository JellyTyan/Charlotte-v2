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
from storage.db.crud import get_user_settings, get_chat_settings
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.file_utils import delete_files
from utils.statistics_helper import log_download_event
from .service import SoundCloudService

logger = logging.getLogger(__name__)


SOUNDCLOUD_REGEX = r"^https:\/\/(?:on\.soundcloud\.com\/[a-zA-Z0-9]+|soundcloud\.com\/[^\/]+\/(sets\/[^\/]+|[^\/\?\s]+))(?:\?.*)?$"

@router.message(F.text.regexp(SOUNDCLOUD_REGEX))
async def soundcloud_handler(message: Message, config: Config, i18n: TranslatorRunner, db_session: AsyncSession):
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id
    download_task = await task_manager.add_task(
        user_id,
        download_coro=process_soundcloud_url(message, config, i18n, db_session),
        message=message
    )

    if download_task:
        async def send_when_ready():
            try:
                media_content = await download_task
                if media_content:
                    send_manager = MediaSender()
                    await send_manager.send(message, media_content, service=\"soundcloud\", db_session=db_session)
            except Exception:
                pass
        await task_manager.add_send_task(user_id, send_when_ready())


async def process_soundcloud_url(message: Message, config: Config, i18n: TranslatorRunner, db_session: AsyncSession):
    if not message.text:
        return None

    chat_id = message.chat.id
    user = message.from_user
    if not chat_id or not user:
        return None

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
            service=Services.SOUNDCLOUD,
            is_logged=True
        )

    if chat_id < 0:
        settings = await get_chat_settings(db_session, chat_id)
    else:
        settings = await get_user_settings(db_session, chat_id)

    if media_metadata.media_type == "track":
        if not media_metadata.performer or not media_metadata.title:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Failed to get metadata",
                url=message.text,
                service=Services.SOUNDCLOUD,
                is_logged=True
            )
        if message.bot:
            await message.bot.send_chat_action(message.chat.id, "record_audio")
        track = await service.download(
            media_metadata
        )

        await log_download_event(db_session, user.id, Services.SOUNDCLOUD, 'success')
        return track

    elif media_metadata.media_type == "album" or media_metadata.media_type == "playlist":
        if chat_id < 0 and settings.profile.allow_playlists == False:
            raise BotError(
                code=ErrorCode.NOT_ALLOWED,
                message="Playlists are not allowed in this chat",
                service=Services.SOUNDCLOUD,
            )
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
        try:
            album_cover = await job.result()
        except Exception as e:
            logger.warning(f"Failed to download album cover: {e}")
            album_cover = None
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
                    raise

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
                            await send_manager.send(message, track_content, skip_reaction=True, service=\"soundcloud\", db_session=db_session)
                            return True
                        return False
                    except Exception:
                        return False

                await task_manager.add_send_task(user.id, send_track())

        await log_download_event(db_session, user.id, Services.SOUNDCLOUD, 'success')
        return None
