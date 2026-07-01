import logging
import httpx
import asyncio
from pathlib import Path
from typing import Any

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message, InlineKeyboardButton
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import StateFilter
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.service_list import Services
from senders.media_sender import MediaSender
from states.youtube import YouTubeStates, YouTubeDialogStates
from storage.db.crud import get_user
from tasks.task_manager import task_manager
from utils import format_duration, truncate_string
from utils.statistics_helper import log_download_event
from aiogram_dialog import DialogManager
from .dialogs import youtube_dialog

from .models import YoutubeMenuCallback, YoutubeQualityCallback
from .utils import get_cache_key, cache_check, parse_time_range

youtube_router = Router(name="youtube")
youtube_router.include_router(youtube_dialog)
logger = logging.getLogger(__name__)

YOUTUBE_REGEX = r"https?://(?:www\.)?(?:m\.)?(?:youtu\.be/|youtube\.com/(?:shorts/|watch\?v=))([\w-]+)"


def handle_youtube_api_errors(res: httpx.Response, url: str):
    if res.status_code == 200:
        return

    err_msg = ""
    try:
        data = res.json()
        if isinstance(data, dict):
            err_msg = data.get("message", "")
    except Exception:
        err_msg = res.text or ""

    err_msg_lower = err_msg.lower()

    if res.status_code == 451 or "geo" in err_msg_lower or "country" in err_msg_lower or "region" in err_msg_lower or "geoblocked" in err_msg_lower:
        raise BotError(
            code=ErrorCode.REGION_RESTRICTED,
            url=url,
            service=Services.YOUTUBE,
            message=f"Region blocked: {err_msg}",
            is_logged=False,
            critical=False
        )

    if res.status_code == 401:
        if "members-only" in err_msg_lower or "private" in err_msg_lower:
            code = ErrorCode.PRIVATE_CONTENT
        else:
            code = ErrorCode.AGE_RESTRICTED
        raise BotError(
            code=code,
            url=url,
            service=Services.YOUTUBE,
            message=f"Access denied: {err_msg}",
            is_logged=False,
            critical=False
        )

    if res.status_code == 404:
        raise BotError(
            code=ErrorCode.NOT_FOUND,
            url=url,
            service=Services.YOUTUBE,
            message=f"Not found: {err_msg}",
            is_logged=True,
            critical=False
        )

    if res.status_code == 413 or "too large" in err_msg_lower:
        raise BotError(
            code=ErrorCode.LARGE_FILE,
            url=url,
            service=Services.YOUTUBE,
            message=f"File too large: {err_msg}",
            is_logged=True,
            critical=False
        )

    raise BotError(
        code=ErrorCode.INTERNAL_ERROR,
        url=url,
        service=Services.YOUTUBE,
        message=f"Server error ({res.status_code}): {err_msg}",
        is_logged=True,
        critical=res.status_code >= 500
    )


async def get_youtube_metadata(http_client: httpx.AsyncClient, url: str) -> dict:
    payload = {"url": url}
    try:
        res = await http_client.post(
            "http://media-core:9546/youtube/metadata",
            json=payload,
            timeout=30.0
        )
    except Exception as e:
        logger.error(f"Failed to fetch YouTube metadata from media-core: {e}")
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            url=url,
            service=Services.YOUTUBE,
            message=f"Failed to connect to media-core: {e}",
            is_logged=True,
            critical=True
        )

    handle_youtube_api_errors(res, url)

    res_json = res.json()
    if res_json.get("status") != "success" or "data" not in res_json:
        raise BotError(
            code=ErrorCode.NOT_FOUND,
            url=url,
            service=Services.YOUTUBE,
            message=f"Invalid metadata response: {res.text}",
            is_logged=True,
            critical=False
        )

    return res_json["data"]


def map_items_to_media(data: dict) -> list[MediaContent]:
    media_content = []
    caption = data.get("caption") or ""
    author = data.get("author_username") or data.get("uploader")
    for item in data.get("items", []):
        item_type = item.get("type", "video")
        path_str = item.get("path")
        if not path_str:
            continue

        cover_str = item.get("cover") or item.get("thumbnail") or data.get("thumbnail")
        cover_path = Path(cover_str) if cover_str and Path(cover_str).exists() else None

        media_content.append(
            MediaContent(
                type=MediaType.AUDIO if item_type == "audio" else MediaType.VIDEO,
                path=Path(path_str),
                title=caption,
                performer=author,
                width=item.get("width"),
                height=item.get("height"),
                duration=item.get("duration"),
                cover=cover_path
            )
        )
    return media_content


async def download_youtube_full(
    http_client: httpx.AsyncClient,
    url: str,
    target_height: int,
    is_audio_only: bool,
    sponsor: bool
) -> list[MediaContent]:
    payload: dict[str, Any] = {
        "url": url,
        "sponsor": sponsor
    }
    if target_height > 0:
        payload["target_height"] = target_height
    if is_audio_only:
        payload["is_audio_only"] = True

    try:
        res = await http_client.post(
            "http://media-core:9546/download/youtube",
            json=payload,
            timeout=300.0
        )
    except Exception as e:
        logger.error(f"Failed to download full YouTube media: {e}")
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            url=url,
            service=Services.YOUTUBE,
            message=f"Failed to connect to media-core: {e}",
            is_logged=True,
            critical=True
        )

    handle_youtube_api_errors(res, url)

    res_json = res.json()
    if res_json.get("status") != "success" or "data" not in res_json:
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            url=url,
            service=Services.YOUTUBE,
            message=f"Invalid download response: {res.text}",
            is_logged=True,
            critical=True
        )

    return map_items_to_media(res_json["data"])


async def download_youtube_clip(
    http_client: httpx.AsyncClient,
    url: str,
    target_height: int,
    is_audio_only: bool,
    start_time: str,
    end_time: str,
    sponsor: bool
) -> list[MediaContent]:
    payload: dict[str, Any] = {
        "url": url,
        "sponsor": sponsor
    }
    if target_height > 0:
        payload["target_height"] = target_height
    if is_audio_only:
        payload["is_audio_only"] = True
    if start_time:
        payload["start_time"] = start_time
    if end_time:
        payload["end_time"] = end_time

    try:
        res = await http_client.post(
            "http://media-core:9546/download/youtube",
            json=payload,
            timeout=300.0
        )
    except Exception as e:
        logger.error(f"Failed to download YouTube clip: {e}")
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            url=url,
            service=Services.YOUTUBE,
            message=f"Failed to connect to media-core: {e}",
            is_logged=True,
            critical=True
        )

    handle_youtube_api_errors(res, url)

    res_json = res.json()
    if res_json.get("status") != "success" or "data" not in res_json:
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            url=url,
            service=Services.YOUTUBE,
            message=f"Invalid download response: {res.text}",
            is_logged=True,
            critical=True
        )

    return map_items_to_media(res_json["data"])


@youtube_router.message(F.text.regexp(YOUTUBE_REGEX), StateFilter("*"))
async def youtube_handler(
    message: Message,
    state: FSMContext,
    dialog_manager: DialogManager,
    i18n: TranslatorRunner,
    db_session: AsyncSession,
    http_client: httpx.AsyncClient
):
    from aiogram_dialog import StartMode
    stack = dialog_manager.current_stack()
    if stack and stack.last_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=stack.last_message_id)
        except Exception:
            pass

    url = message.text
    chat_id = message.chat.id

    async with ChatActionSender.choose_sticker(bot=message.bot, chat_id=chat_id):
        process_message = await message.reply(i18n.get('processing'))

        try:
            metadata = await get_youtube_metadata(http_client, url)
        except Exception as e:
            await process_message.delete()
            raise e

    from utils.url_cache import store_url, url_hash
    store_url(url)
    h = url_hash(url)

    from storage.db.crud import get_user_settings
    user_id = message.from_user.id
    user = await get_user(db_session, user_id)
    is_premium = user.is_premium if user else False

    settings = await get_user_settings(db_session, user_id)
    ui_mode = "simple"
    if settings and hasattr(settings.services.youtube, "ui_mode"):
        ui_mode = settings.services.youtube.ui_mode
    elif settings and hasattr(settings.services.youtube, "simple"):
        ui_mode = "simple" if settings.services.youtube.simple else "advanced"

    target_state = YouTubeDialogStates.simple
    if ui_mode == "balance":
        target_state = YouTubeDialogStates.balance
    elif ui_mode == "advanced":
        target_state = YouTubeDialogStates.advanced

    await process_message.delete()

    await dialog_manager.start(
        target_state,
        data={
            "url": url,
            "url_hash": h,
            "title": metadata.get("title"),
            "thumbnail": metadata.get("thumbnail"),
            "uploader": metadata.get("uploader"),
            "uploader_url": metadata.get("uploader_url") or metadata.get("channel_url"),
            "duration": metadata.get("duration"),
            "options": metadata.get("options", []),
            "audio_only": metadata.get("audio_only"),
            "is_premium": is_premium
        },
        mode=StartMode.RESET_STACK
    )


async def send_mode_selection_menu(
    message_or_query: Message | CallbackQuery,
    state: FSMContext,
    i18n: TranslatorRunner,
    db_session: AsyncSession
):
    data = await state.get_data()
    user_id = message_or_query.from_user.id

    user = await get_user(db_session, user_id)
    is_premium = user.is_premium if user else False

    from storage.db.crud import get_user_settings
    settings = await get_user_settings(db_session, user_id)
    is_simple = settings.services.youtube.simple if settings else True

    trim_active = data.get("trim", False)
    current_format = data.get("format", "video")

    markup = InlineKeyboardBuilder()

    if is_simple:
        markup.button(
            text=i18n.get("yt-btn-video"),
            callback_data=YoutubeMenuCallback(action="download_simple", format="video", trim=False).pack()
        )
        markup.button(
            text=i18n.get("yt-btn-audio"),
            callback_data=YoutubeMenuCallback(action="download_simple", format="audio", trim=False).pack()
        )
        markup.button(
            text=i18n.get("yt-btn-cancel"),
            callback_data=YoutubeMenuCallback(action="cancel", format="video", trim=False).pack()
        )
        markup.adjust(2, 1)
    else:
        options = data.get("options", [])
        audio_only = data.get("audio_only", {})

        # Video resolutions buttons
        for opt in options:
            label = opt.get("label", "")
            height = opt.get("target_height", 0)
            size_mb = opt.get("size_mb", 0)

            if size_mb > 100 and not is_premium and not trim_active:
                btn_text = f"★ {label} (~{size_mb:.1f} MB)"
            else:
                btn_text = f"{label} (~{size_mb:.1f} MB)"

            markup.button(
                text=btn_text,
                callback_data=YoutubeQualityCallback(height=height, size_mb=size_mb, label=label).pack()
            )

        # Audio button
        if audio_only:
            a_label = audio_only.get("label", "Audio")
            a_height = audio_only.get("target_height", 0)
            a_size = audio_only.get("size_mb", 0)
            markup.button(
                text=f"🎵 {a_label} (~{a_size:.1f} MB)",
                callback_data=YoutubeQualityCallback(height=a_height, size_mb=a_size, label=a_label).pack()
            )

        markup.adjust(2)

        # Trim Button
        if is_premium:
            if trim_active:
                markup.row(
                    InlineKeyboardButton(
                        text=i18n.get("yt-btn-trim-active"),
                        callback_data=YoutubeMenuCallback(action="toggle_trim", format=current_format, trim=False).pack()
                    )
                )
            else:
                markup.row(
                    InlineKeyboardButton(
                        text=i18n.get("yt-btn-trim"),
                        callback_data=YoutubeMenuCallback(action="toggle_trim", format=current_format, trim=True).pack()
                    )
                )
        else:
            markup.row(
                InlineKeyboardButton(
                    text=i18n.get("yt-btn-trim-locked"),
                    callback_data=YoutubeMenuCallback(action="toggle_trim", format=current_format, trim=True).pack()
                )
            )

        # Cancel Button
        markup.row(
            InlineKeyboardButton(
                text=i18n.get("yt-btn-cancel"),
                callback_data=YoutubeMenuCallback(action="cancel", format=current_format, trim=trim_active).pack()
            )
        )

    caption = f"<b>{data.get('title')}</b>\n\n"
    if data.get("uploader"):
        if data.get("uploader_url"):
            caption += f"<b>Channel:</b> <a href='{data.get('uploader_url')}'>{data.get('uploader')}</a>\n"
        else:
            caption += f"<b>Channel:</b> {data.get('uploader')}\n"

    duration = data.get("duration")
    if duration:
        caption += f"<b>Duration:</b> {format_duration(duration)}\n"

    caption += f"\n{data.get('description') or ''}"

    reply_markup = markup.as_markup()
    thumbnail = data.get("thumbnail")

    import os
    if isinstance(message_or_query, Message):
        if thumbnail and os.path.exists(thumbnail):
            await message_or_query.reply_photo(
                photo=FSInputFile(thumbnail),
                caption=truncate_string(caption, 1024),
                reply_markup=reply_markup
            )
        else:
            await message_or_query.reply(
                truncate_string(caption, 1024),
                reply_markup=reply_markup
            )
    else:
        try:
            await message_or_query.message.edit_reply_markup(reply_markup=reply_markup)
        except Exception:
            pass


@youtube_router.callback_query(YoutubeMenuCallback.filter(), StateFilter(YouTubeStates.choosing_mode))
async def menu_callback_handler(
    callback_query: CallbackQuery,
    callback_data: YoutubeMenuCallback,
    state: FSMContext,
    i18n: TranslatorRunner,
    db_session: AsyncSession
):
    user_id = callback_query.from_user.id
    message = callback_query.message

    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id != user_id:
            await callback_query.answer(i18n.get("menu-not-yours"), show_alert=True)
            return

    action = callback_data.action

    if action == "cancel":
        await state.clear()
        await message.delete()
        await callback_query.answer(i18n.get("action-cancelled"))
        return

    user = await get_user(db_session, user_id)
    is_premium = user.is_premium if user else False

    if action == "toggle_trim":
        if callback_data.trim and not is_premium:
            await callback_query.answer(i18n.get("yt-trim-sponsor-only"), show_alert=True)
            return

        await state.update_data(trim=callback_data.trim)
        await send_mode_selection_menu(callback_query, state, i18n, db_session)
        await callback_query.answer()

    elif action == "download_simple":
        is_audio = callback_data.format == "audio"
        data = await state.get_data()
        url = data["url"]

        await state.clear()
        await message.delete()

        asyncio.create_task(process_youtube_download(
            message=message.reply_to_message or message,
            url=url,
            target_height=0,
            is_audio_only=is_audio,
            user_id=user_id,
            db_session=db_session,
            i18n=i18n
        ))
        await callback_query.answer(i18n.get('starting-download'))


@youtube_router.callback_query(YoutubeQualityCallback.filter(), StateFilter(YouTubeStates.choosing_mode))
async def quality_callback_handler(
    callback_query: CallbackQuery,
    callback_data: YoutubeQualityCallback,
    state: FSMContext,
    i18n: TranslatorRunner,
    db_session: AsyncSession
):
    user_id = callback_query.from_user.id
    message = callback_query.message

    if message.reply_to_message and message.reply_to_message.from_user:
        if message.reply_to_message.from_user.id != user_id:
            await callback_query.answer(i18n.get("menu-not-yours"), show_alert=True)
            return

    data = await state.get_data()
    trim = data.get("trim", False)
    url = data["url"]
    url_hash = data["url_hash"]

    is_audio = callback_data.height == 0
    await state.update_data(
        target_height=callback_data.height,
        size_mb=callback_data.size_mb,
        label=callback_data.label,
        format="audio" if is_audio else "video"
    )

    if trim:
        await state.set_state(YouTubeStates.entering_time_range)
        await message.edit_reply_markup(reply_markup=None)
        await message.answer(i18n.get("yt-trim-ask-range"))
        await callback_query.answer()
    else:
        user = await get_user(db_session, user_id)
        is_premium = user.is_premium if user else False

        if callback_data.size_mb > 100 and not is_premium:
            from modules.payment.video import PaymentService
            payload = f"yt_{url_hash}_{callback_data.height}_{1 if is_audio else 0}"

            invoice_params = await PaymentService.create_single_download_invoice(
                chat_id=message.chat.id,
                payload=payload,
                provider_token=""
            )
            invoice_params.pop('chat_id', None)

            await state.clear()
            await message.delete()
            await message.answer_invoice(**invoice_params)
            await callback_query.answer()
            return

        await state.clear()
        await message.delete()

        asyncio.create_task(process_youtube_download(
            message=message.reply_to_message or message,
            url=url,
            target_height=callback_data.height,
            is_audio_only=is_audio,
            user_id=user_id,
            db_session=db_session,
            i18n=i18n
        ))
        await callback_query.answer(i18n.get('starting-download'))


@youtube_router.message(YouTubeStates.entering_time_range)
async def time_range_message_handler(
    message: Message,
    state: FSMContext,
    i18n: TranslatorRunner,
    db_session: AsyncSession
):
    if not message.text:
        return

    data = await state.get_data()
    url = data["url"]
    duration = data.get("duration", 0)
    target_height = data.get("target_height", 0)
    is_audio_only = data.get("format") == "audio"
    user_id = message.from_user.id

    parsed = parse_time_range(message.text)
    if not parsed:
        await message.reply(i18n.get("yt-trim-invalid-range"))
        return

    start_formatted, end_formatted, start_seconds, end_seconds = parsed

    if duration > 0:
        dur_str = format_duration(duration)
        if start_seconds >= duration:
            await message.reply(i18n.get("yt-trim-out-of-bounds", duration=dur_str))
            return
        if end_seconds != -1 and end_seconds > duration:
            await message.reply(i18n.get("yt-trim-out-of-bounds", duration=dur_str))
            return

    await state.clear()

    process_message = await message.reply(i18n.get("yt-trim-processing"))

    asyncio.create_task(process_clip_download(
        message=message,
        process_message=process_message,
        url=url,
        target_height=target_height,
        is_audio_only=is_audio_only,
        start_time=start_formatted,
        end_time=end_formatted,
        user_id=user_id,
        db_session=db_session,
        i18n=i18n
    ))


async def process_youtube_download(
    message: Message,
    url: str,
    target_height: int,
    is_audio_only: bool,
    user_id: int,
    db_session: AsyncSession,
    http_client: httpx.AsyncClient = None,
    payment_charge_id: str = None,
    i18n: TranslatorRunner = None
):
    send_manager = MediaSender()

    from storage.db import database_manager
    async with database_manager.async_session() as session:
        db_session = session
        try:
            if not i18n:
                try:
                    from core.loader import dp
                    hub = dp.workflow_data.get("_translator_hub")
                    if hub:
                        from storage.db.crud import get_user_settings
                        settings = await get_user_settings(db_session, user_id)
                        lang = settings.profile.language if settings else "en"
                        i18n = hub.get_translator_by_locale(lang)
                except Exception:
                    pass

            user = await get_user(db_session, user_id)
            is_premium = (user.is_premium if user else False) or (payment_charge_id is not None)

            cache_key = get_cache_key(url, target_height, is_audio_only)
            cached = await cache_check(db_session, cache_key)
            if cached:
                await send_manager.send(message, cached, service="youtube", db_session=db_session)
                await db_session.commit()
                return

            client = http_client or httpx.AsyncClient()
            try:
                async with ChatActionSender.record_video_note(bot=message.bot, chat_id=message.chat.id):
                    media_content = await task_manager.run_download(
                        user_id=user_id,
                        url=url,
                        coro=download_youtube_full(
                            http_client=client,
                            url=url,
                            target_height=target_height,
                            is_audio_only=is_audio_only,
                            sponsor=is_premium
                        )
                    )

                if media_content:
                    await send_manager.send(
                        message=message,
                        content=media_content,
                        service="youtube",
                        cache_key=cache_key,
                        db_session=db_session
                    )

                await db_session.commit()

            except Exception as e:
                await db_session.rollback()
                bot_err = e if isinstance(e, BotError) else BotError(code=ErrorCode.INTERNAL_ERROR, message=str(e), service=Services.YOUTUBE, is_logged=True)
                await log_download_event(db_session, user_id, Services.YOUTUBE, 'failed_download', error_code=bot_err.code)

                if payment_charge_id and message.bot:
                    try:
                        await message.bot.refund_star_payment(user_id, telegram_payment_charge_id=payment_charge_id)
                        from storage.db.crud import update_payment_status
                        await update_payment_status(db_session, payment_charge_id, "refunded")
                        refund_msg = i18n.get("download-failed-refund") if i18n else "❌ Download failed. Your payment has been refunded."
                        await message.answer(refund_msg)
                    except Exception as refund_error:
                        logger.error(f"Failed to refund payment: {refund_error}")
                else:
                    if bot_err.send_user_message and message.bot:
                        from utils.error_messages import get_i18n_error_message
                        msg_text = get_i18n_error_message(bot_err.code, i18n) if i18n else None
                        if not msg_text:
                            msg_text = i18n.get("error-internal") if i18n else "❌ An error occurred during download."
                        try:
                            await message.answer(msg_text)
                        except Exception as msg_err:
                            logger.error(f"Failed to send error message: {msg_err}")

                await db_session.commit()

                if bot_err.critical and message.bot:
                    from core.config import Config
                    cfg = Config()
                    if cfg.ADMIN_ID:
                        try:
                            await message.bot.send_message(
                                cfg.ADMIN_ID,
                                f"Sorry, there was an error:\nService: YouTube\n{url}\n\n<pre>{bot_err.message}</pre>",
                                parse_mode="HTML"
                            )
                        except Exception as admin_err:
                            logger.error(f"Failed to notify admin: {admin_err}")

                logger.error(f"YouTube download error: {bot_err.message}")
            finally:
                if http_client is None:
                    await client.aclose()
        except Exception as outer_e:
            await db_session.rollback()
            logger.error(f"Outer exception in process_youtube_download: {outer_e}")


async def process_clip_download(
    message: Message,
    process_message: Message,
    url: str,
    target_height: int,
    is_audio_only: bool,
    start_time: str,
    end_time: str,
    user_id: int,
    db_session: AsyncSession,
    http_client: httpx.AsyncClient = None,
    i18n: TranslatorRunner = None
):
    send_manager = MediaSender()

    from storage.db import database_manager
    async with database_manager.async_session() as session:
        db_session = session
        try:
            if not i18n:
                try:
                    from core.loader import dp
                    hub = dp.workflow_data.get("_translator_hub")
                    if hub:
                        from storage.db.crud import get_user_settings
                        settings = await get_user_settings(db_session, user_id)
                        lang = settings.profile.language if settings else "en"
                        i18n = hub.get_translator_by_locale(lang)
                except Exception:
                    pass

            user = await get_user(db_session, user_id)
            is_premium = user.is_premium if user else False

            client = http_client or httpx.AsyncClient()
            try:
                async with ChatActionSender.record_video_note(bot=message.bot, chat_id=message.chat.id):
                    media_content = await task_manager.run_download(
                        user_id=user_id,
                        url=url,
                        coro=download_youtube_clip(
                            http_client=client,
                            url=url,
                            target_height=target_height,
                            is_audio_only=is_audio_only,
                            start_time=start_time,
                            end_time=end_time,
                            sponsor=is_premium
                        )
                    )

                try:
                    await process_message.delete()
                except Exception:
                    pass

                if media_content:
                    await send_manager.send(
                        message=message,
                        content=media_content,
                        service="youtube",
                        cache_key=None,
                        db_session=db_session
                    )

                await db_session.commit()

            except Exception as e:
                await db_session.rollback()
                try:
                    await process_message.delete()
                except Exception:
                    pass

                bot_err = e if isinstance(e, BotError) else BotError(code=ErrorCode.INTERNAL_ERROR, message=str(e), service=Services.YOUTUBE, is_logged=True)
                await log_download_event(db_session, user_id, Services.YOUTUBE, 'failed_download', error_code=bot_err.code)

                if bot_err.send_user_message and message.bot:
                    from utils.error_messages import get_i18n_error_message
                    msg_text = get_i18n_error_message(bot_err.code, i18n) if i18n else None
                    if not msg_text:
                        msg_text = i18n.get("error-internal") if i18n else "❌ An error occurred during download."
                    try:
                        await message.answer(msg_text)
                    except Exception as msg_err:
                        logger.error(f"Failed to send error message: {msg_err}")

                await db_session.commit()

                if bot_err.critical and message.bot:
                    from core.config import Config
                    cfg = Config()
                    if cfg.ADMIN_ID:
                        try:
                            await message.bot.send_message(
                                cfg.ADMIN_ID,
                                f"Sorry, there was an error:\nService: YouTube (Clip)\n{url}\n\n<pre>{bot_err.message}</pre>",
                                parse_mode="HTML"
                            )
                        except Exception as admin_err:
                            logger.error(f"Failed to notify admin: {admin_err}")

                logger.error(f"YouTube clip download error: {bot_err.message}")
            finally:
                if http_client is None:
                    await client.aclose()
        except Exception as outer_e:
            await db_session.rollback()
            logger.error(f"Outer exception in process_clip_download: {outer_e}")
