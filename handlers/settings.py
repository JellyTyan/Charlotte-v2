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
import logging
from fluentogram import TranslatorRunner

from storage.db.crud import update_user_settings, update_chat_settings, get_user_settings, get_chat_settings, create_user, create_chat
from core.loader import dp
# from utils.register_services import SERVICES


settings_keys = [
    "send_raw", "send_music_covers", "send_reactions", "send_notifications",
    "auto_caption", "auto_translate_titles",
]

chat_only_settings = [
    "allow_playlists", "blocked_services"
]

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

def build_main_keyboard(settings: dict, i18n: TranslatorRunner, is_group: bool = False) -> InlineKeyboardMarkup:
    # Добавляем настройки только для групп
    keyboards = [
        [
            InlineKeyboardButton(
                text=f"{i18n.btn.language()} →",
                callback_data="settings_lang"
            ),
            InlineKeyboardButton(
                text=i18n.btn.send.raw(is_enabled='true' if settings['send_raw'] else 'false'),
                callback_data="settings_send_raw"
            ),
        ],
        [
            InlineKeyboardButton(
                text=i18n.btn.send.music.covers(is_enabled='true' if settings['send_music_covers'] else 'false'),
                callback_data="settings_send_music_covers"
            ),
            InlineKeyboardButton(
                text=i18n.btn.send.reactions(is_enabled='true' if settings['send_reactions'] else 'false'),
                callback_data="settings_send_reactions"
            ),
        ],
        [
            InlineKeyboardButton(
                text=i18n.btn.auto.caption(is_enabled='true' if settings['auto_caption'] else 'false'),
                callback_data="settings_auto_caption"
            ),
            InlineKeyboardButton(
                text=i18n.btn.notifications(is_enabled='true' if settings['send_notifications'] else 'false'),
                callback_data="settings_send_notifications"
            ),
        ],
        [
            InlineKeyboardButton(
                text=i18n.btn.auto.translate(is_enabled='true' if settings['auto_translate_titles'] else 'false'),
                callback_data="settings_auto_translate_titles"
            ),
            InlineKeyboardButton(
                text=f"{i18n.btn.title.language()} →",
                callback_data="settings_title_language"
            ),
        ],
    ]
    if is_group:
        keyboards.append([
            InlineKeyboardButton(
                text=i18n.btn.allow.playlists(is_enabled='true' if settings['allow_playlists'] else 'false'),
                callback_data="settings_allow_playlists"
            ),
            InlineKeyboardButton(
                text=i18n.btn.blocked.services(),
                callback_data="settings_blocked_services"
            ),
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboards)

def build_back_keyboard(i18n: TranslatorRunner):
    """Back button - used within handlers when i18n context is already available"""
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=i18n.settings.back(), callback_data="settings_back")]]
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
async def settings_command(message: Message, i18n: TranslatorRunner) -> None:
    chat = message.chat
    if message.bot is None or message.from_user is None:
        return
    if chat.type in ("group", "supergroup"):
        is_admin = await check_if_admin_or_owner(message.bot, chat.id, message.from_user.id)
        if not is_admin:
            await message.answer(i18n.settings.no.permission())
            return

    settings = await get_settings_for_chat(chat.id, message.from_user.id)
    is_group = chat.type in ("group", "supergroup")

    await message.answer(
        i18n.settings.welcome(),
        reply_markup=build_main_keyboard(settings, i18n, is_group)
    )


@dp.callback_query(lambda c: c.data == "settings_back")
async def settings_back(callback: CallbackQuery, i18n: TranslatorRunner):
    if callback.message is None:
        return
    settings = await get_settings_for_chat(callback.message.chat.id, callback.from_user.id)
    is_group = callback.message.chat.type in ("group", "supergroup")
    text = i18n.settings.welcome()
    if isinstance(callback.message, InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(
            callback.from_user.id,
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=build_main_keyboard(settings, i18n, is_group)
            )
    else:
        await callback.message.edit_text(
            text,
            parse_mode=ParseMode.HTML,
            reply_markup=build_main_keyboard(settings, i18n, is_group)
        )
    await callback.answer()


@dp.callback_query(lambda c: c.data.startswith("settings_") and c.data in [f"settings_{k}" for k in settings_keys + ["allow_playlists"]])
async def toggle_setting(callback: CallbackQuery, i18n: TranslatorRunner):
    data = callback.data
    message = callback.message
    if not data or not message:
        return
    key = data.split("_", 1)[1]
    chat = message.chat

    # Check if the setting is available for this chat type
    if chat.type in ("group", "supergroup"):
        if key not in settings_keys and key != "allow_playlists":
            await callback.answer(i18n.settings.no.allowed.groups())
            return
    else:
        if key not in settings_keys:
            await callback.answer(i18n.settings.no.allowed.dm())
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
    description = i18n.get(f"desc-{key.replace('_', '-')}")

    # Статус
    status_text = i18n.setting.status.changed(
        setting_name=key,
        is_enabled='true' if new_value else 'false'
    )
    text = f"{description}\n\n{status_text}"
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
async def apply_setting_toggle(callback: CallbackQuery, i18n: TranslatorRunner):
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
                reply_markup=build_back_keyboard(i18n)
                )
        else:
            await callback.message.edit_text(
                text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=build_back_keyboard(i18n)
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
    data = callback.data
    if not data:
        return
    service_name = data.replace("toggle_service_", "")
    message = callback.message
    if not message:
        return
    chat = message.chat

    # Проверяем права администратора для групп
    if chat.type in ("group", "supergroup"):
        bot = callback.bot
        if not bot:
            return
        is_admin = await check_if_admin_or_owner(bot, chat.id, callback.from_user.id)
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
            InlineKeyboardButton(text="🔙 " + ("Back"), callback_data="settings_back"),
        ]
    ])
    text = "Pick a language!"
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


@dp.callback_query(lambda c: c.data.startswith("settings_lang_") and c.data != "settings_lang")
async def settings_lang_set(callback: CallbackQuery, state: FSMContext, i18n: TranslatorRunner):
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
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=build_back_keyboard(i18n))
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
async def settings_title_language_set(callback: CallbackQuery, i18n: TranslatorRunner):
    lang = callback.data.removeprefix("settings_title_lang_")
    chat = callback.message.chat

    if chat.type == "private":
        await update_user_settings(user_id=callback.from_user.id, title_language=lang)
    else:
        await update_chat_settings(chat_id=chat.id, title_language=lang)

    text = ("Title language has been changed to *{language}*!").format(language=lang.upper())
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=build_back_keyboard(i18n))
    await callback.answer(("Title language updated!"))


async def check_if_admin_or_owner(bot: Bot, chat_id: int, user_id: int) -> bool:
    chat_member = await bot.get_chat_member(chat_id, user_id)
    return chat_member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]
