import logging
import re
import httpx
import asyncio
from pathlib import Path
from typing import Any

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import StateFilter
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.service_list import Services
from senders.media_sender import MediaSender
from states.youtube import YouTubeStates
from storage.db.crud import get_user
from tasks.task_manager import task_manager
from utils import format_duration, truncate_string, escape_html, build_caption, format_author_link, safe_truncate_html, extract_url
from utils.statistics_helper import log_download_event
from storage.cache.redis_client import cache_set, cache_get, cache_delete
from middlewares.button_owner import register_message_owner

from .keyboards import (
    YouTubeActionCallback,
    YouTubeFormatCallback,
    get_reliable_thumbnail,
    build_yt_header,
    build_simple_keyboard,
    build_balance_keyboard,
    build_advanced_keyboard,
    build_trim_input_keyboard,
)
from .utils import get_cache_key, cache_check, parse_time_range

youtube_router = Router(name="youtube")
logger = logging.getLogger(__name__)

YOUTUBE_REGEX = r"https?://(?:www\.)?(?:m\.)?(?:youtu\.be/|youtube\.com/(?:shorts/|watch\?v=))([\w-]+)"

_background_tasks: set[asyncio.Task] = set()


def run_background_task(coro) -> asyncio.Task:
    t = asyncio.create_task(coro)
    _background_tasks.add(t)
    t.add_done_callback(_background_tasks.discard)
    return t


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

    is_error = res.status_code >= 400
    if res.status_code == 451 or (is_error and ("geo" in err_msg_lower or "country" in err_msg_lower or "region" in err_msg_lower or "geoblocked" in err_msg_lower)):
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


def map_items_to_media(data: dict, extra_metadata: dict | None = None) -> list[MediaContent]:
    extra_metadata = extra_metadata or {}
    media_content = []
    plain_title = str(data.get("title") or extra_metadata.get("title") or "").strip()

    author_obj = data.get("author") if isinstance(data.get("author"), dict) else {}
    author = (
        author_obj.get("username")
        or author_obj.get("name")
        or data.get("author_username")
        or data.get("uploader")
        or extra_metadata.get("uploader")
        or ""
    )
    author_url = (
        author_obj.get("url")
        or data.get("uploader_url")
        or data.get("channel_url")
        or extra_metadata.get("uploader_url")
        or extra_metadata.get("channel_url")
        or ""
    )
    if not author_url and author and author.startswith("@"):
        author_url = f"https://www.youtube.com/{author}"

    author_link = format_author_link(author, author_url, icon="👤")

    title_esc = escape_html(plain_title)
    if author_link and title_esc:
        header = f"{author_link}\n<b>{title_esc}</b>"
    elif author_link:
        header = author_link
    else:
        header = f"<b>{title_esc}</b>" if title_esc else ""

    raw_description = str(
        extra_metadata.get("description")
        or data.get("description")
        or data.get("caption")
        or ""
    ).strip()

    if raw_description.lower().strip() == plain_title.lower().strip():
        raw_description = ""

    desc_esc = escape_html(raw_description)

    caption = build_caption(header=header, description=desc_esc)

    for item in data.get("items", []):
        item_type = item.get("type", "video")
        path_str = item.get("path")
        if not path_str:
            continue

        cover_str = (
            item.get("cover_path")
            or item.get("cover")
            or item.get("thumbnail")
            or data.get("thumbnail")
            or data.get("cover_path")
            or extra_metadata.get("thumbnail")
        )
        cover_path = Path(cover_str) if cover_str and Path(cover_str).exists() else None

        media_content.append(
            MediaContent(
                type=MediaType.AUDIO if item_type == "audio" else MediaType.VIDEO,
                path=Path(path_str),
                title=plain_title if item_type == "audio" else caption,
                description=caption,
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
    sponsor: bool,
    user_id: int,
    is_topich: bool = False,
    extra_metadata: dict | None = None
) -> list[MediaContent]:
    yt_opts: dict[str, Any] = {}
    if is_topich:
        yt_opts["topich"] = True
    else:
        if target_height > 0:
            yt_opts["target_height"] = target_height
        if is_audio_only:
            yt_opts["is_audio_only"] = True

    payload: dict[str, Any] = {
        "user_id": user_id,
        "url": url,
        "sponsor": sponsor,
        "nsfw": False,
    }
    if yt_opts:
        payload["yt_opts"] = yt_opts

    data = await task_manager.run_media_download(
        user_id=user_id,
        url=url,
        service=Services.YOUTUBE,
        payload=payload,
        http_client=http_client,
    )

    items = map_items_to_media(data, extra_metadata=extra_metadata)
    if is_topich:
        for item in items:
            item.as_document = True
    return items


async def download_youtube_clip(
    http_client: httpx.AsyncClient,
    url: str,
    target_height: int,
    is_audio_only: bool,
    start_time: str,
    end_time: str,
    sponsor: bool,
    user_id: int,
    extra_metadata: dict | None = None
) -> list[MediaContent]:
    yt_opts: dict[str, Any] = {}
    if target_height > 0:
        yt_opts["target_height"] = target_height
    if is_audio_only:
        yt_opts["is_audio_only"] = True
    if start_time:
        yt_opts["start_time"] = start_time
    if end_time:
        yt_opts["end_time"] = end_time

    payload: dict[str, Any] = {
        "user_id": user_id,
        "url": url,
        "sponsor": sponsor,
        "nsfw": False,
        "yt_opts": yt_opts
    }

    data = await task_manager.run_media_download(
        user_id=user_id,
        url=url,
        service=Services.YOUTUBE,
        payload=payload,
        http_client=http_client,
    )

    return map_items_to_media(data, extra_metadata=extra_metadata)


async def safe_edit_markup(message: Message, reply_markup: InlineKeyboardMarkup) -> None:
    try:
        await message.edit_reply_markup(reply_markup=reply_markup)
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            logger.warning("Failed to edit reply markup: %s", e)
    except Exception as e:
        logger.warning("Failed to edit reply markup: %s", e)


async def trigger_download_native(
    callback: CallbackQuery,
    meta_data: dict[str, Any],
    height: int,
    is_audio: bool,
    size_mb: float = 0.0,
    is_topich: bool = False,
    i18n: TranslatorRunner | None = None,
    db_session: AsyncSession | None = None,
) -> None:
    user_id = callback.from_user.id
    target_message = callback.message.reply_to_message or callback.message
    url = meta_data["url"]
    url_hash = meta_data["url_hash"]
    is_premium = meta_data.get("is_premium", False)

    origin_msg_id = meta_data.get("origin_message_id")
    if origin_msg_id and target_message:
        user_message = target_message.model_copy(update={"message_id": origin_msg_id})
        if getattr(target_message, "bot", None):
            user_message._bot = target_message.bot
    else:
        user_message = target_message

    if not getattr(user_message, "bot", None):
        from core.loader import bot as default_bot
        if default_bot:
            user_message._bot = default_bot

    if size_mb > 100 and not is_premium:
        from modules.payment.video import PaymentService
        payload = f"yt_{url_hash}_{height}_{1 if is_audio else 0}"
        invoice_params = await PaymentService.create_single_download_invoice(
            chat_id=user_message.chat.id,
            payload=payload,
            provider_token=""
        )
        invoice_params.pop('chat_id', None)
        await user_message.answer_invoice(**invoice_params)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.answer()
        return

    try:
        await callback.message.delete()
    except Exception:
        pass

    from tasks.task_manager import task_manager
    if task_manager.is_user_busy(user_id):
        try:
            from utils.ephemeral import notify_already_downloading_if_ephemeral
            await notify_already_downloading_if_ephemeral(user_message, user_id, i18n)
        except Exception as e:
            logger.debug(f"Failed to send busy notification: {e}")

    extra_metadata = {
        "uploader": meta_data.get("uploader"),
        "uploader_url": meta_data.get("uploader_url") or meta_data.get("channel_url"),
        "channel_url": meta_data.get("channel_url"),
        "description": meta_data.get("description"),
        "thumbnail": meta_data.get("thumbnail"),
        "title": meta_data.get("title"),
    }

    run_background_task(process_youtube_download(
        message=user_message,
        url=url,
        target_height=height,
        is_audio_only=is_audio,
        user_id=user_id,
        db_session=db_session,
        i18n=i18n,
        is_topich=is_topich,
        extra_metadata=extra_metadata
    ))
    toast = i18n.get('starting-download') if i18n else "Начинаем загрузку..."
    await callback.answer(toast)


@youtube_router.message(F.text.regexp(YOUTUBE_REGEX), StateFilter("*"))
async def youtube_handler(
    message: Message,
    state: FSMContext,
    i18n: TranslatorRunner,
    db_session: AsyncSession,
    http_client: httpx.AsyncClient
):
    if not message.text or not message.from_user:
        return

    url = extract_url(YOUTUBE_REGEX, message.text)
    if not url:
        return
    chat_id = message.chat.id

    from utils.effects import react_safe
    await react_safe(message, "👀")

    from tasks.task_manager import task_manager
    if task_manager.is_user_busy(message.from_user.id):
        from utils.ephemeral import notify_already_downloading_if_ephemeral
        await notify_already_downloading_if_ephemeral(message, message.from_user.id, i18n)

    async with ChatActionSender.choose_sticker(bot=message.bot, chat_id=chat_id):
        metadata = await get_youtube_metadata(http_client, url)

    from utils.url_cache import store_url, url_hash
    await store_url(url)
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

    author_data = metadata.get("author") if isinstance(metadata.get("author"), dict) else {}
    uploader = author_data.get("username") or author_data.get("name") or metadata.get("uploader") or metadata.get("author_username")
    uploader_url = author_data.get("url") or metadata.get("uploader_url") or metadata.get("channel_url")
    thumbnail = metadata.get("cover_path") or metadata.get("thumbnail") or metadata.get("cover")

    options = metadata.get("options", [])
    audio_only = metadata.get("audio_only", {})
    default_selected = ""
    if options:
        highest = max(options, key=lambda x: x.get("target_height", 0))
        default_selected = f"v_{highest.get('target_height', 0)}"
    elif audio_only:
        default_selected = "audio"

    meta_data = {
        "url": url,
        "url_hash": h,
        "title": metadata.get("title") or metadata.get("caption"),
        "thumbnail": thumbnail,
        "uploader": uploader,
        "uploader_url": uploader_url,
        "channel_url": metadata.get("channel_url"),
        "description": metadata.get("description") or metadata.get("caption", ""),
        "duration": metadata.get("duration"),
        "options": options,
        "audio_only": audio_only,
        "is_premium": is_premium,
        "origin_message_id": message.message_id,
        "selected_format": default_selected,
        "trim_active": False,
        "ui_mode": ui_mode,
    }
    await cache_set(f"yt_meta:{h}", meta_data, ttl=3600)

    header = build_yt_header(meta_data, i18n)

    if ui_mode == "balance":
        keyboard = build_balance_keyboard(user_id, h, meta_data, i18n)
    elif ui_mode == "advanced":
        keyboard = build_advanced_keyboard(user_id, h, meta_data, i18n)
    else:
        keyboard = build_simple_keyboard(user_id, h, i18n)

    reliable_thumb = get_reliable_thumbnail(url, thumbnail)
    menu_msg = None
    if reliable_thumb:
        try:
            menu_msg = await message.reply_photo(
                photo=reliable_thumb,
                caption=header,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.warning("Failed to send thumbnail photo: %s", e)

    if not menu_msg:
        menu_msg = await message.reply(
            text=header,
            reply_markup=keyboard,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )

    await register_message_owner(menu_msg, user_id)


@youtube_router.callback_query(YouTubeActionCallback.filter())
async def on_yt_action_callback(
    callback: CallbackQuery,
    callback_data: YouTubeActionCallback,
    state: FSMContext,
    i18n: TranslatorRunner,
    db_session: AsyncSession,
):
    if callback.from_user.id != callback_data.owner_id:
        not_yours = i18n.get("menu-not-yours") if i18n else "❌ Это не ваш запрос"
        await callback.answer(not_yours, show_alert=True)
        return

    h = callback_data.h
    meta_data = await cache_get(f"yt_meta:{h}")
    if not meta_data:
        expired = i18n.get("action-cancelled") if i18n else "⚠️ Запрос устарел, отправьте ссылку заново."
        await callback.answer(expired, show_alert=True)
        return

    action = callback_data.action

    if action == "cancel":
        await state.clear()
        try:
            await callback.message.delete()
        except Exception:
            pass
        canceled_text = i18n.get("action-cancelled") if i18n else "Отменено"
        await callback.answer(canceled_text)
        return

    elif action == "to_adv":
        meta_data["ui_mode"] = "advanced"
        await cache_set(f"yt_meta:{h}", meta_data, ttl=3600)
        kb = build_advanced_keyboard(callback_data.owner_id, h, meta_data, i18n)
        await safe_edit_markup(callback.message, kb)
        await callback.answer()
        return

    elif action == "to_bal":
        meta_data["ui_mode"] = "balance"
        await cache_set(f"yt_meta:{h}", meta_data, ttl=3600)
        kb = build_balance_keyboard(callback_data.owner_id, h, meta_data, i18n)
        await safe_edit_markup(callback.message, kb)
        await callback.answer()
        return

    elif action == "toggle_trim":
        if not meta_data.get("is_premium"):
            msg = i18n.get("yt-sponsor-only") if i18n else "🌟 Эта фича только для Спонсоров!"
            await callback.answer(msg, show_alert=True)
            return

        current = meta_data.get("trim_active", False)
        meta_data["trim_active"] = not current
        await cache_set(f"yt_meta:{h}", meta_data, ttl=3600)
        kb = build_advanced_keyboard(callback_data.owner_id, h, meta_data, i18n)
        await safe_edit_markup(callback.message, kb)
        await callback.answer()
        return

    elif action == "sim_vid":
        options = meta_data.get("options", [])
        highest_h = max([opt.get("target_height", 0) for opt in options], default=0) if options else 0
        matching = next((opt for opt in options if opt.get("target_height") == highest_h), {})
        size_mb = matching.get("size_mb", 0.0)
        await trigger_download_native(
            callback=callback,
            meta_data=meta_data,
            height=highest_h,
            is_audio=False,
            size_mb=size_mb,
            i18n=i18n,
            db_session=db_session,
        )
        return

    elif action == "sim_aud":
        audio_only = meta_data.get("audio_only", {})
        a_h = audio_only.get("target_height", 0) if audio_only else 0
        a_size = audio_only.get("size_mb", 0.0) if audio_only else 0.0
        await trigger_download_native(
            callback=callback,
            meta_data=meta_data,
            height=a_h,
            is_audio=True,
            size_mb=a_size,
            i18n=i18n,
            db_session=db_session,
        )
        return

    elif action == "cont":
        trim_active = meta_data.get("trim_active", False)
        selected_id = meta_data.get("selected_format", "audio")
        options = meta_data.get("options", [])
        audio_only = meta_data.get("audio_only", {})

        if selected_id == "topich":
            if not meta_data.get("is_premium"):
                msg = i18n.get("yt-sponsor-only") if i18n else "🌟 Эта фича только для Спонсоров!"
                await callback.answer(msg, show_alert=True)
                return
            is_audio = False
            height = 0
            size_mb = 0.0
            is_topich = True
        elif selected_id == "audio":
            is_audio = True
            height = audio_only.get("target_height", 0) if audio_only else 0
            size_mb = audio_only.get("size_mb", 0.0) if audio_only else 0.0
            is_topich = False
        else:
            is_audio = False
            height = int(selected_id.replace("v_", ""))
            matching = next((opt for opt in options if opt.get("target_height") == height), {})
            size_mb = matching.get("size_mb", 0.0)
            is_topich = False

        if trim_active:
            await state.set_state(YouTubeStates.entering_time_range)
            await state.set_data({
                "url": meta_data["url"],
                "duration": meta_data.get("duration", 0),
                "target_height": height,
                "format": "audio" if is_audio else "video",
                "is_audio": is_audio,
                "is_topich": is_topich,
                "uploader": meta_data.get("uploader"),
                "uploader_url": meta_data.get("uploader_url"),
                "channel_url": meta_data.get("channel_url"),
                "description": meta_data.get("description"),
                "thumbnail": meta_data.get("thumbnail"),
                "title": meta_data.get("title"),
                "menu_message_id": callback.message.message_id,
            })
            ask_text = i18n.get("yt-trim-ask-range") if i18n else "Введите интервал для обрезки в формате <b>hh:mm:ss-hh:mm:ss</b>:"
            kb = build_trim_input_keyboard(callback_data.owner_id, h, i18n)
            await callback.message.reply(ask_text, reply_markup=kb, parse_mode="HTML")
            await callback.answer()
            return
        else:
            await trigger_download_native(
                callback=callback,
                meta_data=meta_data,
                height=height,
                is_audio=is_audio,
                size_mb=size_mb,
                is_topich=is_topich,
                i18n=i18n,
                db_session=db_session,
            )
            return


@youtube_router.callback_query(YouTubeFormatCallback.filter())
async def on_yt_format_callback(
    callback: CallbackQuery,
    callback_data: YouTubeFormatCallback,
    i18n: TranslatorRunner,
    db_session: AsyncSession,
):
    if callback.from_user.id != callback_data.owner_id:
        not_yours = i18n.get("menu-not-yours") if i18n else "❌ Это не ваш запрос"
        await callback.answer(not_yours, show_alert=True)
        return

    h = callback_data.h
    meta_data = await cache_get(f"yt_meta:{h}")
    if not meta_data:
        expired = i18n.get("action-cancelled") if i18n else "⚠️ Запрос устарел, отправьте ссылку заново."
        await callback.answer(expired, show_alert=True)
        return

    item_id = callback_data.item_id
    options = meta_data.get("options", [])
    audio_only = meta_data.get("audio_only", {})

    if callback_data.mode == "bal":
        if item_id == "audio":
            a_h = audio_only.get("target_height", 0) if audio_only else 0
            a_size = audio_only.get("size_mb", 0.0) if audio_only else 0.0
            await trigger_download_native(
                callback=callback,
                meta_data=meta_data,
                height=a_h,
                is_audio=True,
                size_mb=a_size,
                i18n=i18n,
                db_session=db_session,
            )
        else:
            height = int(item_id.replace("v_", ""))
            matching = next((opt for opt in options if opt.get("target_height") == height), {})
            size_mb = matching.get("size_mb", 0.0)
            await trigger_download_native(
                callback=callback,
                meta_data=meta_data,
                height=height,
                is_audio=False,
                size_mb=size_mb,
                i18n=i18n,
                db_session=db_session,
            )
        return

    elif callback_data.mode == "adv":
        if item_id == "topich" and not meta_data.get("is_premium"):
            msg = i18n.get("yt-sponsor-only") if i18n else "🌟 Эта фича только для Спонсоров!"
            await callback.answer(msg, show_alert=True)
            return

        meta_data["selected_format"] = item_id
        await cache_set(f"yt_meta:{h}", meta_data, ttl=3600)
        kb = build_advanced_keyboard(callback_data.owner_id, h, meta_data, i18n)
        await safe_edit_markup(callback.message, kb)
        await callback.answer()
        return


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
    url = data.get("url")
    if not url:
        await state.clear()
        return

    duration = data.get("duration", 0)
    dur_str = format_duration(duration) if duration else ""

    parsed = parse_time_range(message.text)
    if not parsed:
        await message.reply(i18n.get("yt-trim-invalid-format"))
        return

    start_formatted, end_formatted, start_seconds, end_seconds = parsed

    if duration > 0:
        if start_seconds >= duration:
            await message.reply(i18n.get("yt-trim-out-of-bounds", duration=dur_str))
            return
        if end_seconds != -1 and end_seconds > duration:
            await message.reply(i18n.get("yt-trim-out-of-bounds", duration=dur_str))
            return

    target_height = data.get("target_height", 0)
    is_audio_only = data.get("is_audio", False)
    is_topich = data.get("is_topich", False)
    user_id = message.from_user.id

    extra_metadata = {
        "uploader": data.get("uploader"),
        "uploader_url": data.get("uploader_url") or data.get("channel_url"),
        "channel_url": data.get("channel_url"),
        "description": data.get("description"),
        "thumbnail": data.get("thumbnail"),
        "title": data.get("title"),
    }

    menu_message_id = data.get("menu_message_id")
    if menu_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=menu_message_id)
        except Exception:
            pass

    await state.clear()

    process_message = await message.reply(i18n.get("yt-trim-processing"))

    run_background_task(process_clip_download(
        message=message,
        process_message=process_message,
        url=url,
        target_height=target_height,
        is_audio_only=is_audio_only,
        start_time=start_formatted,
        end_time=end_formatted,
        user_id=user_id,
        db_session=db_session,
        i18n=i18n,
        extra_metadata=extra_metadata
    ))


async def process_youtube_download(
    message: Message,
    url: str,
    target_height: int,
    is_audio_only: bool,
    user_id: int,
    db_session: AsyncSession,
    i18n: TranslatorRunner | None = None,
    payment_charge_id: str | None = None,
    http_client: httpx.AsyncClient | None = None,
    is_topich: bool = False,
    extra_metadata: dict | None = None
):
    if not getattr(message, "bot", None):
        from core.loader import bot as default_bot
        if default_bot:
            message._bot = default_bot

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

            _action = ChatActionSender.upload_voice if is_audio_only else ChatActionSender.upload_video

            cache_key = get_cache_key(url, target_height, is_audio_only, is_topich)
            cached = await cache_check(db_session, cache_key)
            if cached:
                if message.bot:
                    async with _action(bot=message.bot, chat_id=message.chat.id):
                        await send_manager.send(message, cached, service="youtube", db_session=db_session)
                else:
                    await send_manager.send(message, cached, service="youtube", db_session=db_session)
                await db_session.commit()
                return

            await db_session.commit()

            client = http_client or httpx.AsyncClient()
            try:
                if message.bot:
                    async with _action(bot=message.bot, chat_id=message.chat.id):
                        media_content = await download_youtube_full(
                            http_client=client,
                            url=url,
                            target_height=target_height,
                            is_audio_only=is_audio_only,
                            sponsor=is_premium,
                            user_id=user_id,
                            is_topich=is_topich,
                            extra_metadata=extra_metadata
                        )
                else:
                    media_content = await download_youtube_full(
                        http_client=client,
                        url=url,
                        target_height=target_height,
                        is_audio_only=is_audio_only,
                        sponsor=is_premium,
                        user_id=user_id,
                        is_topich=is_topich,
                        extra_metadata=extra_metadata
                    )

                if media_content:
                    if message.bot:
                        async with _action(bot=message.bot, chat_id=message.chat.id):
                            await send_manager.send(
                                message=message,
                                content=media_content,
                                service="youtube",
                                cache_key=cache_key,
                                db_session=db_session,
                            )
                    else:
                        await send_manager.send(
                            message=message,
                            content=media_content,
                            service="youtube",
                            cache_key=cache_key,
                            db_session=db_session,
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
                        from utils.error_messages import get_error_keyboard
                        from middlewares.button_owner import register_message_owner
                        sent = await message.answer(refund_msg, reply_markup=get_error_keyboard(i18n, owner_id=user_id))
                        if sent:
                            await register_message_owner(sent, user_id)
                    except Exception as refund_error:
                        logger.error(f"Failed to refund payment: {refund_error}")
                else:
                    if bot_err.send_user_message and message.bot:
                        from utils.error_messages import get_i18n_error_message, get_error_keyboard
                        from middlewares.button_owner import register_message_owner
                        msg_text = get_i18n_error_message(bot_err.code, i18n) if i18n else None
                        if not msg_text:
                            msg_text = i18n.get("error-internal") if i18n else "❌ An error occurred during download."
                        try:
                            sent = await message.answer(msg_text, reply_markup=get_error_keyboard(i18n, owner_id=user_id))
                            if sent:
                                await register_message_owner(sent, user_id)
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
    i18n: TranslatorRunner = None,
    extra_metadata: dict | None = None
):
    if not getattr(message, "bot", None):
        from core.loader import bot as default_bot
        if default_bot:
            message._bot = default_bot

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

            await db_session.commit()

            _action = ChatActionSender.upload_voice if is_audio_only else ChatActionSender.upload_video

            client = http_client or httpx.AsyncClient()
            try:
                if message.bot:
                    async with _action(bot=message.bot, chat_id=message.chat.id):
                        media_content = await download_youtube_clip(
                            http_client=client,
                            url=url,
                            target_height=target_height,
                            is_audio_only=is_audio_only,
                            start_time=start_time,
                            end_time=end_time,
                            sponsor=is_premium,
                            user_id=user_id,
                            extra_metadata=extra_metadata
                        )
                else:
                    media_content = await download_youtube_clip(
                        http_client=client,
                        url=url,
                        target_height=target_height,
                        is_audio_only=is_audio_only,
                        start_time=start_time,
                        end_time=end_time,
                        sponsor=is_premium,
                        user_id=user_id,
                        extra_metadata=extra_metadata
                    )

                try:
                    await process_message.delete()
                except Exception:
                    pass

                if media_content:
                    if message.bot:
                        async with _action(bot=message.bot, chat_id=message.chat.id):
                            await send_manager.send(
                                message=message,
                                content=media_content,
                                service="youtube",
                                cache_key=None,
                                db_session=db_session,
                            )
                    else:
                        await send_manager.send(
                            message=message,
                            content=media_content,
                            service="youtube",
                            cache_key=None,
                            db_session=db_session,
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
                    from utils.error_messages import get_i18n_error_message, get_error_keyboard
                    from middlewares.button_owner import register_message_owner
                    msg_text = get_i18n_error_message(bot_err.code, i18n) if i18n else None
                    if not msg_text:
                        msg_text = i18n.get("error-internal") if i18n else "❌ An error occurred during download."
                    try:
                        sent = await message.answer(msg_text, reply_markup=get_error_keyboard(i18n, owner_id=user_id))
                        if sent:
                            await register_message_owner(sent, user_id)
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
