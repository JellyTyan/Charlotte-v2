import logging
from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from storage.db.crud import get_chat_settings, update_chat_settings
from handlers.settings import check_if_admin_or_owner, build_chat_banlist_keyboard
from utils.ephemeral import send_smart_message

logger = logging.getLogger(__name__)

router = Router()


def extract_target_user_id(message: Message) -> int | None:
    """Extract target user id from reply or command arguments."""
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id

    parts = (message.text or "").split()
    if len(parts) >= 2:
        arg = parts[1].strip()
        # Support optional mention-like format or raw integer
        if arg.startswith("@"):
            return None
        try:
            return int(arg)
        except ValueError:
            return None
    return None


@router.message(Command("cban"))
async def cban_command(message: Message, i18n: TranslatorRunner, db_session: AsyncSession) -> None:
    if message.chat.type not in ("group", "supergroup"):
        await send_smart_message(message, i18n.get("settings-no-allowed-dm"), for_user_id=message.from_user.id)
        return

    if not message.from_user or not message.bot:
        return

    is_admin = await check_if_admin_or_owner(message.bot, message.chat.id, message.from_user.id)
    if not is_admin:
        await send_smart_message(message, i18n.settings.no.permission(), for_user_id=message.from_user.id)
        return

    target_id = extract_target_user_id(message)
    if not target_id:
        await send_smart_message(message, i18n.get("cban-usage"), for_user_id=message.from_user.id)
        return

    if target_id == message.from_user.id:
        await send_smart_message(message, i18n.get("cban-cannot-ban-self"), for_user_id=message.from_user.id)
        return

    if target_id == message.bot.id:
        await send_smart_message(message, i18n.get("cban-cannot-ban-bot"), for_user_id=message.from_user.id)
        return

    # Check if target is admin or owner
    target_is_admin = await check_if_admin_or_owner(message.bot, message.chat.id, target_id)
    if target_is_admin:
        await send_smart_message(message, i18n.get("cban-cannot-ban-admin"), for_user_id=message.from_user.id)
        return

    chat_settings = await get_chat_settings(db_session, message.chat.id)
    if not chat_settings:
        await send_smart_message(message, i18n.get("general-error"), for_user_id=message.from_user.id)
        return

    if target_id in chat_settings.profile.banned_users:
        await send_smart_message(
            message,
            i18n.get("cban-already-banned", user_id=target_id),
            for_user_id=message.from_user.id
        )
        return

    chat_settings.profile.banned_users.add(target_id)
    await update_chat_settings(db_session, message.chat.id, chat_settings)

    await send_smart_message(
        message,
        i18n.get("cban-success", user_id=target_id),
        for_user_id=message.from_user.id
    )


@router.message(Command("cunban"))
async def cunban_command(message: Message, i18n: TranslatorRunner, db_session: AsyncSession) -> None:
    if message.chat.type not in ("group", "supergroup"):
        await send_smart_message(message, i18n.get("settings-no-allowed-dm"), for_user_id=message.from_user.id)
        return

    if not message.from_user or not message.bot:
        return

    is_admin = await check_if_admin_or_owner(message.bot, message.chat.id, message.from_user.id)
    if not is_admin:
        await send_smart_message(message, i18n.settings.no.permission(), for_user_id=message.from_user.id)
        return

    target_id = extract_target_user_id(message)
    if not target_id:
        await send_smart_message(message, i18n.get("cunban-usage"), for_user_id=message.from_user.id)
        return

    chat_settings = await get_chat_settings(db_session, message.chat.id)
    if not chat_settings:
        await send_smart_message(message, i18n.get("general-error"), for_user_id=message.from_user.id)
        return

    if target_id not in chat_settings.profile.banned_users:
        await send_smart_message(
            message,
            i18n.get("cunban-not-banned", user_id=target_id),
            for_user_id=message.from_user.id
        )
        return

    chat_settings.profile.banned_users.remove(target_id)
    await update_chat_settings(db_session, message.chat.id, chat_settings)

    await send_smart_message(
        message,
        i18n.get("cunban-success", user_id=target_id),
        for_user_id=message.from_user.id
    )


@router.message(Command("cbanlist"))
async def cbanlist_command(message: Message, i18n: TranslatorRunner, db_session: AsyncSession) -> None:
    if message.chat.type not in ("group", "supergroup"):
        await send_smart_message(message, i18n.get("settings-no-allowed-dm"), for_user_id=message.from_user.id)
        return

    if not message.from_user or not message.bot:
        return

    is_admin = await check_if_admin_or_owner(message.bot, message.chat.id, message.from_user.id)
    if not is_admin:
        await send_smart_message(message, i18n.settings.no.permission(), for_user_id=message.from_user.id)
        return

    chat_settings = await get_chat_settings(db_session, message.chat.id)
    if not chat_settings:
        await send_smart_message(message, i18n.get("general-error"), for_user_id=message.from_user.id)
        return

    banned_users = chat_settings.profile.banned_users
    if not banned_users:
        text = f"{i18n.get('cbanlist-title')}\n\n{i18n.get('cbanlist-empty')}"
        await send_smart_message(message, text, for_user_id=message.from_user.id)
        return

    user_list = "\n".join(f"• <code>{uid}</code>" for uid in sorted(banned_users))
    text = f"{i18n.get('cbanlist-title')}\n\n{user_list}"
    kb = build_chat_banlist_keyboard(banned_users, i18n)

    await send_smart_message(
        message,
        text,
        for_user_id=message.from_user.id,
        reply_markup=kb
    )
