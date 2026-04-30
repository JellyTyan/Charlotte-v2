from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, Update
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from storage.cache.redis_client import cache_get, cache_delete
from storage.db.crud import create_user, create_chat

from core.loader import dp


@dp.message(CommandStart())
async def start_command(message: Message, command: CommandObject, state: FSMContext, i18n: TranslatorRunner, db_session: AsyncSession):
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
        await create_user(session=db_session, user_id=message.from_user.id)
    else:
        admins = await message.chat.get_administrators()
        owner_id = next((admin.user.id for admin in admins if admin.status == "creator"), message.from_user.id)
        await create_chat(session=db_session, chat_id=message.chat.id, owner_id=owner_id)

    await message.answer(i18n.msg.hello(name=message.from_user.first_name),parse_mode=ParseMode.MARKDOWN)
    return None