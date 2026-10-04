import logging
import re
import time

from aiogram import Bot, F, Router
from aiogram.dispatcher.event.bases import SkipHandler
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.saves import (
    PAGE_SIZE,
    TYPE_EMOJIS,
    SavesItemCallback,
    SavesPageCallback,
    build_rename_cancel_keyboard,
    build_save_card_keyboard,
    build_saves_list_keyboard,
    format_save_card_text,
    format_saves_list_text,
    save_status_text,
)
from middlewares.button_owner import register_message_owner
from modules.inline.handler import MUSIC_TAGS, PASTE_TRIGGERS, RECENT_TAGS, SAVED_TAGS
from states.saves import SavesStates
from storage.cache.redis_client import cache_set
from storage.db.crud import (
    check_if_user_premium,
    delete_user_save,
    get_public_save_by_file_id,
    get_save_by_file_id,
    get_save_by_id,
    get_user_saves,
    get_user_saves_count,
    is_user_public_saves_banned,
    rename_user_save,
    save_user_media,
    toggle_save_public,
)
from utils.ephemeral import send_smart_message
from utils.recent_downloads import extract_file_unique_id, extract_media_from_message
from utils.text_utils import escape_html

router = Router(name="saves")
logger = logging.getLogger(__name__)

MAX_SAVES_FREE = 200
MAX_SAVES_PREMIUM = 1000
MAX_LABEL_LEN = 128
_MAX_WORD_LEN = 64  # защита от «словa» из сотни символов без пробелов

# Inline-триггеры бота: название, начинающееся с них, никогда не найдётся поиском
_RESERVED_PREFIXES = frozenset(t.lower() for t in RECENT_TAGS + MUSIC_TAGS + SAVED_TAGS)
_RESERVED_EXACT = frozenset(t.lower() for t in PASTE_TRIGGERS)

# «Мусорное» название: только цифры, пунктуация, эмодзи, подчёркивания
_TRASH_PATTERN = re.compile(r"^[\W\d_]+$")

_RENAME_TTL = 300  # сек. — сколько ждём новое название после «Переименовать»


def _label_error(label: str, i18n: TranslatorRunner) -> str | None:
    """Вернуть текст ошибки для пользователя или None, если название подходит."""
    if len(label) > MAX_LABEL_LEN:
        return i18n.saves.name.too.long()
    lowered = label.lower()
    if lowered in _RESERVED_EXACT or lowered.split()[0] in _RESERVED_PREFIXES:
        return i18n.saves.label.reserved(label=escape_html(label))
    if _TRASH_PATTERN.match(label):
        return i18n.saves.label.trash()
    if any(len(w) > _MAX_WORD_LEN for w in label.split()):
        return i18n.saves.label.word.too.long()
    return None


async def _bot_username(bot: Bot) -> str:
    return (await bot.me()).username or "CharlotteFox_Bot"


async def _safe_edit_message(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    """Safely edit regular or ephemeral message in callbacks."""
    if not callback.message:
        return
    try:
        if getattr(callback.message, "ephemeral_message_id", None) is not None:
            await callback.message.edit_ephemeral_text(text, reply_markup=reply_markup, parse_mode="HTML")
        else:
            await callback.message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except Exception as e:
        logger.debug(f"Could not edit message in saves callback: {e}")


async def _render_list(
    session: AsyncSession, user_id: int, page: int, i18n: TranslatorRunner
) -> tuple[str, InlineKeyboardMarkup | None]:
    total_count = await get_user_saves_count(session, user_id)
    if total_count == 0:
        return i18n.saves.empty(), None
    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(0, min(page, total_pages - 1))
    saves = await get_user_saves(session, user_id, offset=page * PAGE_SIZE, limit=PAGE_SIZE)
    return (
        format_saves_list_text(total_count, i18n),
        build_saves_list_keyboard(saves, page=page, total_pages=total_pages, owner_id=user_id, i18n=i18n),
    )


# ─────────────────────────────────────────────────────────────────────────────
# /save command
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("save"))
async def handle_save_command(
    message: Message,
    command: CommandObject,
    db_session: AsyncSession,
    i18n: TranslatorRunner,
) -> None:
    """Save media from a replied message to the user's personal library."""
    if not message.from_user:
        return

    user_id = message.from_user.id

    async def reply(text: str, **kwargs) -> None:
        await send_smart_message(message, text, for_user_id=user_id, parse_mode="HTML", **kwargs)

    source = message.reply_to_message
    if not source:
        return await reply(i18n.saves.usage())

    # Сохранять можно только сообщения, отправленные ботом
    if not source.from_user or source.from_user.id != message.bot.id:
        return await reply(i18n.saves.bot.only())

    label = (command.args or "").strip()
    if not label:
        return await reply(i18n.saves.no.name())
    if error := _label_error(label, i18n):
        return await reply(error)

    file_id, media_type, file_title = extract_media_from_message(source)
    if not file_id or not media_type:
        return await reply(i18n.saves.no.media())

    file_unique_id = extract_file_unique_id(source)
    caption = source.caption or None
    title = file_title or label

    # Тот же файл уже сохранён?
    dupe_media = await get_save_by_file_id(db_session, user_id, file_id, file_unique_id)
    if dupe_media:
        return await reply(i18n.saves.dupe.media(existing_label=escape_html(dupe_media.label)))

    # Одинаковые названия разрешены: несколько разных картинок могут быть «Sanae Art Touhou»,
    # всё внутри (кнопки, inline-результаты, счётчики) работает по id

    current_count = await get_user_saves_count(db_session, user_id)
    limit = MAX_SAVES_PREMIUM if await check_if_user_premium(db_session, user_id) else MAX_SAVES_FREE
    if current_count >= limit:
        return await reply(i18n.saves.limit.reached(current=current_count, limit=limit))

    save = await save_user_media(
        session=db_session,
        user_id=user_id,
        label=label,
        telegram_file_id=file_id,
        media_type=media_type,
        title=title,
        caption=caption,
        is_public=False,
        file_unique_id=file_unique_id,
    )

    status = save_status_text(save, i18n)  # до i18n.saves.saved — см. format_save_card_text
    bot_username = await _bot_username(message.bot)
    await reply(
        i18n.saves.saved(
            emoji=TYPE_EMOJIS.get(media_type, "📁"),
            label=escape_html(save.label),
            status=status,
            bot_username=bot_username,
        ),
        reply_markup=build_save_card_keyboard(save, page=0, owner_id=user_id, i18n=i18n),
    )


# ─────────────────────────────────────────────────────────────────────────────
# /saves list, cards, actions
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("saves"))
async def handle_saves_list(
    message: Message,
    db_session: AsyncSession,
    i18n: TranslatorRunner,
) -> None:
    """Show the user's media library."""
    if not message.from_user:
        return

    user_id = message.from_user.id
    text, markup = await _render_list(db_session, user_id, 0, i18n)
    if markup is None:
        await send_smart_message(message, text, for_user_id=user_id, parse_mode="HTML")
        return

    menu_msg = await message.reply(text, reply_markup=markup, parse_mode="HTML")
    await register_message_owner(menu_msg, user_id)


@router.callback_query(SavesPageCallback.filter())
async def handle_saves_page(
    callback: CallbackQuery,
    callback_data: SavesPageCallback,
    db_session: AsyncSession,
    i18n: TranslatorRunner,
) -> None:
    if callback.from_user.id != callback_data.owner_id:
        await callback.answer(i18n.saves.foreign.library(), show_alert=True)
        return

    text, markup = await _render_list(db_session, callback.from_user.id, callback_data.page, i18n)
    await _safe_edit_message(callback, text, reply_markup=markup)
    await callback.answer()


@router.callback_query(SavesItemCallback.filter())
async def handle_saves_item(
    callback: CallbackQuery,
    callback_data: SavesItemCallback,
    state: FSMContext,
    db_session: AsyncSession,
    i18n: TranslatorRunner,
) -> None:
    user_id = callback.from_user.id
    if user_id != callback_data.owner_id:
        await callback.answer(i18n.saves.foreign.library(), show_alert=True)
        return

    action = callback_data.action
    page = callback_data.page

    if action == "close":
        await state.clear()
        if callback.message:
            try:
                await callback.message.delete()
            except Exception:
                pass
        await callback.answer()
        return

    if action == "to_list":
        await state.clear()
        text, markup = await _render_list(db_session, user_id, page, i18n)
        await _safe_edit_message(callback, text, reply_markup=markup)
        await callback.answer()
        return

    if action == "del":
        deleted = await delete_user_save(db_session, user_id, callback_data.save_id)
        if deleted:
            await callback.answer(i18n.saves.deleted.toast())
        else:
            await callback.answer(i18n.saves.missing.toast(), show_alert=True)
        text, markup = await _render_list(db_session, user_id, page, i18n)
        await _safe_edit_message(callback, text, reply_markup=markup)
        return

    # Остальные действия работают с конкретной сохранёнкой пользователя
    save = await get_save_by_id(db_session, callback_data.save_id)
    if not save or save.user_id != user_id:
        await callback.answer(i18n.saves.missing.toast(), show_alert=True)
        return

    if action == "view":
        await state.clear()
        text = format_save_card_text(save, await _bot_username(callback.bot), i18n)
        await _safe_edit_message(callback, text, reply_markup=build_save_card_keyboard(save, page, user_id, i18n))
        await callback.answer()

    elif action == "preview":
        send = {
            "video": callback.bot.send_video,
            "photo": callback.bot.send_photo,
            "gif": callback.bot.send_animation,
            "audio": callback.bot.send_audio,
        }.get(save.media_type, callback.bot.send_document)
        try:
            await send(callback.message.chat.id, save.telegram_file_id, caption=f"👁 <b>{escape_html(save.label)}</b>", parse_mode="HTML")
            await callback.answer()
        except Exception as e:
            logger.warning("Failed to preview save %s: %s", save.id, e)
            await callback.answer(i18n.saves.preview.failed(), show_alert=True)

    elif action == "toggle_pub":
        if not save.is_public:
            if await is_user_public_saves_banned(db_session, user_id):
                await callback.answer(i18n.saves.banned.alert(), show_alert=True)
                return
            if await get_public_save_by_file_id(
                db_session, save.telegram_file_id, save.file_unique_id, exclude_save_id=save.id
            ):
                await callback.answer(i18n.saves.dupe.public(), show_alert=True)
                return

        updated = await toggle_save_public(db_session, user_id, save.id)
        if not updated:
            await callback.answer(i18n.saves.missing.toast(), show_alert=True)
            return

        await callback.answer(i18n.saves.toast.pending() if updated.is_public else i18n.saves.toast.private())
        text = format_save_card_text(updated, await _bot_username(callback.bot), i18n)
        await _safe_edit_message(callback, text, reply_markup=build_save_card_keyboard(updated, page, user_id, i18n))

    elif action == "rename":
        await state.set_state(SavesStates.rename_input)
        await state.set_data({"save_id": save.id, "page": page, "ts": time.time()})
        await _safe_edit_message(
            callback,
            i18n.saves.rename.prompt(label=escape_html(save.label), max=MAX_LABEL_LEN),
            reply_markup=build_rename_cancel_keyboard(save.id, page, user_id, i18n),
        )
        await callback.answer()

    else:
        await callback.answer()


@router.message(SavesStates.rename_input, F.text)
async def handle_rename_input(
    message: Message,
    state: FSMContext,
    db_session: AsyncSession,
    i18n: TranslatorRunner,
) -> None:
    data = await state.get_data()
    is_link = any(e.type in ("url", "text_link") for e in (message.entities or []))

    # Команды, ссылки на скачивание и «забытый» режим переименования отдаём остальным хендлерам
    if message.text.startswith("/") or is_link or time.time() - data.get("ts", 0) > _RENAME_TTL:
        await state.clear()
        raise SkipHandler()

    user_id = message.from_user.id
    save_id = data.get("save_id")
    label = message.text.strip()

    if error := _label_error(label, i18n):
        await message.reply(error, parse_mode="HTML")
        return

    was_approved_public = False
    current = await get_save_by_id(db_session, save_id)
    if current:
        was_approved_public = current.is_public and current.is_approved

    updated = await rename_user_save(db_session, save_id, user_id, label)
    await state.clear()
    if not updated:
        await message.reply(i18n.saves.missing.toast())
        return

    text = i18n.saves.renamed(label=escape_html(updated.label))
    if was_approved_public and not updated.is_approved:
        text += f"\n<i>⚠️ {i18n.saves.rename.remoderation()}</i>"
    text += "\n\n" + format_save_card_text(updated, await _bot_username(message.bot), i18n)

    await message.reply(
        text,
        reply_markup=build_save_card_keyboard(updated, page=data.get("page", 0), owner_id=user_id, i18n=i18n),
        parse_mode="HTML",
    )


# ─────────────────────────────────────────────────────────────────────────────
# /copy command
# ─────────────────────────────────────────────────────────────────────────────

@router.message(Command("copy"))
async def handle_copy_command(
    message: Message,
    i18n: TranslatorRunner,
) -> None:
    """Copy media from a replied bot message into clipboard for 1 hour."""
    if not message.from_user:
        return

    user_id = message.from_user.id
    reply = message.reply_to_message
    if not reply:
        await send_smart_message(message, i18n.copy.usage(), for_user_id=user_id, parse_mode="HTML")
        return

    if not reply.from_user or reply.from_user.id != message.bot.id:
        await send_smart_message(message, i18n.copy.bot.only(), for_user_id=user_id, parse_mode="HTML")
        return

    file_id, media_type, file_title = extract_media_from_message(reply)
    if not file_id or not media_type:
        await send_smart_message(message, i18n.copy.no.media(), for_user_id=user_id, parse_mode="HTML")
        return

    data = {
        "file_id": file_id,
        "media_type": media_type,
        "title": file_title or "Copied media",
    }
    await cache_set(f"clipboard:{user_id}", data, ttl=3600)

    await send_smart_message(
        message,
        i18n.copy.copied(
            emoji=TYPE_EMOJIS.get(media_type, "📋"),
            bot_username=await _bot_username(message.bot),
        ),
        for_user_id=user_id,
        parse_mode="HTML",
    )
