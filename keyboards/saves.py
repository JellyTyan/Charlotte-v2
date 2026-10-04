from collections.abc import Sequence

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluentogram import TranslatorRunner

from storage.db.models import UserSaves
from utils.text_utils import escape_html

PAGE_SIZE = 5
TYPE_EMOJIS = {"video": "🎬", "photo": "🖼", "audio": "🎵", "gif": "🎞"}


class SavesPageCallback(CallbackData, prefix="sv_page"):
    page: int
    owner_id: int


class SavesItemCallback(CallbackData, prefix="sv_item"):
    action: str  # "view", "preview", "toggle_pub", "del", "rename", "to_list", "close"
    save_id: int
    page: int
    owner_id: int


class SavesReplaceCallback(CallbackData, prefix="sv_repl"):
    confirm: bool
    save_id: int
    owner_id: int


def save_status_text(save: UserSaves, i18n: TranslatorRunner) -> str:
    if not save.is_public:
        return i18n.saves.status.private()
    return i18n.saves.status.public() if save.is_approved else i18n.saves.status.pending()


def format_saves_list_text(total_count: int, i18n: TranslatorRunner) -> str:
    return f"{i18n.saves.header(count=total_count)}\n\n{i18n.saves.list.hint()}"


def format_save_card_text(save: UserSaves, bot_username: str, i18n: TranslatorRunner) -> str:
    # Вычисляем до i18n.saves.card: TranslatorRunner копит ключ в себе, и вложенный
    # i18n-вызов в аргументах склеился бы с ним («saves-card-saves-status-private»)
    status = save_status_text(save, i18n)
    return i18n.saves.card(
        emoji=TYPE_EMOJIS.get(save.media_type, "📁"),
        label=escape_html(save.label),
        status=status,
        uses=save.uses_count,
        date=save.created_at.strftime("%d.%m.%Y %H:%M") if save.created_at else "—",
        bot_username=bot_username,
    )


def _item(action: str, save_id: int, page: int, owner_id: int) -> str:
    return SavesItemCallback(action=action, save_id=save_id, page=page, owner_id=owner_id).pack()


def build_saves_list_keyboard(
    saves: Sequence[UserSaves],
    page: int,
    total_pages: int,
    owner_id: int,
    i18n: TranslatorRunner,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for s in saves:
        emoji = TYPE_EMOJIS.get(s.media_type, "📁")
        if s.is_public:
            pub_icon = "🌐" if s.is_approved else "⏳"
        else:
            pub_icon = "🔒"
        uses_tag = f" • 👁{s.uses_count}" if s.uses_count > 0 else ""
        label_display = s.label if len(s.label) <= 22 else (s.label[:19] + "...")
        builder.button(text=f"{emoji} {label_display} {pub_icon}{uses_tag}", callback_data=_item("view", s.id, page, owner_id))

    builder.adjust(1)

    nav_buttons: list[InlineKeyboardButton] = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(
            text="◀️", callback_data=SavesPageCallback(page=page - 1, owner_id=owner_id).pack(),
        ))
    # Нажатие на номер страницы просто перерисовывает текущую (отдельный noop-хендлер не нужен)
    nav_buttons.append(InlineKeyboardButton(
        text=f"{page + 1}/{total_pages}", callback_data=SavesPageCallback(page=page, owner_id=owner_id).pack(),
    ))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(
            text="▶️", callback_data=SavesPageCallback(page=page + 1, owner_id=owner_id).pack(),
        ))
    builder.row(*nav_buttons)

    builder.row(InlineKeyboardButton(text=i18n.saves.btn.close(), callback_data=_item("close", 0, page, owner_id)))
    return builder.as_markup()


def build_save_card_keyboard(
    save: UserSaves,
    page: int,
    owner_id: int,
    i18n: TranslatorRunner,
) -> InlineKeyboardMarkup:
    toggle_text = i18n.saves.btn.make.private() if save.is_public else i18n.saves.btn.make.public()
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=i18n.saves.btn.preview(), callback_data=_item("preview", save.id, page, owner_id)),
        InlineKeyboardButton(text=i18n.saves.btn.send(), switch_inline_query=save.label),
    )
    builder.row(
        InlineKeyboardButton(text=toggle_text, callback_data=_item("toggle_pub", save.id, page, owner_id)),
        InlineKeyboardButton(text=i18n.saves.btn.rename(), callback_data=_item("rename", save.id, page, owner_id)),
    )
    builder.row(
        InlineKeyboardButton(text=i18n.saves.btn.delete(), callback_data=_item("del", save.id, page, owner_id)),
        InlineKeyboardButton(text=i18n.saves.btn.back(), callback_data=_item("to_list", save.id, page, owner_id)),
    )
    return builder.as_markup()


def build_rename_cancel_keyboard(save_id: int, page: int, owner_id: int, i18n: TranslatorRunner) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.saves.btn.cancel(), callback_data=_item("view", save_id, page, owner_id))
    return builder.as_markup()


def build_replace_keyboard(save_id: int, owner_id: int, i18n: TranslatorRunner) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=i18n.saves.btn.replace(), callback_data=SavesReplaceCallback(confirm=True, save_id=save_id, owner_id=owner_id).pack())
    builder.button(text=i18n.saves.btn.cancel(), callback_data=SavesReplaceCallback(confirm=False, save_id=save_id, owner_id=owner_id).pack())
    builder.adjust(2)
    return builder.as_markup()
