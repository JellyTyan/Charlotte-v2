from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, Update
from aiogram.utils.keyboard import InlineKeyboardBuilder
from fluentogram import TranslatorHub, TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from storage.cache.redis_client import cache_get, cache_delete
from storage.db.crud import create_user, create_chat, get_user_settings, update_user_settings

from core.loader import dp
from aiogram import Router

router = Router()

SUPPORTED_LANGS = {"be", "cs", "de", "en", "es", "fa", "pl", "ru", "uk"}


def _resolve_lang(language_code: str | None) -> str:
    if not language_code:
        return "en"
    lang = language_code.split("-")[0].lower()
    return lang if lang in SUPPORTED_LANGS else "en"


@router.message(CommandStart())
async def start_command(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    i18n: TranslatorRunner,
    db_session: AsyncSession,
    _translator_hub: TranslatorHub,
):
    if not message.from_user:
        return None

    if command.args:
        url_hash = command.args

        cached_data = await cache_get(f"inline_url:{url_hash}")
        url = cached_data.get('url') if cached_data else None

        if not url:
            return await message.answer(i18n.inline.url.expired())

        await cache_delete(f"inline_url:{url_hash}")

        await message.answer(i18n.inline.url.received(url=url))

        new_message = message.model_copy(update={"text": url, "entities": None})

        await dp.feed_update(message.bot, Update(update_id=0, message=new_message))
        return None

    if message.chat.type == "private":
        _, is_new = await create_user(session=db_session, user_id=message.from_user.id)

        if is_new:
            lang = _resolve_lang(message.from_user.language_code)
            if lang != "en":
                settings = await get_user_settings(session=db_session, user_id=message.from_user.id)
                settings.profile.language = lang
                await update_user_settings(session=db_session, user_id=message.from_user.id, settings=settings)
                i18n = _translator_hub.get_translator_by_locale(lang)

        bot = await message.bot.me()

        builder = InlineKeyboardBuilder()
        builder.button(
            text=i18n.btn.add.group(),
            url=f"https://t.me/{bot.username}?startgroup=true",
        )
        builder.button(
            text=i18n.btn.my.settings(),
            callback_data="settings_main",
        )
        builder.adjust(1)

        await message.answer(
            i18n.msg.hello(name=message.from_user.first_name),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=builder.as_markup()
        )
    else:
        admins = await message.chat.get_administrators()
        owner_id = next((admin.user.id for admin in admins if admin.status == "creator"), message.from_user.id)
        await create_chat(session=db_session, chat_id=message.chat.id, owner_id=owner_id)

        await message.answer(
            i18n.msg.hello(name=message.from_user.first_name),
            parse_mode=ParseMode.MARKDOWN,
        )
    return None