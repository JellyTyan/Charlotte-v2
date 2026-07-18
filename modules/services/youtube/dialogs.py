import logging
import asyncio
import re
from typing import Any

from aiogram.enums import ContentType
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, Message
from aiogram_dialog import Dialog, Window, DialogManager
from aiogram_dialog.api.entities import MediaAttachment
from aiogram_dialog.widgets.media import DynamicMedia
from aiogram_dialog.widgets.text import Format
from aiogram_dialog.widgets.kbd import Button, Row, Group, Select, SwitchTo
from aiogram_dialog.widgets.input import TextInput
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from states.youtube import YouTubeDialogStates
from utils import format_duration
from .utils import parse_time_range

logger = logging.getLogger(__name__)


def get_reliable_thumbnail(url: str, thumbnail: str | None) -> str | None:
    match = re.search(r'(?:v=|/vi/|/shorts/|youtu\.be/)([\w-]{11})', url or '')
    if not match and thumbnail:
        match = re.search(r'/vi/([\w-]{11})', thumbnail)
    if match:
        return f"https://img.youtube.com/vi/{match.group(1)}/hqdefault.jpg"
    if thumbnail and (thumbnail.startswith("http://") or thumbnail.startswith("https://")):
        return thumbnail
    if thumbnail and thumbnail.startswith("//"):
        return "https:" + thumbnail
    return None


# --- Getters ---

async def get_common_metadata(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    start_data = dialog_manager.start_data or {}
    title = start_data.get("title") or "YouTube Media"
    uploader = start_data.get("uploader") or ""
    duration = start_data.get("duration") or 0
    dur_str = format_duration(duration) if duration else ""

    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")

    header = f"<b>{title}</b>"
    if uploader:
        ch_text = i18n.get("yt-label-channel", uploader=uploader) if i18n else f"Канал: {uploader}"
        header += f"\n{ch_text}"
    if dur_str:
        dur_text = i18n.get("yt-label-duration", duration=dur_str) if i18n else f"Длительность: {dur_str}"
        header += f"\n{dur_text}"

    url = start_data.get("url") or ""
    thumbnail_url = get_reliable_thumbnail(url, start_data.get("thumbnail"))
    media = MediaAttachment(type=ContentType.PHOTO, url=thumbnail_url) if thumbnail_url else None

    btn_video = i18n.get("yt-btn-video") if i18n else "Скачать видео"
    btn_audio = i18n.get("yt-btn-audio") if i18n else "Скачать аудио"
    btn_advanced = i18n.get("yt-btn-advanced") if i18n else "Расширенные настройки"
    btn_continue = i18n.get("yt-btn-continue") if i18n else "Далее"
    btn_back = i18n.get("yt-btn-back") if i18n else "Назад"
    btn_cancel = i18n.get("yt-btn-cancel") if i18n else "❌ Отмена"
    trim_prompt = i18n.get("yt-trim-ask-range") if i18n else "Введите интервал для обрезки в формате <b>hh:mm:ss-hh:mm:ss</b> (например, <code>01:20-02:45</code>) или <b>hh:mm:ss-inf</b>:"

    return {
        "title": title,
        "header": header,
        "uploader": uploader,
        "duration": duration,
        "media": media,
        "btn_video": btn_video,
        "btn_audio": btn_audio,
        "btn_advanced": btn_advanced,
        "btn_continue": btn_continue,
        "btn_back": btn_back,
        "btn_cancel": btn_cancel,
        "trim_prompt": trim_prompt,
    }


async def get_simple_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    return await get_common_metadata(dialog_manager)


async def get_balance_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    start_data = dialog_manager.start_data or {}
    options = start_data.get("options", [])
    audio_only = start_data.get("audio_only", {})
    is_premium = start_data.get("is_premium", False)

    sorted_opts = sorted(options, key=lambda x: x.get("target_height", 0), reverse=True)

    items = []
    for opt in sorted_opts:
        h = opt.get("target_height", 0)
        lbl = opt.get("label", f"{h}p")
        size_mb = opt.get("size_mb", 0.0)
        star = "★ " if (size_mb > 100 and not is_premium) else ""
        items.append({
            "id": f"video_{h}",
            "text": f"{star}{lbl} (~{size_mb:.1f} MB)",
            "height": h,
            "size_mb": size_mb,
            "is_audio": False
        })

    if audio_only:
        a_lbl = audio_only.get("label", "Audio")
        a_h = audio_only.get("target_height", 0)
        a_size = audio_only.get("size_mb", 0.0)
        items.append({
            "id": "audio",
            "text": f"{a_lbl} (~{a_size:.1f} MB)",
            "height": a_h,
            "size_mb": a_size,
            "is_audio": True
        })

    common = await get_common_metadata(dialog_manager)
    common["balance_formats"] = items
    return common


async def get_advanced_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    start_data = dialog_manager.start_data or {}
    dialog_data = dialog_manager.dialog_data

    options = start_data.get("options", [])
    audio_only = start_data.get("audio_only", {})
    is_premium = start_data.get("is_premium", False)

    selected_id = dialog_data.get("selected_format")
    if not selected_id and options:
        highest = max(options, key=lambda x: x.get("target_height", 0))
        selected_id = f"video_{highest.get('target_height', 0)}"
        dialog_data["selected_format"] = selected_id
    elif not selected_id and audio_only:
        selected_id = "audio"
        dialog_data["selected_format"] = selected_id

    items = []
    sorted_opts = sorted(options, key=lambda x: x.get("target_height", 0), reverse=True)
    for opt in sorted_opts:
        h = opt.get("target_height", 0)
        lbl = opt.get("label", f"{h}p")
        size_mb = opt.get("size_mb", 0.0)
        item_id = f"video_{h}"
        check = "✓ " if item_id == selected_id else ""
        star = "★ " if (size_mb > 100 and not is_premium) else ""
        items.append({
            "id": item_id,
            "text": f"{check}{star}{lbl} (~{size_mb:.1f} MB)",
            "height": h,
            "size_mb": size_mb,
            "is_audio": False
        })

    if audio_only:
        a_lbl = audio_only.get("label", "Audio")
        a_h = audio_only.get("target_height", 0)
        a_size = audio_only.get("size_mb", 0.0)
        item_id = "audio"
        check = "✓ " if item_id == selected_id else ""
        items.append({
            "id": item_id,
            "text": f"{check}{a_lbl} (~{a_size:.1f} MB)",
            "height": a_h,
            "size_mb": a_size,
            "is_audio": True
        })

    i18n: TranslatorRunner = dialog_manager.middleware_data.get("i18n")

    topich_id = "topich"
    check = "✓ " if topich_id == selected_id else ""
    topich_lbl = i18n.get("yt-btn-topich") if i18n else "ТОПИЧ"
    if not is_premium:
        topich_lbl = f"★ {topich_lbl}"
        
    items.append({
        "id": topich_id,
        "text": f"{check}{topich_lbl}",
        "height": 0,
        "size_mb": 0.0,
        "is_audio": False
    })

    trim_active = dialog_data.get("trim_active", False)
    if i18n:
        trim_label = i18n.get("yt-btn-trim-active") if trim_active else i18n.get("yt-btn-trim")
    else:
        trim_label = "✓ Обрезка" if trim_active else "Обрезка"
        
    if not is_premium:
        trim_label = f"★ {trim_label}"

    common = await get_common_metadata(dialog_manager)
    common["advanced_formats"] = items
    common["trim_button_label"] = trim_label
    return common


# --- Event Handlers ---

async def trigger_download(
    dialog_manager: DialogManager,
    height: int,
    is_audio: bool,
    size_mb: float = 0.0,
    is_topich: bool = False
):
    from .handler import process_youtube_download
    start_data = dialog_manager.start_data or {}
    url = start_data["url"]
    url_hash = start_data["url_hash"]

    middleware_data = dialog_manager.middleware_data
    event = dialog_manager.event

    if isinstance(event, CallbackQuery):
        user_id = event.from_user.id
        dialog_msg = event.message
        target_message = event.message.reply_to_message or event.message
    elif isinstance(event, Message):
        user_id = event.from_user.id
        dialog_msg = event
        target_message = event
    else:
        user_obj = middleware_data.get("event_from_user")
        user_id = user_obj.id if user_obj else 0
        dialog_msg = getattr(event, "message", None) or event
        target_message = dialog_msg

    i18n: TranslatorRunner = middleware_data.get("i18n")
    db_session: AsyncSession = middleware_data.get("db_session")

    is_premium = start_data.get("is_premium", False)

    if size_mb > 100 and not is_premium:
        from modules.payment.video import PaymentService
        payload = f"yt_{url_hash}_{height}_{1 if is_audio else 0}"
        invoice_params = await PaymentService.create_single_download_invoice(
            chat_id=target_message.chat.id,
            payload=payload,
            provider_token=""
        )
        invoice_params.pop('chat_id', None)
        await target_message.answer_invoice(**invoice_params)
        if dialog_msg:
            try:
                await dialog_msg.delete()
            except TelegramBadRequest as e:
                logger.warning("Failed to delete dialog message %s: %s", dialog_msg.message_id, e)
        await dialog_manager.done()
        return

    if dialog_msg:
        try:
            await dialog_msg.delete()
        except TelegramBadRequest as e:
            logger.warning("Failed to delete dialog message %s: %s", dialog_msg.message_id, e)
    await dialog_manager.done()

    asyncio.create_task(process_youtube_download(
        message=target_message,
        url=url,
        target_height=height,
        is_audio_only=is_audio,
        user_id=user_id,
        db_session=db_session,
        i18n=i18n,
        is_topich=is_topich
    ))


async def on_simple_video(c: CallbackQuery, button: Button, manager: DialogManager):
    start_data = manager.start_data or {}
    options = start_data.get("options", [])
    highest_h = max([opt.get("target_height", 0) for opt in options], default=0) if options else 0
    await trigger_download(manager, height=highest_h, is_audio=False)


async def on_simple_audio(c: CallbackQuery, button: Button, manager: DialogManager):
    start_data = manager.start_data or {}
    audio_only = start_data.get("audio_only", {})
    a_h = audio_only.get("target_height", 0) if audio_only else 0
    await trigger_download(manager, height=a_h, is_audio=True)


async def on_balance_format_click(c: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    start_data = manager.start_data or {}
    options = start_data.get("options", [])
    audio_only = start_data.get("audio_only", {})

    if item_id == "audio":
        a_h = audio_only.get("target_height", 0) if audio_only else 0
        a_size = audio_only.get("size_mb", 0.0) if audio_only else 0.0
        await trigger_download(manager, height=a_h, is_audio=True, size_mb=a_size)
    else:
        height = int(item_id.replace("video_", ""))
        matching = next((opt for opt in options if opt.get("target_height") == height), {})
        size_mb = matching.get("size_mb", 0.0)
        await trigger_download(manager, height=height, is_audio=False, size_mb=size_mb)


async def on_advanced_format_click(c: CallbackQuery, widget: Any, manager: DialogManager, item_id: str):
    start_data = manager.start_data or {}
    is_premium = start_data.get("is_premium", False)

    if item_id == "topich" and not is_premium:
        i18n: TranslatorRunner = manager.middleware_data.get("i18n")
        msg = i18n.get("yt-sponsor-only") if i18n else "🌟 Эта фича только для Спонсоров!"
        await c.answer(msg, show_alert=True)
        return

    manager.dialog_data["selected_format"] = item_id


async def on_cancel_click(c: CallbackQuery, button: Button, manager: DialogManager):
    if c.message:
        try:
            await c.message.delete()
        except TelegramBadRequest as e:
            logger.warning("Failed to delete dialog message %s: %s", c.message.message_id, e)
    await manager.done()
    await c.answer()


async def on_toggle_trim(c: CallbackQuery, button: Button, manager: DialogManager):
    start_data = manager.start_data or {}
    is_premium = start_data.get("is_premium", False)
    i18n: TranslatorRunner = manager.middleware_data.get("i18n")

    if not is_premium:
        msg = i18n.get("yt-sponsor-only") if i18n else "🌟 Эта фича только для Спонсоров!"
        await c.answer(msg, show_alert=True)
        return

    current = manager.dialog_data.get("trim_active", False)
    manager.dialog_data["trim_active"] = not current
    await c.answer()


async def on_advanced_continue(c: CallbackQuery, button: Button, manager: DialogManager):
    trim_active = manager.dialog_data.get("trim_active", False)
    if trim_active:
        await manager.switch_to(YouTubeDialogStates.trim_input)
        await c.answer()
    else:
        selected_id = manager.dialog_data.get("selected_format", "audio")
        start_data = manager.start_data or {}
        options = start_data.get("options", [])
        audio_only = start_data.get("audio_only", {})

        if selected_id == "topich":
            is_premium = start_data.get("is_premium", False)
            if not is_premium:
                i18n: TranslatorRunner = manager.middleware_data.get("i18n")
                msg = i18n.get("yt-sponsor-only") if i18n else "🌟 Эта фича только для Спонсоров!"
                await c.answer(msg, show_alert=True)
                return
            await trigger_download(manager, height=0, is_audio=False, size_mb=0.0, is_topich=True)
        elif selected_id == "audio":
            a_h = audio_only.get("target_height", 0) if audio_only else 0
            a_size = audio_only.get("size_mb", 0.0) if audio_only else 0.0
            await trigger_download(manager, height=a_h, is_audio=True, size_mb=a_size)
        else:
            height = int(selected_id.replace("video_", ""))
            matching = next((opt for opt in options if opt.get("target_height") == height), {})
            size_mb = matching.get("size_mb", 0.0)
            await trigger_download(manager, height=height, is_audio=False, size_mb=size_mb)


async def on_trim_input_success(m: Message, widget: Any, manager: DialogManager, text: str):
    start_data = manager.start_data or {}
    dialog_data = manager.dialog_data
    middleware_data = manager.middleware_data
    i18n: TranslatorRunner = middleware_data.get("i18n")
    db_session: AsyncSession = middleware_data.get("db_session")

    url = start_data["url"]
    duration = start_data.get("duration", 0)
    selected_id = dialog_data.get("selected_format", "audio")
    audio_only = start_data.get("audio_only", {})

    if selected_id == "audio":
        is_audio_only = True
        target_height = audio_only.get("target_height", 0) if audio_only else 0
    else:
        is_audio_only = False
        target_height = int(selected_id.replace("video_", ""))

    parsed = parse_time_range(text)
    if not parsed:
        await m.reply(i18n.get("yt-trim-invalid-range"))
        return

    start_formatted, end_formatted, start_seconds, end_seconds = parsed

    if duration > 0:
        dur_str = format_duration(duration)
        if start_seconds >= duration:
            await m.reply(i18n.get("yt-trim-out-of-bounds", duration=dur_str))
            return
        if end_seconds != -1 and end_seconds > duration:
            await m.reply(i18n.get("yt-trim-out-of-bounds", duration=dur_str))
            return

    await manager.done()

    from .handler import process_clip_download
    process_message = await m.reply(i18n.get("yt-trim-processing"))
    asyncio.create_task(process_clip_download(
        message=m,
        process_message=process_message,
        url=url,
        target_height=target_height,
        is_audio_only=is_audio_only,
        start_time=start_formatted,
        end_time=end_formatted,
        user_id=m.from_user.id if m.from_user else 0,
        db_session=db_session,
        i18n=i18n
    ))


async def get_trim_input_data(dialog_manager: DialogManager, **kwargs) -> dict[str, Any]:
    return await get_common_metadata(dialog_manager)


# --- Windows Definition ---

window_simple = Window(
    DynamicMedia("media"),
    Format("{header}"),
    Row(
        Button(Format("{btn_video}"), id="sim_video", on_click=on_simple_video),
        Button(Format("{btn_audio}"), id="sim_audio", on_click=on_simple_audio),
    ),
    Button(Format("{btn_cancel}"), id="cancel_dialog", on_click=on_cancel_click),
    state=YouTubeDialogStates.simple,
    getter=get_simple_data
)

window_balance = Window(
    DynamicMedia("media"),
    Format("{header}"),
    Group(
        Select(
            Format("{item[text]}"),
            id="bal_format_select",
            item_id_getter=lambda x: x["id"],
            items="balance_formats",
            on_click=on_balance_format_click
        ),
        width=2
    ),
    SwitchTo(Format("{btn_advanced}"), id="to_advanced", state=YouTubeDialogStates.advanced),
    Button(Format("{btn_cancel}"), id="cancel_dialog", on_click=on_cancel_click),
    state=YouTubeDialogStates.balance,
    getter=get_balance_data
)

window_advanced = Window(
    DynamicMedia("media"),
    Format("{header}"),
    Group(
        Select(
            Format("{item[text]}"),
            id="adv_format_select",
            item_id_getter=lambda x: x["id"],
            items="advanced_formats",
            on_click=on_advanced_format_click
        ),
        width=2
    ),
    Row(
        Button(Format("{trim_button_label}"), id="toggle_trim", on_click=on_toggle_trim),
        Button(Format("{btn_continue}"), id="adv_continue", on_click=on_advanced_continue),
    ),
    Button(Format("{btn_cancel}"), id="cancel_dialog", on_click=on_cancel_click),
    state=YouTubeDialogStates.advanced,
    getter=get_advanced_data
)

window_trim_input = Window(
    Format("{trim_prompt}"),
    TextInput(
        id="trim_input_text",
        on_success=on_trim_input_success
    ),
    SwitchTo(Format("{btn_back}"), id="back_to_adv", state=YouTubeDialogStates.advanced),
    state=YouTubeDialogStates.trim_input,
    getter=get_trim_input_data
)

youtube_dialog = Dialog(
    window_simple,
    window_balance,
    window_advanced,
    window_trim_input
)
