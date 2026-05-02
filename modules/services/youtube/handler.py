import logging

from aiofiles import os as aios
from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from models.errors import BotError, ErrorCode
from models.service_list import Services
from senders.media_sender import MediaSender
from states import YouTubeTrimStates
from storage.db.crud import get_user
from tasks.task_manager import task_manager
from utils import format_duration, truncate_string
from utils.arq_pool import get_arq_pool
from utils.file_utils import delete_files
from utils.statistics_helper import log_download_event
from .service import YouTubeService
from .models import YoutubeCallback, YoutubeTrimCallback
from .utils import get_cache_key, cache_check, parse_time_to_seconds

youtube_router = Router(name="youtube")

logger = logging.getLogger(__name__)


YOUTUBE_REGEX = r"https?://(?:www\.)?(?:m\.)?(?:youtu\.be/|youtube\.com/(?:shorts/|watch\?v=))([\w-]+)"


@youtube_router.message(F.text.regexp(YOUTUBE_REGEX))
async def youtube_handler(message: Message, i18n: TranslatorRunner, db_session: AsyncSession):
    if not message.text or not message.from_user:
        return

    url = message.text
    chat_id = message.chat.id

    if message.bot:
        await message.bot.send_chat_action(chat_id, "find_location")

    process_message = await message.reply(i18n.get('processing'))

    arq = await get_arq_pool('light')
    service = YouTubeService(arq=arq)

    # Получаем метаданные (без скачивания самого видео)
    media_metadata = await service.get_info(url)

    if media_metadata is None:
        await process_message.delete()
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message="Failed to get metadata",
            url=url,
            service=Services.YOUTUBE,
            is_logged=True
        )

    # Собираем красивое описание
    caption = f"<b>{media_metadata.title}</b>\n\n"
    caption += f"<b>Channel:</b> <a href='{media_metadata.performer_url}'>{media_metadata.performer}</a>\n"
    caption += f"<b>Duration:</b> {format_duration(media_metadata.duration) if media_metadata.duration else '00'}\n\n"
    caption += f"{media_metadata.description}"

    await process_message.delete()

    # Отправляем UI с выбором качества
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


@youtube_router.callback_query(YoutubeCallback.filter())
async def format_choice_handler(callback_query: CallbackQuery, callback_data: YoutubeCallback, i18n: TranslatorRunner,
                                db_session: AsyncSession):
    user_id = callback_query.from_user.id
    message = callback_query.message

    if not isinstance(message, Message):
        return

    # Защита от чужих нажатий
    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id != user_id:
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

    # Формируем строку формата для yt-dlp
    if callback_data.type == 'video':
        format_choice = f"youtube_video_{callback_data.format_id}+{callback_data.audio_id}"
    else:
        format_choice = f"youtube_audio_{callback_data.format_id}"

    # Отвечаем юзеру (чтобы часики на кнопке пропали)
    if task_manager.is_cancelled(user_id):
        await callback_query.answer("🛑 Cancelled")
        return
    await callback_query.answer(i18n.get('starting-download'))

    original_message = message.reply_to_message if message.reply_to_message else message

    # --- ПРОВЕРКА PREMIUM И ОПЛАТЫ ---
    user = await get_user(db_session, user_id)
    is_premium = user.is_premium if user else False

    if callback_data.sponsored and not is_premium:
        from modules.payment.video import PaymentService
        payload = f"yt_{callback_data.url_hash}_{format_choice}_{callback_data.resolution}"

        invoice_params = await PaymentService.create_single_download_invoice(
            chat_id=message.chat.id,
            payload=payload,
            provider_token=""
        )
        invoice_params.pop('chat_id', None)

        await message.delete()
        await message.answer_invoice(**invoice_params)
        return

    await message.delete()

    # --- СКАЧИВАНИЕ И ОТПРАВКА ---
    await process_youtube_download(
        message=original_message,
        url=url,
        format_choice=format_choice,
        resolution=callback_data.resolution,
        user_id=user_id,
        db_session=db_session
    )


async def process_youtube_download(message: Message, url: str, format_choice: str, resolution: str, user_id: int, db_session: AsyncSession, payment_charge_id: str = None):
    """Linear download process for both free and paid YouTube downloads, with refund support."""
    arq = await get_arq_pool('light')
    service = YouTubeService(arq=arq)
    send_manager = MediaSender()

    cache_key = get_cache_key(url, resolution)
    cached = await cache_check(db_session, cache_key)
    if cached:
        await send_manager.send(message, cached, service="youtube", db_session=db_session)
        return

    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "record_video")

    try:
        media_content = await task_manager.run_download(
            user_id=user_id,
            url=url,
            coro=service.download(url, format_choice)
        )

        if media_content:
            await send_manager.send(
                message,
                media_content,
                service="youtube",
                cache_key=cache_key,
                db_session=db_session
            )

    except Exception as e:
        await log_download_event(db_session, user_id, Services.YOUTUBE, 'failed_download')

        # Логика возврата средств (Refund), если скачивание упало после оплаты
        if payment_charge_id and message.bot:
            try:
                await message.bot.refund_star_payment(user_id, telegram_payment_charge_id=payment_charge_id)
                from storage.db.crud import update_payment_status
                await update_payment_status(db_session, payment_charge_id, "refunded")
                await message.answer("❌ Download failed. Your payment has been refunded.")
            except Exception as refund_error:
                logger.error(f"Failed to refund payment: {refund_error}")

        if isinstance(e, BotError):
            raise e
        raise BotError(code=ErrorCode.DOWNLOAD_FAILED, message=str(e), service=Services.YOUTUBE, is_logged=True) from e


@youtube_router.callback_query(YoutubeTrimCallback.filter())
async def trim_start_handler(
    callback_query: CallbackQuery,
    callback_data: YoutubeTrimCallback,
    i18n: TranslatorRunner,
    db_session: AsyncSession,
    state: FSMContext
):
    user_id = callback_query.from_user.id
    user = await get_user(db_session, user_id)
    
    if not user or not user.is_premium:
        await callback_query.answer(i18n.get('yt-trim-sponsor-only'), show_alert=True)
        return

    from utils.url_cache import get_url
    url = get_url(callback_data.url_hash)
    if not url:
        await callback_query.answer(i18n.get('url-expired'), show_alert=True)
        return

    await state.update_data(url=url, duration=callback_data.duration)
    await state.set_state(YouTubeTrimStates.waiting_start_time)
    await callback_query.message.answer(i18n.get('yt-trim-ask-start'))
    await callback_query.answer()


@youtube_router.message(YouTubeTrimStates.waiting_start_time)
async def trim_get_start(message: Message, i18n: TranslatorRunner, state: FSMContext):
    if not message.text:
        return
        
    start_sec = parse_time_to_seconds(message.text)
    if start_sec is None:
        await message.reply(i18n.get('yt-trim-invalid-time'))
        return
        
    data = await state.get_data()
    duration = data.get('duration', 0)
    
    if duration > 0 and start_sec >= duration:
        await message.reply(i18n.get('yt-trim-out-of-bounds', duration=format_duration(duration)))
        return
        
    await state.update_data(start_sec=start_sec)
    await state.set_state(YouTubeTrimStates.waiting_end_time)
    await message.reply(i18n.get('yt-trim-ask-end'))


@youtube_router.message(YouTubeTrimStates.waiting_end_time)
async def trim_get_end(message: Message, i18n: TranslatorRunner, state: FSMContext, db_session: AsyncSession):
    if not message.text:
        return
        
    data = await state.get_data()
    end_sec = parse_time_to_seconds(message.text)
    
    if end_sec is None:
        await message.reply(i18n.get('yt-trim-invalid-time'))
        return
        
    if end_sec <= data['start_sec']:
        await message.reply(i18n.get('yt-trim-end-before-start'))
        return
        
    duration = data.get('duration', 0)
    if duration > 0 and end_sec > duration:
        await message.reply(i18n.get('yt-trim-out-of-bounds', duration=format_duration(duration)))
        return
        
    url = data['url']
    start_sec = data['start_sec']
    user_id = message.from_user.id
    
    await state.clear()

    process_message = await message.reply(i18n.get('yt-trim-processing'))

    try:
        if message.bot:
            await message.bot.send_chat_action(message.chat.id, "record_video")
            
        arq = await get_arq_pool('light')
        service = YouTubeService(arq=arq)
        send_manager = MediaSender()
        
        # Format choice is hardcoded to best video/audio for trim by default.
        # Ideally, we would have stored the user's choice, but since Trim
        # is a separate button on the main info card, we just grab the best.
        format_choice = "youtube_video_best" 

        media_content = await task_manager.run_download(
            user_id=user_id,
            url=url,
            coro=service.download_trim(url, format_choice, start_sec, end_sec)
        )

        await process_message.delete()

        if media_content:
            await send_manager.send(
                message,
                media_content,
                service="youtube",
                cache_key=None, # DO NOT CACHE
                db_session=db_session
            )

    except Exception as e:
        await process_message.delete()
        await log_download_event(db_session, user_id, Services.YOUTUBE, 'failed_download')
        
        if isinstance(e, BotError):
            raise e
        raise BotError(code=ErrorCode.DOWNLOAD_FAILED, message=str(e), service=Services.YOUTUBE, is_logged=True) from e
