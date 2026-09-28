import html
import logging
from aiogram import Router, F
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.ext.asyncio import AsyncSession
from fluentogram import TranslatorRunner

from storage.db.crud import (
    save_user_media,
    get_user_saves,
    get_user_saves_count,
    delete_user_save,
    toggle_save_public,
    get_save_by_id,
    check_if_user_premium,
    is_user_public_saves_banned,
)
from utils.text_utils import escape_html
from utils.ephemeral import send_smart_message
from storage.cache.redis_client import cache_set

router = Router(name="saves")
logger = logging.getLogger(__name__)

MAX_SAVES_FREE = 200
MAX_SAVES_PREMIUM = 1000
PAGE_SIZE = 5


from utils.recent_downloads import extract_media_from_message


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
            await callback.message.edit_ephemeral_text(
                text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
    except Exception as e:
        logger.debug(f"Could not edit message in saves callback: {e}")


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
    reply = message.reply_to_message
    if not reply:
        await send_smart_message(
            message,
            i18n.saves.usage(),
            for_user_id=user_id,
            parse_mode="HTML",
        )
        return

    # Защита: сохранять можно только сообщения, отправленные ботом
    bot_info = await message.bot.get_me()
    if not reply.from_user or reply.from_user.id != bot_info.id:
        await send_smart_message(
            message,
            i18n.saves.bot.only(),
            for_user_id=user_id,
            parse_mode="HTML",
        )
        return

    args_str = (command.args or "").strip()
    if not args_str:
        await send_smart_message(
            message,
            i18n.saves.no.name(),
            for_user_id=user_id,
            parse_mode="HTML",
        )
        return

    label = args_str

    if len(label) > 128:
        await send_smart_message(
            message,
            i18n.saves.name.too.long(),
            for_user_id=user_id,
            parse_mode="HTML",
        )
        return

    file_id, media_type, file_title = extract_media_from_message(reply)
    if not file_id or not media_type:
        await send_smart_message(
            message,
            i18n.saves.no.media(),
            for_user_id=user_id,
            parse_mode="HTML",
        )
        return

    current_count = await get_user_saves_count(db_session, user_id)
    is_premium = await check_if_user_premium(db_session, user_id)
    limit = MAX_SAVES_PREMIUM if is_premium else MAX_SAVES_FREE

    if current_count >= limit:
        await send_smart_message(
            message,
            i18n.saves.limit.reached(current=current_count, limit=limit),
            for_user_id=user_id,
            parse_mode="HTML",
        )
        return

    caption = reply.caption or None
    title = file_title or label

    save = await save_user_media(
        session=db_session,
        user_id=user_id,
        label=label,
        telegram_file_id=file_id,
        media_type=media_type,
        title=title,
        caption=caption,
        is_public=False,
    )

    bot_username = bot_info.username or "CharlotteFox_Bot"

    type_emojis = {
        "video": "🎬",
        "photo": "🖼",
        "audio": "🎵",
        "gif": "🎞",
    }
    emoji = type_emojis.get(media_type, "📁")

    status_text = i18n.saves.status.private()
    toggle_btn_text = i18n.saves.btn.make.public()

    builder = InlineKeyboardBuilder()
    builder.button(text=toggle_btn_text, callback_data=f"saves_toggle_pub:{save.id}")
    builder.button(text="🗑 Удалить", callback_data=f"saves_del:{save.id}:0")
    builder.adjust(2)

    await send_smart_message(
        message,
        i18n.saves.saved(
            emoji=emoji,
            label=escape_html(label),
            status=status_text,
            bot_username=bot_username,
        ),
        for_user_id=user_id,
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("saves_toggle_pub:"))
async def handle_toggle_public_callback(
    callback: CallbackQuery,
    db_session: AsyncSession,
    i18n: TranslatorRunner,
) -> None:
    """Toggle save between private and public."""
    try:
        save_id = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        return

    save_item = await get_save_by_id(db_session, save_id)
    if not save_item or save_item.user_id != callback.from_user.id:
        await callback.answer(i18n.saves.missing.toast(), show_alert=True)
        return

    if not save_item.is_public and await is_user_public_saves_banned(db_session, callback.from_user.id):
        await callback.answer(i18n.saves.banned.alert(), show_alert=True)
        return

    save = await toggle_save_public(db_session, callback.from_user.id, save_id)
    if not save:
        await callback.answer(i18n.saves.missing.toast(), show_alert=True)
        return

    toast = i18n.saves.toast.pending() if save.is_public else i18n.saves.toast.private()
    await callback.answer(toast, show_alert=False)

    toggle_btn_text = i18n.saves.btn.make.private() if save.is_public else i18n.saves.btn.make.public()
    builder = InlineKeyboardBuilder()
    builder.button(text=toggle_btn_text, callback_data=f"saves_toggle_pub:{save.id}")
    builder.button(text="🗑 Удалить", callback_data=f"saves_del:{save.id}:0")
    builder.adjust(2)

    bot_info = await callback.bot.get_me()
    bot_username = bot_info.username or "CharlotteFox_Bot"
    type_emojis = {"video": "🎬", "photo": "🖼", "audio": "🎵", "gif": "🎞"}
    emoji = type_emojis.get(save.media_type, "📁")
    status_text = i18n.saves.status.pending() if save.is_public else i18n.saves.status.private()

    new_text = i18n.saves.saved(
        emoji=emoji,
        label=escape_html(save.label),
        status=status_text,
        bot_username=bot_username,
    )
    await _safe_edit_message(callback, new_text, reply_markup=builder.as_markup())


@router.message(Command("saves"))
async def handle_saves_list(
    message: Message,
    db_session: AsyncSession,
    i18n: TranslatorRunner,
) -> None:
    """Display user's saved media list with pagination."""
    if not message.from_user:
        return

    user_id = message.from_user.id
    total_count = await get_user_saves_count(db_session, user_id)

    if total_count == 0:
        await send_smart_message(
            message,
            i18n.saves.empty(),
            for_user_id=user_id,
            parse_mode="HTML",
        )
        return

    bot_info = await message.bot.get_me()
    bot_username = bot_info.username or "CharlotteFox_Bot"

    text, markup = await _render_saves_page(db_session, user_id, page=0, total_count=total_count, i18n=i18n, bot_username=bot_username)
    await send_smart_message(
        message,
        text,
        for_user_id=user_id,
        reply_markup=markup,
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("saves_page:"))
async def handle_saves_page_callback(
    callback: CallbackQuery,
    db_session: AsyncSession,
    i18n: TranslatorRunner,
) -> None:
    """Handle pagination clicks in /saves list."""
    try:
        page = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        page = 0

    user_id = callback.from_user.id
    total_count = await get_user_saves_count(db_session, user_id)
    if total_count == 0:
        await _safe_edit_message(callback, i18n.saves.empty())
        await callback.answer()
        return

    bot_info = await callback.bot.get_me()
    bot_username = bot_info.username or "CharlotteFox_Bot"

    text, markup = await _render_saves_page(db_session, user_id, page=page, total_count=total_count, i18n=i18n, bot_username=bot_username)
    await _safe_edit_message(callback, text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("saves_del:"))
async def handle_delete_save_callback(
    callback: CallbackQuery,
    db_session: AsyncSession,
    i18n: TranslatorRunner,
) -> None:
    """Handle delete save button click."""
    parts = callback.data.split(":")
    save_id = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 0

    user_id = callback.from_user.id
    deleted = await delete_user_save(db_session, user_id, save_id)

    if deleted:
        await callback.answer(i18n.saves.deleted.toast(), show_alert=False)
    else:
        await callback.answer(i18n.saves.missing.toast(), show_alert=True)

    total_count = await get_user_saves_count(db_session, user_id)
    if total_count == 0:
        await _safe_edit_message(callback, i18n.saves.empty())
        return

    # Adjust page if out of range
    max_page = (total_count - 1) // PAGE_SIZE
    if page > max_page:
        page = max_page

    bot_info = await callback.bot.get_me()
    bot_username = bot_info.username or "CharlotteFox_Bot"

    text, markup = await _render_saves_page(db_session, user_id, page=page, total_count=total_count, i18n=i18n, bot_username=bot_username)
    await _safe_edit_message(callback, text, reply_markup=markup)


async def _render_saves_page(
    session: AsyncSession,
    user_id: int,
    page: int,
    total_count: int,
    i18n: TranslatorRunner,
    bot_username: str,
) -> tuple[str, InlineKeyboardMarkup]:
    """Helper to render /saves page text and pagination buttons."""
    offset = page * PAGE_SIZE
    saves = await get_user_saves(session, user_id, offset=offset, limit=PAGE_SIZE)

    type_emojis = {
        "video": "🎬",
        "photo": "🖼",
        "audio": "🎵",
        "gif": "🎞",
    }

    lines = [
        i18n.saves.header(count=total_count),
        "",
    ]

    builder = InlineKeyboardBuilder()

    for idx, save in enumerate(saves, start=offset + 1):
        emoji = type_emojis.get(save.media_type, "📁")
        pub_icon = "🌐" if save.is_public else "🔒"
        uses_str = f" • 👁 {save.uses_count}" if save.uses_count > 0 else ""
        lines.append(f"{idx}. {emoji} <b>{escape_html(save.label)}</b> {pub_icon}{uses_str}")
        builder.button(
            text=i18n.saves.delete.btn(label=save.label[:16]),
            callback_data=f"saves_del:{save.id}:{page}",
        )

    builder.adjust(1)

    # Navigation buttons
    max_page = (total_count - 1) // PAGE_SIZE
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text=i18n.saves.prev.btn(), callback_data=f"saves_page:{page - 1}"))
    nav_buttons.append(InlineKeyboardButton(text=f"{page + 1}/{max_page + 1}", callback_data="noop"))
    if page < max_page:
        nav_buttons.append(InlineKeyboardButton(text=i18n.saves.next.btn(), callback_data=f"saves_page:{page + 1}"))

    builder.row(*nav_buttons)

    lines.append("")
    lines.append(i18n.saves.footer.hint(bot_username=bot_username))

    return "\n".join(lines), builder.as_markup()


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
        await send_smart_message(
            message,
            i18n.copy.usage(),
            for_user_id=user_id,
            parse_mode="HTML",
        )
        return

    bot_info = await message.bot.get_me()
    if not reply.from_user or reply.from_user.id != bot_info.id:
        await send_smart_message(
            message,
            i18n.copy.bot.only(),
            for_user_id=user_id,
            parse_mode="HTML",
        )
        return

    file_id, media_type, file_title = extract_media_from_message(reply)
    if not file_id or not media_type:
        await send_smart_message(
            message,
            i18n.copy.no.media(),
            for_user_id=user_id,
            parse_mode="HTML",
        )
        return

    bot_username = bot_info.username or "CharlotteFox_Bot"
    title = file_title or "Copied media"

    data = {
        "file_id": file_id,
        "media_type": media_type,
        "title": title,
    }
    await cache_set(f"clipboard:{user_id}", data, ttl=3600)

    type_emojis = {
        "video": "🎬",
        "photo": "🖼",
        "audio": "🎵",
        "gif": "🎞",
    }
    emoji = type_emojis.get(media_type, "📋")

    await send_smart_message(
        message,
        i18n.copy.copied(
            emoji=emoji,
            bot_username=bot_username,
        ),
        for_user_id=user_id,
        parse_mode="HTML",
    )

