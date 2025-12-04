from aiogram import Bot
from aiogram.enums.chat_member_status import ChatMemberStatus
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InlineKeyboardMarkup,
    Message,
    InlineKeyboardButton,
    CallbackQuery,
    InaccessibleMessage
)
from aiogram.enums import ParseMode
# from aiogram.utils.i18n import gettext as _
import logging

from storage.db.crud import update_user_settings, update_chat_settings, get_user_settings, get_chat_settings, create_user, create_chat
from core.loader import dp
# from main import custom_i18n
# from utils.register_services import SERVICES


settings_keys = [
    "send_raw", "send_music_covers", "send_reactions", "send_notifications",
    "auto_caption", "auto_translate_titles",
]

chat_only_settings = [
    "allow_playlists", "blocked_services"
]

settings_descriptions_raw = {
    "send_raw": "Send the uncompressed version of art images after the usual preview, so you can get the best quality.",
    "send_notifications": "Control whether a sound notification is sent when media is delivered.",
    "send_music_covers": "Send music covers as separate files after the track is sent.",
    "send_reactions": "Automatically add an emoji reaction to messages with links that I process.",
    "auto_caption": "Automatically add captions to downloaded media.",
    "auto_translate_titles": "Translate captions and titles into your preferred language.",
    "allow_playlists": "Allow downloading full playlists from supported platforms in this chat.",
    "blocked_services": "View and manage which websites or platforms are blocked in this chat."
}

LANGUAGES = [
    { "code": "en", "name": "English", "flag": "🇺🇲" },
    { "code": "uk", "name": "Українська", "flag": "🇺🇦" },
    { "code": "be", "name": "Беларуская", "flag": "🇧🇾" },
    { "code": "ru", "name": "Русский", "flag": "🇷🇺" },
    { "code": "pl", "name": "Polski", "flag": "🇵🇱" },
    { "code": "cs", "name": "Čeština", "flag": "🇨🇿" },
    { "code": "de", "name": "Deutsch", "flag": "🇩🇪" },
    { "code": "fr", "name": "Français", "flag": "🇫🇷" },
    { "code": "es", "name": "Español", "flag": "🇪🇸" },
    { "code": "it", "name": "Italiano", "flag": "🇮🇹" },
    { "code": "pt", "name": "Português", "flag": "🇵🇹" },
    { "code": "tr", "name": "Türkçe", "flag": "🇹🇷" },
    { "code": "vi", "name": "Tiếng Việt", "flag": "🇻🇳" },
    { "code": "id", "name": "Bahasa Indonesia", "flag": "🇮🇩" },
    { "code": "fa", "name": "فارسی", "flag": "🇮🇷" },
    { "code": "zh-CN", "name": "中文 (简体)", "flag": "🇨🇳" },
    { "code": "ja", "name": "日本語", "flag": "🇯🇵" },
    { "code": "ko", "name": "한국어", "flag": "🇰🇷" },
    { "code": "hi", "name": "हिन्दी", "flag": "🇮🇳" }
]

def build_main_keyboard(settings: dict, is_group: bool = False) -> InlineKeyboardMarkup:
    def icon(flag: bool) -> str:
        return "✅" if flag else "❌"

    keyboards = [
        [
        InlineKeyboardButton(text=f"{('Language')} →", callback_data="settings_lang"),
        InlineKeyboardButton(text=f"{icon(settings['send_raw'])} {('Send art raw')}", callback_data="settings_send_raw"),
        ],
        [
            InlineKeyboardButton(text=f"{icon(settings['send_music_covers'])} {('Send Music Covers')}", callback_data="settings_send_music_covers"),
            InlineKeyboardButton(text=f"{icon(settings['send_reactions'])} {('Send reactions')}", callback_data="settings_send_reactions"),
        ],
        [
            InlineKeyboardButton(text=f"{icon(settings['auto_translate_titles'])} {('Auto translate titles')}", callback_data="settings_auto_translate_titles"),
            InlineKeyboardButton(text=f"{icon(settings['auto_caption'])} {('Auto caption')}", callback_data="settings_auto_caption"),
        ],
        [
            InlineKeyboardButton(text=f"{icon(settings['send_notifications'])} {('Send a notification')}", callback_data="settings_send_notifications"),
            InlineKeyboardButton(text=f"{('Title language')} →", callback_data="settings_title_language"),
        ],
    ]

    # Добавляем настройки только для групп
    if is_group:
        keyboards.append([
            InlineKeyboardButton(text=f"{icon(settings['allow_playlists'])} {('Allow playlists')}", callback_data="settings_allow_playlists"),
            InlineKeyboardButton(text=f"🔒 {('Blocked services')} →", callback_data="settings_blocked_services"),
        ])

    kb = InlineKeyboardMarkup(inline_keyboard=keyboards)
    return kb

def build_back_keyboard():
    """Back button - used within handlers when i18n context is already available"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="🔙 " + ("Back"), callback_data="settings_back")]]
    )

async def get_default_settings():
    """Returns default settings"""
    return {
        "send_raw": False,
        "send_music_covers": False,
        "send_reactions": False,
        "send_notifications": False,
        "auto_caption": False,
        "auto_translate_titles": False,
        "allow_playlists": True,
        "blocked_services": [],
    }

async def get_settings_for_chat(chat_id: int, user_id: int) -> dict:
    """Gets settings for chat or user"""
    if chat_id < 0:  # Group
        settings_obj = await get_chat_settings(chat_id)
        if not settings_obj:
            await create_chat(chat_id, user_id)
            settings_obj = await get_chat_settings(chat_id)
    else:  # Private chat
        settings_obj = await get_user_settings(user_id)
        if not settings_obj:
            await create_user(user_id)
            settings_obj = await get_user_settings(user_id)

    if not settings_obj:
        return await get_default_settings()

    return {
        "send_raw": settings_obj.send_raw,
        "send_notifications": settings_obj.send_notifications,
        "send_music_covers": settings_obj.send_music_covers,
        "send_reactions": settings_obj.send_reactions,
        "auto_caption": settings_obj.auto_caption,
        "auto_translate_titles": settings_obj.auto_translate_titles,
        "allow_playlists": getattr(settings_obj, 'allow_playlists', True),
        "blocked_services": getattr(settings_obj, 'blocked_services', []),
    }

@dp.message(Command("settings"))
async def settings_command(message: Message) -> None:
    chat = message.chat
    if message.bot is None or message.from_user is None:
        return
    if chat.type in ("group", "supergroup"):
        is_admin = await check_if_admin_or_owner(message.bot, chat.id, message.from_user.id)
        if not is_admin:
            await message.answer(("You don't have permission to edit these settings!"))
            return

    settings = await get_settings_for_chat(chat.id, message.from_user.id)
    is_group = chat.type in ("group", "supergroup")

    await message.answer(
        ("Welcome! Here are your personal settings. Feel free to customize them as you like!"),
        reply_markup=build_main_keyboard(settings, is_group)
    )


@dp.callback_query(lambda c: c.data == "settings_back")
async def settings_back(callback: CallbackQuery):
    if callback.message is None:
        return
    settings = await get_settings_for_chat(callback.message.chat.id, callback.from_user.id)
    is_group = callback.message.chat.type in ("group", "supergroup")
    text = ("Welcome! Here are your personal settings. Feel free to customize them as you like!")
    if isinstance(callback.message, InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(
            callback.from_user.id,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=build_main_keyboard(settings, is_group)
            )
    else:
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=build_main_keyboard(settings, is_group)
        )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("settings_") and c.data in [f"settings_{k}" for k in settings_keys + ["allow_playlists"]])
async def toggle_setting(callback: CallbackQuery):
    data = callback.data
    message = callback.message
    if not data or not message:
        return
    key = data.split("_", 1)[1]
    chat = message.chat

    # Check if the setting is available for this chat type
    if chat.type in ("group", "supergroup"):
        if key not in settings_keys and key != "allow_playlists":
            await callback.answer(("This setting is not available for groups!"))
            return
    else:
        if key not in settings_keys:
            await callback.answer(("This setting is not available for private chats!"))
            return

    # Get current settings
    current_settings = await get_settings_for_chat(chat.id, callback.from_user.id)
    current_value = current_settings[key]

    # Create enable/disable keyboard
    new_value = not current_value
    callback_data = f"toggle_{key}_{new_value}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"✅ {('Enable')}" if not current_value else f"❌ {('Disable')}",
                callback_data=callback_data
            ),
        ],
        [
            InlineKeyboardButton(text="🔙 " + ("Back"), callback_data="settings_back"),
        ]
    ])

    # Show setting description with enable/disable options
    text = (
        f"{settings_descriptions_raw[key]}\n\n"
        "**Current status:** {status}"
    ).format(status=f"✅ {('Enabled')}" if current_value else f"❌ {('Disabled')}")
    if isinstance(callback.message, InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(
            callback.from_user.id,
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
            )
    else:
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb
        )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("toggle_") and not c.data.startswith("toggle_service_"))
async def apply_setting_toggle(callback: CallbackQuery):
    data = callback.data
    if not data or not data.startswith("toggle_"):
        logging.error(f"Invalid callback data format, data don't starts with toggle_: {callback.data}")
        await callback.answer(("Invalid setting!"))
        return

    message = callback.message
    if not message:
        return

    # Remove prefix toggle_
    data_without_prefix = data[7:]

    last_underscore_index = data_without_prefix.rfind("_")
    if last_underscore_index == -1:
        logging.error(f"Invalid callback data format: {callback.data}")
        await callback.answer(("Invalid setting!"))
        return

    key = data_without_prefix[:last_underscore_index]
    value_str = data_without_prefix[last_underscore_index + 1:]
    new_value = value_str == "True"
    chat = message.chat

    # Validate that the key is in our allowed settings
    if key not in settings_keys and key != "allow_playlists":
        logging.error(f"Key '{key}' not found in settings_keys: {settings_keys}")
        await callback.answer(("Invalid setting!"))
        return

    try:
        # Update in database
        if chat.type in ("group", "supergroup"):
            await update_chat_settings(chat.id, **{key: new_value})
        else:
            await update_user_settings(callback.from_user.id, **{key: new_value})

        # Show confirmation message
        status_text = ("enabled") if new_value else ("disabled")
        text = ("Setting *{setting}* has been {status}!").format(setting=(key), status=status_text)
        if isinstance(callback.message, InaccessibleMessage) or callback.message is None:
            if callback.bot is None:
                return
            await callback.bot.send_message(
                callback.from_user.id,
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=build_back_keyboard()
                )
        else:
            await callback.message.edit_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=build_back_keyboard()
            )
        await callback.answer(("Setting updated!"))
    except Exception as e:
        logging.error(f"Error updating setting {key}: {e}")
        await callback.answer(("Error updating setting!"))

# Обработчик для управления заблокированными сервисами
# @dp.callback_query(lambda c: c.data == "settings_blocked_services")
# async def blocked_services_menu(callback: CallbackQuery):
#     chat = callback.message.chat

#     # Проверяем права администратора для групп
#     if chat.type in ("group", "supergroup"):
#         is_admin = await check_if_admin_or_owner(callback.bot, chat.id, callback.from_user.id)
#         if not is_admin:
#             await callback.answer(_("You don't have permission to edit these settings!"))
#             return

#     settings = await get_settings_for_chat(chat.id, callback.from_user.id)
#     blocked_services = settings.get("blocked_services", [])

#     # Получаем список всех доступных сервисов
#     available_services = list(SERVICES.keys())

#     # Создаем клавиатуру с сервисами
#     keyboards = []
#     for service in available_services:
#         is_blocked = service in blocked_services
#         icon = "🚫" if is_blocked else "✅"
#         keyboards.append([
#             InlineKeyboardButton(
#                 text=f"{icon} {service}",
#                 callback_data=f"toggle_service_{service}"
#             )
#         ])

#     keyboards.append([InlineKeyboardButton(text="🔙 " + _("Back"), callback_data="settings_back")])

#     kb = InlineKeyboardMarkup(inline_keyboard=keyboards)

#     blocked_count = len(blocked_services)
#     text = _("**Blocked Services Management**\n\nCurrently blocked: {count} services\n\nTap a service to toggle its status.").format(count=blocked_count)

#     await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=kb)
#     await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("toggle_service_"))
async def toggle_service_block(callback: CallbackQuery):
    service_name = callback.data.replace("toggle_service_", "")
    chat = callback.message.chat

    # Проверяем права администратора для групп
    if chat.type in ("group", "supergroup"):
        is_admin = await check_if_admin_or_owner(callback.bot, chat.id, callback.from_user.id)
        if not is_admin:
            await callback.answer(("You don't have permission to edit these settings!"))
            return

    try:
        # Получаем текущие настройки
        if chat.type in ("group", "supergroup"):
            settings_obj = await get_chat_settings(chat.id)
            if not settings_obj:
                await create_chat(chat.id, callback.from_user.id)
                settings_obj = await get_chat_settings(chat.id)
        else:
            settings_obj = await get_user_settings(callback.from_user.id)
            if not settings_obj:
                await create_user(callback.from_user.id)
                settings_obj = await get_user_settings(callback.from_user.id)

        if not settings_obj:
            await callback.answer(("Settings not found!"))
            return

        blocked_services = getattr(settings_obj, 'blocked_services', [])

        # Переключаем статус сервиса
        if service_name in blocked_services:
            blocked_services.remove(service_name)
            status_text = ("unblocked")
        else:
            blocked_services.append(service_name)
            status_text = ("blocked")

        # Обновляем в базе данных
        if chat.type in ("group", "supergroup"):
            await update_chat_settings(chat.id, blocked_services=blocked_services)
        else:
            await update_user_settings(callback.from_user.id, blocked_services=blocked_services)

        # Обновляем интерфейс
        # await blocked_services_menu(callback)
        await callback.answer(("Service {service} {status}!").format(service=service_name, status=status_text))

    except Exception as e:
        logging.error(f"Error toggling service block {service_name}: {e}")
        await callback.answer(("Error updating service status!"))

# Language selection
@dp.callback_query(lambda c: c.data == "settings_lang")
async def settings_lang_menu(callback: CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="English 🇺🇲", callback_data="settings_lang_en"),
            InlineKeyboardButton(text="Русский 🇷🇺", callback_data="settings_lang_ru"),
        ],
        [
            InlineKeyboardButton(text="Українська 🇺🇦", callback_data="settings_lang_uk"),
            InlineKeyboardButton(text="Polski 🇵🇱", callback_data="settings_lang_pl"),
        ],
        [
            InlineKeyboardButton(text="Tiếng Việt 🇻🇳", callback_data="settings_lang_vi"),
            InlineKeyboardButton(text="🔙 " + _("Back"), callback_data="settings_back"),
        ]
    ])
    await callback.message.edit_text(("Pick a language!"), reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("settings_lang_") and c.data != "settings_lang")
async def settings_lang_set(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.removeprefix("settings_lang_")
    chat = callback.message.chat

    # if chat.type == "private":
    #     await update_user_settings(user_id=callback.from_user.id, lang=lang)
    #     # Clear cache for user
    #     custom_i18n.clear_cache(callback.from_user.id)
    # else:
    #     await update_chat_settings(chat_id=chat.id, lang=lang)
    #     # Clear cache for chat
    #     custom_i18n.clear_cache(chat.id)

    await state.clear()

    text = ("Language has been changed to *{language}*!").format(language=lang.upper())
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=build_back_keyboard())
    await callback.answer(("Language updated!"))


# Title language selection
@dp.callback_query(lambda c: c.data == "settings_title_language")
async def settings_title_language_menu(callback: CallbackQuery):
    buttons = []
    for lang in LANGUAGES:
        buttons.append(
            InlineKeyboardButton(
                text=f"{lang['name']} {lang['flag']}",
                callback_data=f"settings_title_lang_{lang['code']}"
            )
        )

    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    kb = InlineKeyboardMarkup(
        inline_keyboard=rows + [[InlineKeyboardButton(text="🔙 " + ("Back"), callback_data="settings_back")]]
    )

    await callback.message.edit_text(("Pick a title language!"), reply_markup=kb)
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("settings_title_lang_") and c.data != "settings_title_language")
async def settings_title_language_set(callback: CallbackQuery):
    lang = callback.data.removeprefix("settings_title_lang_")
    chat = callback.message.chat

    if chat.type == "private":
        await update_user_settings(user_id=callback.from_user.id, title_language=lang)
    else:
        await update_chat_settings(chat_id=chat.id, title_language=lang)

    text = ("Title language has been changed to *{language}*!").format(language=lang.upper())
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=build_back_keyboard())
    await callback.answer(("Title language updated!"))


async def check_if_admin_or_owner(bot: Bot, chat_id: int, user_id: int) -> bool:
    chat_member = await bot.get_chat_member(chat_id, user_id)
    return chat_member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]
