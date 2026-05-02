import logging

from aiofiles import os as aios
from aiogram import F, Router
from aiogram.types import CallbackQuery, FSInputFile, Message
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from models.errors import BotError, ErrorCode
from models.service_list import Services
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils import format_duration, truncate_string
from utils.arq_pool import get_arq_pool
from utils.file_utils import delete_files
from utils.statistics_helper import log_download_event
from utils.url_cache import get_url
from .models import NicoVideoCallback
from .service import NicoVideoService
from .utils import get_cache_key, cache_check

nicovideo_router = Router(name='nicovideo')

logger = logging.getLogger(__name__)


# https://www.nicovideo.jp/watch/sm46036084
# https://nicovideo.jp/watch/nm12345678
NICOVIDEO_REGEX = r"https?://(?:www\.)?nicovideo\.jp/watch/\S+"


@nicovideo_router.message(F.text.regexp(NICOVIDEO_REGEX))
async def nicovideo_handler(message: Message, i18n: TranslatorRunner, db_session: AsyncSession):
    if not message.text or not message.from_user:
        return

    url = message.text
    chat_id = message.chat.id

    if message.bot:
        await message.bot.send_chat_action(chat_id, "find_location")

    process_message = await message.reply(i18n.get('processing'))

    arq = await get_arq_pool('heavy')
    service = NicoVideoService(arq=arq)

    media_metadata = await service.get_info(url)

    if media_metadata is None:
        await process_message.delete()
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message="Failed to get NicoVideo metadata",
            url=url,
            service=Services.NICOVIDEO,
            is_logged=True
        )

    caption = f"<b>{media_metadata.title}</b>\n\n"
    if media_metadata.performer:
        caption += f"<b>Author:</b> <a href='{media_metadata.performer_url}'>{media_metadata.performer}</a>\n" if media_metadata.performer_url else f"<b>Author:</b> {media_metadata.performer}\n"
    if media_metadata.duration:
        caption += f"<b>Duration:</b> {format_duration(media_metadata.duration)}\n\n"
    if media_metadata.description:
        caption += f"{media_metadata.description}"

    await process_message.delete()

    if media_metadata.cover and await aios.path.exists(media_metadata.cover):
        await message.reply_photo(
            photo=FSInputFile(media_metadata.cover),
            caption=truncate_string(caption, 1024),
            reply_markup=media_metadata.keyboard
        )
        await delete_files([media_metadata.cover])
    else:
        await message.reply(
            truncate_string(caption, 1024),
            reply_markup=media_metadata.keyboard
        )


@nicovideo_router.callback_query(NicoVideoCallback.filter())
async def nicovideo_format_handler(
    callback_query: CallbackQuery,
    callback_data: NicoVideoCallback,
    i18n: TranslatorRunner,
    db_session: AsyncSession
):
    user_id = callback_query.from_user.id
    message = callback_query.message
    if not isinstance(message, Message):
        return

    # Ownership check
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id != callback_query.from_user.id:
            await callback_query.answer("❌ This is not your request")
            return

    if not callback_data.url_hash:
        await callback_query.answer(i18n.get("invalid-callback"))
        return

    url = get_url(callback_data.url_hash)
    if not url:
        await callback_query.answer(i18n.get("url-expired"))
        return

    if task_manager.is_cancelled(user_id):
        await callback_query.answer("🛑 Cancelled")
        return
    await callback_query.answer(i18n.get("starting-download"))

    original_message = message.reply_to_message if message.reply_to_message else message
    await message.delete()

    await process_nicovideo_download(
        message=original_message,
        url=url,
        media_type=callback_data.type,
        video_id=callback_data.video_id,
        audio_id=callback_data.audio_id,
        resolution=callback_data.resolution,
        user_id=user_id,
        db_session=db_session
    )


async def process_nicovideo_download(
    message: Message,
    url: str,
    media_type: str,
    video_id: str | None,
    audio_id: str | None,
    resolution: str,
    user_id: int,
    db_session: AsyncSession
):
    """Linear download process for NicoVideo downloads."""
    arq = await get_arq_pool("heavy")
    service = NicoVideoService(arq=arq)
    send_manager = MediaSender()

    format_choice = f"{video_id}+{audio_id}" if audio_id and video_id else (video_id or audio_id or "default")
    cache_key = get_cache_key(url, resolution)
    
    cached = await cache_check(db_session, cache_key)
    if cached:
        await send_manager.send(message, cached, service="nicovideo", db_session=db_session)
        return

    if message.bot:
        action = "record_audio" if media_type == "audio" else "record_video"
        await message.bot.send_chat_action(message.chat.id, action)

    try:
        media_content = await task_manager.run_download(
            user_id=user_id,
            url=url,
            coro=service.download(url, video_id=video_id, audio_id=audio_id, media_type=media_type)
        )

        if media_content:
            await send_manager.send(
                message, 
                media_content, 
                service="nicovideo",
                cache_key=cache_key,
                db_session=db_session
            )

    except BotError as e:
        await log_download_event(db_session, user_id, Services.NICOVIDEO, "failed_download")
        raise e
