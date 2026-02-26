import logging

from aiofiles import os as aios
from aiogram import F
from aiogram.types import CallbackQuery, FSInputFile, Message
from fluentogram import TranslatorRunner

from models.errors import BotError, ErrorCode
from modules.router import service_router as router
from tasks.task_manager import task_manager
from utils import format_duration, truncate_string
from utils.file_utils import delete_files
from models.service_list import Services
from utils.arq_pool import get_arq_pool
from .service import YouTubeService
from .models import YoutubeCallback

logger = logging.getLogger(__name__)


YOUTUBE_REGEX = r"https?://(?:www\.)?(?:m\.)?(?:youtu\.be/|youtube\.com/(?:shorts/|watch\?v=))([\w-]+)"

@router.message(F.text.regexp(YOUTUBE_REGEX))
async def youtube_handler(message: Message, i18n: TranslatorRunner):
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id

    # Start download task (for YouTube this is just getting metadata and showing UI)
    download_task = await task_manager.add_task(
        user_id,
        download_coro=process_youtube_url(message, i18n),
        message=message
    )


async def process_youtube_url(message: Message, i18n: TranslatorRunner):
    """Get YouTube metadata and display format selection UI"""
    if not message.bot or not message.text:
        return None

    await message.bot.send_chat_action(message.chat.id, "find_location")
    process_message = await message.reply(i18n.get('processing'))

    arq = await get_arq_pool('light')

    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "choose_sticker")

    media_metadata = await YouTubeService(arq=arq).get_info(message.text)
    if media_metadata is None:
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message="Failed to get metadata",
            url=message.text,
            service=Services.YOUTUBE,
            is_logged=True
        )

    caption = f"<b>{media_metadata.title}</b>\n\n"
    caption += f"<b>Channel:</b><a href='{media_metadata.performer_url}'> {media_metadata.performer}</a>\n"
    caption += f"<b>Duration:</b> {format_duration(media_metadata.duration) if media_metadata.duration else '00'}\n\n"
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

    # YouTube handler doesn't need send queue, it just shows UI
    return None


@router.callback_query(YoutubeCallback.filter())
async def format_choice_handler(callback_query: CallbackQuery, callback_data: YoutubeCallback, i18n: TranslatorRunner):
    user_id = callback_query.from_user.id
    message = callback_query.message
    if not isinstance(message, Message):
        return

    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id != callback_query.from_user.id:
            await callback_query.answer("❌ This is not your request")
            return

    from utils.url_cache import get_url

    if not callback_data.url_hash:
        await callback_query.answer(i18n.get('invalid-callback'))
        return

    url = get_url(callback_data.url_hash)
    if not url:
        await callback_query.answer(i18n.get('url-expired'))
        return

    if callback_data.type == 'video':
        format_choice = f"youtube_video_{callback_data.format_id}+{callback_data.audio_id}"
    else:
        format_choice = f"youtube_audio_{callback_data.format_id}"

    active_count = task_manager.get_active_count(user_id)
    if active_count > 0:
        await callback_query.answer(i18n.get('added-to-queue', count=active_count))
    else:
        await callback_query.answer(i18n.get('starting-download'))

    original_message = message.reply_to_message if message.reply_to_message else message

    # Premium Logic
    from storage.db.crud import get_user
    user = await get_user(user_id)
    is_premium = user.is_premium if user else False

    # Check if format requires premium (sponsored flag in callback_data)
    if callback_data.sponsored and not is_premium:
        from modules.payment.service import PaymentService

        # Format payload: yt_URLHASH_FORMAT
        payload = f"yt_{callback_data.url_hash}_{format_choice}"

        invoice_params = await PaymentService.create_single_download_invoice(
            chat_id=message.chat.id,
            payload=payload,
            provider_token="" # Empty for Stars
        )

        # Remove chat_id since answer_invoice uses message.chat.id automatically
        invoice_params.pop('chat_id', None)

        await message.delete()
        await message.answer_invoice(**invoice_params)
        return

    await message.delete()

    # Start download task
    download_task = await task_manager.add_task(
        user_id,
        download_coro=download_youtube_media(original_message, url, format_choice, user_id, ""),
        message=original_message
    )

    # When download completes, queue send task
    if download_task:
        async def send_when_ready():
            try:
                media_content = await download_task
                if media_content:
                    from senders.media_sender import MediaSender
                    send_manager = MediaSender()
                    await send_manager.send(original_message, media_content, user_id, service="youtube")
            except Exception as e:
                # Error already logged in download task
                pass

        await task_manager.add_send_task(user_id, send_when_ready())


async def download_youtube_media(message: Message, url: str, format_choice: str, user_id: int, payment_charge_id: str = ""):
    """Download YouTube media and return content"""
    from utils.statistics_helper import log_download_event

    arq = await get_arq_pool('light')

    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "record_video")

    try:
        media_content = await YouTubeService(arq=arq).download(url, format_choice)

        await log_download_event(user_id, Services.YOUTUBE, 'success')
        return media_content
    except BotError as e:
        # Refund if download failed and user paid
        if payment_charge_id and e.code == ErrorCode.DOWNLOAD_FAILED:
            if message.bot:
                try:
                    await message.bot.refund_star_payment(user_id, telegram_payment_charge_id=payment_charge_id)
                    await message.reply("❌ Download failed. Your payment has been refunded.")

                    # Update payment status in DB
                    from storage.db import update_payment_status
                    await update_payment_status(payment_charge_id, "refunded")
                except Exception as refund_error:
                    logger.error(f"Failed to refund payment: {refund_error}")
        raise e
