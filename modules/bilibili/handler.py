import logging

from aiofiles import os as aios
from aiogram import F
from aiogram.types import CallbackQuery, FSInputFile, Message
from fluentogram import TranslatorRunner

from models.errors import BotError, ErrorCode
from models.service_list import Services
from modules.router import service_router as router
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils import format_duration, truncate_string
from utils.arq_pool import get_arq_pool
from utils.file_utils import delete_files
from utils.statistics_helper import log_download_event
from utils.url_cache import get_url
from .models import BilibiliCallback
from .service import BilibiliService

logger = logging.getLogger(__name__)


BILIBILI_REGEX = r"https?://(?:www\.)?bilibili\.(?:tv|com)(?:/[a-zA-Z0-9_-]+)?/video/[A-Za-z0-9]+"


@router.message(F.text.regexp(BILIBILI_REGEX))
async def bilibili_handler(message: Message, i18n: TranslatorRunner):
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id

    await task_manager.add_task(
        user_id,
        download_coro=process_bilibili_url(message, i18n),
        message=message,
    )


async def process_bilibili_url(message: Message, i18n: TranslatorRunner):
    """Fetch Bilibili metadata and show format-selection keyboard."""
    if not message.bot or not message.text:
        return None

    await message.bot.send_chat_action(message.chat.id, "find_location")
    process_message = await message.reply(i18n.get("processing"))

    arq = await get_arq_pool("heavy")
    service = BilibiliService(arq=arq)

    media_metadata = await service.get_info(message.text)
    if media_metadata is None:
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message="Failed to get Bilibili metadata",
            url=message.text,
            service=Services.BILIBILI,
            is_logged=True,
        )

    caption = f"<b>{media_metadata.title}</b>\n\n"
    if media_metadata.performer:
        caption += f"<b>Author:</b> {media_metadata.performer}\n"
    if media_metadata.duration:
        caption += f"<b>Duration:</b> {format_duration(media_metadata.duration)}\n\n"
    if media_metadata.description:
        caption += media_metadata.description

    await process_message.delete()

    if media_metadata.cover and await aios.path.exists(media_metadata.cover):
        await message.reply_photo(
            photo=FSInputFile(media_metadata.cover),
            caption=truncate_string(caption, 1024),
            reply_markup=media_metadata.keyboard,
        )
        await delete_files([media_metadata.cover])
    else:
        await message.reply(
            truncate_string(caption, 1024),
            reply_markup=media_metadata.keyboard,
        )

    return None  # Actual download happens in callback


@router.callback_query(BilibiliCallback.filter())
async def bilibili_format_handler(
    callback_query: CallbackQuery,
    callback_data: BilibiliCallback,
    i18n: TranslatorRunner,
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

    active_count = task_manager.get_active_count(user_id)
    if active_count > 0:
        await callback_query.answer(i18n.get("added-to-queue", count=active_count))
    else:
        await callback_query.answer(i18n.get("starting-download"))

    original_message = message.reply_to_message if message.reply_to_message else message
    await message.delete()

    download_task = await task_manager.add_task(
        user_id,
        download_coro=_download_bilibili(
            original_message, url,
            callback_data.type,
            callback_data.video_id,
            callback_data.audio_id,
            user_id,
        ),
        message=original_message,
    )

    if download_task:
        async def send_when_ready():
            try:
                media_content = await download_task
                if media_content:
                    sender = MediaSender()
                    await sender.send(original_message, media_content, service="bilibili")
            except Exception as e:
                logger.error(f"Failed to send Bilibili media: {e}", exc_info=True)

        await task_manager.add_send_task(user_id, send_when_ready())


async def _download_bilibili(
    message: Message,
    url: str,
    media_type: str,
    video_id: str | None,
    audio_id: str | None,
    user_id: int,
):
    """Download the Bilibili and return MediaContent list."""
    arq = await get_arq_pool("heavy")

    if message.bot:
        action = "record_audio" if media_type == "audio" else "record_video"
        await message.bot.send_chat_action(message.chat.id, action)

    media_content = await BilibiliService(arq=arq).download(
        url, video_id=video_id, audio_id=audio_id, media_type=media_type
    )
    await log_download_event(user_id, Services.BILIBILI, "success")
    return media_content
