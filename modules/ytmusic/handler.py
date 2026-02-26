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


YTMUSIC_REGEX = r"https:\/\/music\.youtube\.com\/(watch\?v=[\w-]+(&[\w=-]+)*|playlist\?list=[\w-]+(&[\w=-]+)*)"

@router.message(F.text.regexp(YTMUSIC_REGEX))
async def ytmusic_handler(message: Message, config: Config, i18n: TranslatorRunner):
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id
    download_task = await task_manager.add_task(
        user_id,
        download_coro=process_ytmusic_url(message, config, i18n),
        message=message
    )

    if download_task:
        async def send_when_ready():
            try:
                media_content = await download_task
                if media_content:
                    from senders.media_sender import MediaSender
                    send_manager = MediaSender()
                    await send_manager.send(message, media_content, user_id, service="youtube_music")
            except Exception:
                pass
        await task_manager.add_send_task(user_id, send_when_ready())


async def process_ytmusic_url(message: Message, config: Config, i18n: TranslatorRunner):
    if not message.text:
        return None

    user = message.from_user
    if not user:
        return None

    from models.errors import BotError, ErrorCode
    from senders.media_sender import MediaSender
    from utils.statistics_helper import log_download_event
    from utils.arq_pool import get_arq_pool

    from .service import YTMusicService

    arq = await get_arq_pool('light')

    service = YTMusicService(arq=arq)

    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "choose_sticker")

    media_metadata = await service.get_info(message.text, config=config)
    if not media_metadata:
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message="Failed to get metadata",
            url=message.text,
            service=Services.YTMUSIC,
            is_logged=True
        )

    if media_metadata.media_type == "track":
        if not media_metadata.performer or not media_metadata.title:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Failed to get metadata",
                url=message.text,
                service=Services.YTMUSIC,
                is_logged=True
            )
        if message.bot:
            await message.bot.send_chat_action(message.chat.id, "record_audio")
        track = await service.download(media_metadata.url)

        await log_download_event(user.id, Services.YTMUSIC, 'success')
        return track

    elif media_metadata.media_type == "playlist":
        text = f"{media_metadata.title} by {media_metadata.performer}\n"
        if media_metadata.description:
            text += f"<i>{media_metadata.description}</i>\n"
        text += i18n.get('total-tracks', count=media_metadata.extra.get('track_count', 'Unknown')) + "\n"
        if media_metadata.extra.get('year'):
            text += i18n.get('year', year=media_metadata.extra.get('year')) + "\n"

        if media_metadata.cover:
            await message.answer_photo(
                photo=FSInputFile(media_metadata.cover),
                caption = text,
                parse_mode=ParseMode.HTML
            )
            await delete_files([media_metadata.cover])
        else:
            await message.answer(text, parse_mode=ParseMode.HTML)

        await message.reply(i18n.get('downloading-tracks'))
        send_manager = MediaSender()

        for track_meta in media_metadata.items:
            if track_meta.performer is None or track_meta.title is None:
                logger.warning(f"Skipping track with missing metadata")
                continue
            async def download_track(url=track_meta.url):
                try:
                    return await service.download(url)
                except Exception as e:
                    logger.error(f"Failed to download track: {e}")
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
                            await send_manager.send(message, track_content, user.id, skip_reaction=True, service="youtube_music")
                            return True
                        return False
                    except Exception:
                        return False

                await task_manager.add_send_task(user.id, send_track())

        await log_download_event(user.id, Services.YTMUSIC, 'success')
        return None
