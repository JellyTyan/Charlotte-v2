import re
from typing import Any

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluentogram import TranslatorRunner
from utils import format_duration

from utils.text_utils import escape_html


class YouTubeActionCallback(CallbackData, prefix="yt_act"):
    action: str  # "sim_vid", "sim_aud", "to_adv", "to_bal", "toggle_trim", "cont", "cancel"
    owner_id: int
    h: str  # url_hash


class YouTubeFormatCallback(CallbackData, prefix="yt_fmt"):
    owner_id: int
    h: str  # url_hash
    item_id: str  # e.g. "v_1080", "audio", "topich"
    mode: str  # "bal" or "adv"


def get_reliable_thumbnail(url: str, thumbnail: str | None) -> str | None:
    match = re.search(r'(?:v=|/vi/|/shorts/|youtu\.be/)([\w-]{11})', url or '')
    if not match and thumbnail:
        match = re.search(r'/vi/([\w-]{11})', thumbnail)
    if match:
        return f"https://img.youtube.com/vi/{match.group(1)}/hqdefault.jpg"
    if thumbnail and thumbnail.startswith(("http://", "https://")):
        return thumbnail
    if thumbnail and thumbnail.startswith("//"):
        return "https:" + thumbnail
    return None


def build_yt_header(meta_data: dict[str, Any], i18n: TranslatorRunner | None = None) -> str:
    title = escape_html(str(meta_data.get("title") or "YouTube Media"))
    uploader = escape_html(str(meta_data.get("uploader") or ""))
    duration = meta_data.get("duration") or 0
    dur_str = format_duration(duration) if duration else ""

    header = f"<b>{title}</b>"
    if uploader:
        ch_text = i18n.get("yt-label-channel", uploader=uploader) if i18n else f"Канал: {uploader}"
        header += f"\n{ch_text}"
    if dur_str:
        dur_text = i18n.get("yt-label-duration", duration=dur_str) if i18n else f"Длительность: {dur_str}"
        header += f"\n{dur_text}"

    return header


def build_simple_keyboard(
    owner_id: int,
    h: str,
    i18n: TranslatorRunner | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    btn_video = i18n.get("yt-btn-video") if i18n else "Скачать видео"
    btn_audio = i18n.get("yt-btn-audio") if i18n else "Скачать аудио"
    btn_cancel = i18n.get("yt-btn-cancel") if i18n else "❌ Отмена"

    builder.button(
        text=btn_video,
        callback_data=YouTubeActionCallback(action="sim_vid", owner_id=owner_id, h=h).pack(),
    )
    builder.button(
        text=btn_audio,
        callback_data=YouTubeActionCallback(action="sim_aud", owner_id=owner_id, h=h).pack(),
    )
    builder.button(
        text=btn_cancel,
        callback_data=YouTubeActionCallback(action="cancel", owner_id=owner_id, h=h).pack(),
    )
    builder.adjust(2, 1)
    return builder.as_markup()


def build_balance_keyboard(
    owner_id: int,
    h: str,
    meta_data: dict[str, Any],
    i18n: TranslatorRunner | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    options = meta_data.get("options", [])
    audio_only = meta_data.get("audio_only", {})
    is_premium = meta_data.get("is_premium", False)

    sorted_opts = sorted(options, key=lambda x: x.get("target_height", 0), reverse=True)
    for opt in sorted_opts:
        height = opt.get("target_height", 0)
        lbl = opt.get("label", f"{height}p")
        size_mb = opt.get("size_mb", 0.0)
        star = "★ " if (size_mb > 100 and not is_premium) else ""
        text = f"{star}{lbl} (~{size_mb:.1f} MB)"
        builder.button(
            text=text,
            callback_data=YouTubeFormatCallback(owner_id=owner_id, h=h, item_id=f"v_{height}", mode="bal").pack(),
        )

    if audio_only:
        a_lbl = audio_only.get("label", "Audio")
        a_size = audio_only.get("size_mb", 0.0)
        builder.button(
            text=f"{a_lbl} (~{a_size:.1f} MB)",
            callback_data=YouTubeFormatCallback(owner_id=owner_id, h=h, item_id="audio", mode="bal").pack(),
        )

    builder.adjust(2)

    # Action buttons
    btn_advanced = i18n.get("yt-btn-advanced") if i18n else "Расширенные настройки"
    btn_cancel = i18n.get("yt-btn-cancel") if i18n else "❌ Отмена"

    builder.row(
        InlineKeyboardButton(
            text=btn_advanced,
            callback_data=YouTubeActionCallback(action="to_adv", owner_id=owner_id, h=h).pack(),
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=btn_cancel,
            callback_data=YouTubeActionCallback(action="cancel", owner_id=owner_id, h=h).pack(),
        )
    )
    return builder.as_markup()


def build_advanced_keyboard(
    owner_id: int,
    h: str,
    meta_data: dict[str, Any],
    i18n: TranslatorRunner | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    options = meta_data.get("options", [])
    audio_only = meta_data.get("audio_only", {})
    is_premium = meta_data.get("is_premium", False)
    selected_id = meta_data.get("selected_format", "")
    trim_active = meta_data.get("trim_active", False)

    sorted_opts = sorted(options, key=lambda x: x.get("target_height", 0), reverse=True)
    for opt in sorted_opts:
        height = opt.get("target_height", 0)
        lbl = opt.get("label", f"{height}p")
        size_mb = opt.get("size_mb", 0.0)
        item_id = f"v_{height}"
        check = "✓ " if item_id == selected_id else ""
        star = "★ " if (size_mb > 100 and not is_premium) else ""
        text = f"{check}{star}{lbl} (~{size_mb:.1f} MB)"
        builder.button(
            text=text,
            callback_data=YouTubeFormatCallback(owner_id=owner_id, h=h, item_id=item_id, mode="adv").pack(),
        )

    if audio_only:
        a_lbl = audio_only.get("label", "Audio")
        a_size = audio_only.get("size_mb", 0.0)
        item_id = "audio"
        check = "✓ " if item_id == selected_id else ""
        text = f"{check}{a_lbl} (~{a_size:.1f} MB)"
        builder.button(
            text=text,
            callback_data=YouTubeFormatCallback(owner_id=owner_id, h=h, item_id=item_id, mode="adv").pack(),
        )

    # Topich
    topich_id = "topich"
    check = "✓ " if topich_id == selected_id else ""
    topich_lbl = i18n.get("yt-btn-topich") if i18n else "ТОПИЧ"
    if not is_premium:
        topich_lbl = f"★ {topich_lbl}"
    builder.button(
        text=f"{check}{topich_lbl}",
        callback_data=YouTubeFormatCallback(owner_id=owner_id, h=h, item_id=topich_id, mode="adv").pack(),
    )

    builder.adjust(2)

    # Trim button label
    if i18n:
        trim_label = i18n.get("yt-btn-trim-active") if trim_active else i18n.get("yt-btn-trim")
    else:
        trim_label = "✓ Обрезка" if trim_active else "Обрезка"
    if not is_premium:
        trim_label = f"★ {trim_label}"

    btn_continue = i18n.get("yt-btn-continue") if i18n else "Далее"
    btn_cancel = i18n.get("yt-btn-cancel") if i18n else "❌ Отмена"

    builder.row(
        InlineKeyboardButton(
            text=trim_label,
            callback_data=YouTubeActionCallback(action="toggle_trim", owner_id=owner_id, h=h).pack(),
        ),
        InlineKeyboardButton(
            text=btn_continue,
            callback_data=YouTubeActionCallback(action="cont", owner_id=owner_id, h=h).pack(),
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text=btn_cancel,
            callback_data=YouTubeActionCallback(action="cancel", owner_id=owner_id, h=h).pack(),
        )
    )

    return builder.as_markup()


def build_trim_input_keyboard(
    owner_id: int,
    h: str,
    i18n: TranslatorRunner | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    btn_back = i18n.get("yt-btn-back") if i18n else "◀️ Назад"
    builder.button(
        text=btn_back,
        callback_data=YouTubeActionCallback(action="to_adv", owner_id=owner_id, h=h).pack(),
    )
    return builder.as_markup()
