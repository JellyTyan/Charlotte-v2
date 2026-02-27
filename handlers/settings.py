import logging
from typing import Union, Literal
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
from fluentogram import TranslatorRunner

from models.settings import ChatSettingsJson, UserSettingsJson
from models.service_list import Services
from storage.db.crud import update_user_settings, update_chat_settings, get_user_settings, get_chat_settings, create_user, create_chat
from core.loader import dp

logger = logging.getLogger(__name__)

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

DESC_MAPPING = {
    "notifications": "send_notifications",
    "reactions": "send_reactions",
    "allow_playlists": "allow_playlists",
    "raw": "send_raw",
    "caption": "auto_caption",
    "translate_caption": "auto_translate_titles",
    "send_covers": "send_music_covers",
    "lossless": "lossless_mode"
}

def get_desc(key: str, i18n: TranslatorRunner) -> str:
    mapped = str(DESC_MAPPING.get(key, key))
    return i18n.get(f"desc-{mapped.replace('_', '-')}")

async def get_settings_obj(chat_id: int, user_id: int) -> tuple[UserSettingsJson | ChatSettingsJson, bool]:
    is_group = chat_id < 0
    if is_group:
        settings = await get_chat_settings(chat_id)
        if not settings:
            await create_chat(chat_id, user_id)
            settings = await get_chat_settings(chat_id)
        return settings, True
    else:
        settings = await get_user_settings(user_id)
        if not settings:
            await create_user(user_id)
            settings = await get_user_settings(user_id)
        return settings, False

async def save_settings_obj(chat_id: int, user_id: int, settings):
    is_group = chat_id < 0
    if is_group:
        await update_chat_settings(chat_id, settings)
    else:
        await update_user_settings(user_id, settings)


def build_main_keyboard(settings, i18n: TranslatorRunner, is_group: bool = False) -> InlineKeyboardMarkup:
    keyboards = [
        [
            InlineKeyboardButton(text=f"{i18n.btn.language()} →", callback_data="settings_lang"),
            InlineKeyboardButton(text=f"{i18n.btn.title.language()} →", callback_data="settings_title_language"),
        ],
        [
            InlineKeyboardButton(
                text=i18n.btn.notifications(is_enabled='true' if settings.profile.notifications else 'false'),
                callback_data="menu_profile_notifications"
            ),
            InlineKeyboardButton(
                text=i18n.btn.send.reactions(is_enabled='true' if settings.profile.reactions else 'false'),
                callback_data="menu_profile_reactions"
            ),
        ],
        [
            InlineKeyboardButton(text=i18n.btn.configure.services(), callback_data="settings_services")
        ]
    ]

    if is_group:
        keyboards.insert(2, [
            InlineKeyboardButton(
                text=i18n.btn.allow.playlists(is_enabled='true' if settings.profile.allow_playlists else 'false'),
                callback_data="menu_profile_allow_playlists"
            )
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboards)

def build_services_keyboard(i18n: TranslatorRunner) -> InlineKeyboardMarkup:
    buttons = []
    for s in Services:
        buttons.append(InlineKeyboardButton(text=s.value, callback_data=f"settings_svc_{s.value.lower()}"))

    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    rows.append([InlineKeyboardButton(text=f"{i18n.settings.back()}", callback_data="settings_main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def build_service_settings_keyboard(settings, service: str, i18n: TranslatorRunner) -> InlineKeyboardMarkup:
    svc_settings = getattr(settings.services, service)
    keyboards = []

    if hasattr(svc_settings, 'caption'):
        keyboards.append([
            InlineKeyboardButton(
                text=i18n.btn.auto.caption(is_enabled='true' if svc_settings.caption else 'false'),
                callback_data=f"menu_service_{service}_caption"
            ),
            InlineKeyboardButton(
                text=i18n.btn.send.raw(is_enabled='true' if svc_settings.raw else 'false'),
                callback_data=f"menu_service_{service}_raw"
            )
        ])
        keyboards.append([
            InlineKeyboardButton(
                text=i18n.btn.auto.translate(is_enabled='true' if svc_settings.translate_caption else 'false'),
                callback_data=f"menu_service_{service}_translate_caption"
            )
        ])

    if hasattr(svc_settings, 'send_covers'):
        keyboards.append([
            InlineKeyboardButton(
                text=i18n.btn.send.music.covers(is_enabled='true' if svc_settings.send_covers else 'false'),
                callback_data=f"menu_service_{service}_send_covers"
            )
        ])
        keyboards.append([
            InlineKeyboardButton(
                text=i18n.btn.lossless(is_enabled='true' if svc_settings.lossless else 'false'),
                callback_data=f"menu_service_{service}_lossless"
            )
        ])
    if isinstance(settings, ChatSettingsJson) and hasattr(settings.profile, 'blocked_services'):
        keyboards.append([
            InlineKeyboardButton(
                text=i18n.btn.service.enabled(is_enabled='false' if service in settings.profile.blocked_services else 'true'),
                callback_data=f"block_svc_{service}"
            )
        ])

    keyboards.append([InlineKeyboardButton(text=f"{i18n.settings.back()}", callback_data="settings_services")])
    return InlineKeyboardMarkup(inline_keyboard=keyboards)

def build_back_keyboard(i18n: TranslatorRunner, to="settings_main", text=None):
    if not text:
        text = i18n.settings.back()
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=to)]]
    )

async def check_if_admin_or_owner(bot: Bot, chat_id: int, user_id: int) -> bool:
    chat_member = await bot.get_chat_member(chat_id, user_id)
    return chat_member.status in [ChatMemberStatus.CREATOR, ChatMemberStatus.ADMINISTRATOR]

async def safe_edit_text(callback: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup, parse_mode: str = ParseMode.MARKDOWN):
    if isinstance(callback.message, InaccessibleMessage) or callback.message is None:
        if callback.bot is None:
            return
        await callback.bot.send_message(
            callback.from_user.id,
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )
    else:
        await callback.message.edit_text(
            text,
            parse_mode=parse_mode,
            reply_markup=reply_markup
        )

# === Handlers === #

# Main settings
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
        admins = await message.bot.get_chat_administrators(chat.id)
        owner_id = next((admin.user.id for admin in admins if admin.status == "creator"), message.from_user.id)
        await create_chat(chat.id, owner_id)
    else:
        await create_user(message.from_user.id)

    settings, is_group = await get_settings_obj(chat.id, message.from_user.id)
    await message.answer(
        i18n.settings.welcome(),
        reply_markup=build_main_keyboard(settings, i18n, is_group)
    )

# Comeback
@dp.callback_query(lambda c: c.data == "settings_main")
async def settings_main(callback: CallbackQuery, i18n: TranslatorRunner):
    if callback.message is None: return
    settings, is_group = await get_settings_obj(callback.message.chat.id, callback.from_user.id)
    await safe_edit_text(callback, i18n.settings.welcome(), build_main_keyboard(settings, i18n, is_group), ParseMode.HTML)
    await callback.answer()

# Service settings: choosing one
@dp.callback_query(lambda c: c.data == "settings_services")
async def settings_services_menu(callback: CallbackQuery, i18n: TranslatorRunner):
    if callback.message is None: return
    text = i18n.settings.select.service()
    await safe_edit_text(callback, text, build_services_keyboard(i18n))
    await callback.answer()

# Service settings
@dp.callback_query(lambda c: c.data.startswith("settings_svc_"))
async def settings_svc_menu(callback: CallbackQuery, i18n: TranslatorRunner):
    if callback.message is None: return
    if callback.data is None: return
    service = callback.data.replace("settings_svc_", "")
    settings, is_group = await get_settings_obj(callback.message.chat.id, callback.from_user.id)
    name = service.replace("_", " ").title()
    text = i18n.settings.service.title(name=name)
    await safe_edit_text(callback, text, build_service_settings_keyboard(settings, service, i18n))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("menu_profile_"))
async def menu_profile_setting(callback: CallbackQuery, i18n: TranslatorRunner):
    if callback.message is None: return
    if callback.data is None: return
    key = callback.data.replace("menu_profile_", "")
    settings, is_group = await get_settings_obj(callback.message.chat.id, callback.from_user.id)
    current_value = getattr(settings.profile, key)

    new_value = not current_value
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"✅ {i18n.get('enable')}" if not current_value else f"❌ {i18n.get('disable')}",
                callback_data=f"toggle_profile_{key}_{new_value}"
            ),
        ],
        [InlineKeyboardButton(text=f"{i18n.get('back')}", callback_data="settings_main")]
    ])

    description = get_desc(key, i18n)
    status_word = i18n.get('enabled') if current_value else i18n.get('disabled')
    status_text = i18n.get('current-status', status=status_word)
    text = f"{description}\n\n{status_text}"

    await safe_edit_text(callback, text, kb)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("menu_service_"))
async def menu_service_setting(callback: CallbackQuery, i18n: TranslatorRunner):
    if callback.message is None or callback.data is None: return
    parts = callback.data.replace("menu_service_", "").split("_")

    service_map = {s.value.lower(): s.value.lower() for s in Services}
    target_service = None
    for svc_name in service_map:
        if callback.data.startswith(f"menu_service_{svc_name}_"):
            target_service = svc_name
            break
    if not target_service: return

    key = callback.data.replace(f"menu_service_{target_service}_", "")
    settings, is_group = await get_settings_obj(callback.message.chat.id, callback.from_user.id)

    svc_settings = getattr(settings.services, target_service)
    current_value = getattr(svc_settings, key)
    new_value = not current_value

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text=f"✅ {i18n.get('enable')}" if not current_value else f"❌ {i18n.get('disable')}",
                callback_data=f"toggle_service_{target_service}_{key}_{new_value}"
            ),
        ],
        [InlineKeyboardButton(text=f"{i18n.get('back')}", callback_data=f"settings_svc_{target_service}")]
    ])

    description = get_desc(key, i18n)
    status_word = i18n.get('enabled') if current_value else i18n.get('disabled')
    status_text = i18n.get('current-status', status=status_word)
    title = i18n.settings.service.title(name=target_service.replace('_', ' ').title())
    text = f"{title}\n\n{description}\n\n{status_text}"

    await safe_edit_text(callback, text, kb)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("block_svc_"))
async def menu_service_block(callback: CallbackQuery, i18n: TranslatorRunner):
    if callback.message is None or callback.data is None: return

    service = callback.data.replace("block_svc_", "")
    
    settings, is_group = await get_settings_obj(callback.message.chat.id, callback.from_user.id)
    if not isinstance(settings, ChatSettingsJson): 
        logger.error(f"Not a chat settings: {type(settings)}")
        return

    logger.info(f"Before toggle - blocked_services: {settings.profile.blocked_services}, target: {service}")
    if service in settings.profile.blocked_services:
        settings.profile.blocked_services.remove(service)
    else:
        settings.profile.blocked_services.add(service)
    logger.info(f"After toggle - blocked_services: {settings.profile.blocked_services}")
    
    await save_settings_obj(callback.message.chat.id, callback.from_user.id, settings)

    name = service.replace("_", " ").title()
    text = i18n.settings.service.title(name=name)

    await safe_edit_text(callback, text, build_service_settings_keyboard(settings, service, i18n))
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("toggle_profile_"))
async def apply_profile_setting(callback: CallbackQuery, i18n: TranslatorRunner):
    if callback.message is None or callback.data is None: return
    data = callback.data.replace("toggle_profile_", "")
    last_uscores = data.rfind("_")
    key = data[:last_uscores]
    new_value = data[last_uscores+1:] == "True"

    chat_id = callback.message.chat.id
    settings, is_group = await get_settings_obj(chat_id, callback.from_user.id)
    setattr(settings.profile, key, new_value)
    await save_settings_obj(chat_id, callback.from_user.id, settings)

    status_text = i18n.get('enabled') if new_value else i18n.get('disabled')
    text = i18n.get('setting-changed', setting=key.replace('_', ' '), status=status_text)
    await safe_edit_text(callback, text, build_back_keyboard(i18n, "settings_main"))
    await callback.answer(i18n.get('setting-updated'))

@dp.callback_query(lambda c: c.data.startswith("toggle_service_"))
async def apply_service_setting(callback: CallbackQuery, i18n: TranslatorRunner):
    if callback.message is None or callback.data is None: return

    service_map = {s.value.lower(): s.value.lower() for s in Services}
    target_service = None
    for svc_name in service_map:
        if callback.data.startswith(f"toggle_service_{svc_name}_"):
            target_service = svc_name
            break
    if not target_service: return

    data = callback.data.replace(f"toggle_service_{target_service}_", "")
    last_uscores = data.rfind("_")
    key = data[:last_uscores]
    new_value = data[last_uscores+1:] == "True"

    chat_id = callback.message.chat.id
    settings, is_group = await get_settings_obj(chat_id, callback.from_user.id)
    svc_settings = getattr(settings.services, target_service)
    setattr(svc_settings, key, new_value)
    await save_settings_obj(chat_id, callback.from_user.id, settings)

    status_text = i18n.get('enabled') if new_value else i18n.get('disabled')
    text = i18n.get('setting-changed', setting=key.replace('_', ' '), status=status_text)
    await safe_edit_text(callback, text, build_back_keyboard(i18n, f"settings_svc_{target_service}"))
    await callback.answer(i18n.get('setting-updated'))


@dp.callback_query(lambda c: c.data == "settings_lang")
async def settings_lang_menu(callback: CallbackQuery, i18n: TranslatorRunner):
    if callback.message is None: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="English 🇺🇲", callback_data="settings_lang_set_en"),
            InlineKeyboardButton(text="Русский 🇷🇺", callback_data="settings_lang_set_ru"),
        ],
        [
            InlineKeyboardButton(text="Українська 🇺🇦", callback_data="settings_lang_set_uk"),
            InlineKeyboardButton(text="Беларуская 🇧🇾", callback_data="settings_lang_set_be"),
        ],
        [
            InlineKeyboardButton(text="Čeština 🇨🇿", callback_data="settings_lang_set_cs"),
            InlineKeyboardButton(text="Polski 🇵🇱", callback_data="settings_lang_set_pl"),
        ],
        [
            InlineKeyboardButton(text="Deutsch 🇩🇪", callback_data="settings_lang_set_de"),
            InlineKeyboardButton(text="Español 🇪🇸", callback_data="settings_lang_set_es"),
        ],
        [
            InlineKeyboardButton(text="فارسی 🇮🇷", callback_data="settings_lang_set_fa"),
        ],
        [
            InlineKeyboardButton(text=f"{i18n.get('back')}", callback_data="settings_main"),
        ]
    ])
    text = i18n.get('pick-language')
    await safe_edit_text(callback, text, kb)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("settings_lang_set_"))
async def settings_lang_set(callback: CallbackQuery, state: FSMContext, i18n: TranslatorRunner):
    if callback.message is None or callback.data is None: return
    lang = callback.data.replace("settings_lang_set_", "")
    settings, is_group = await get_settings_obj(callback.message.chat.id, callback.from_user.id)
    settings.profile.language = lang
    await save_settings_obj(callback.message.chat.id, callback.from_user.id, settings)

    await state.clear()
    text = i18n.get('language-changed', language=lang.upper())
    await safe_edit_text(callback, text, build_back_keyboard(i18n, "settings_main"))
    await callback.answer(i18n.get('language-updated'))


@dp.callback_query(lambda c: c.data == "settings_title_language")
async def settings_title_language_menu(callback: CallbackQuery, i18n: TranslatorRunner):
    if callback.message is None: return
    buttons = []
    for lang in LANGUAGES:
        buttons.append(
            InlineKeyboardButton(
                text=f"{lang['name']} {lang['flag']}",
                callback_data=f"settings_title_lang_set_{lang['code']}"
            )
        )

    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    kb = InlineKeyboardMarkup(
        inline_keyboard=rows + [[InlineKeyboardButton(text=f"{i18n.get('back')}", callback_data="settings_main")]]
    )

    await safe_edit_text(callback, i18n.get('pick-title-language'), kb)
    await callback.answer()

@dp.callback_query(lambda c: c.data.startswith("settings_title_lang_set_"))
async def settings_title_language_set(callback: CallbackQuery, i18n: TranslatorRunner):
    if callback.message is None or callback.data is None: return
    lang = callback.data.replace("settings_title_lang_set_", "")

    settings, is_group = await get_settings_obj(callback.message.chat.id, callback.from_user.id)

    if hasattr(settings.profile, 'title_language'):
        settings.profile.title_language = lang

    await save_settings_obj(callback.message.chat.id, callback.from_user.id, settings)

    text = i18n.get('title-language-changed', language=lang.upper())
    await safe_edit_text(callback, text, build_back_keyboard(i18n, "settings_main"))
    await callback.answer(i18n.get('title-language-updated'))
