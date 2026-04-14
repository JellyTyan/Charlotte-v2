from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession
from storage.db.crud import create_user, create_chat

from core.loader import dp


@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext, i18n: TranslatorRunner, db_session: AsyncSession):
    if not message.from_user:
        return
    if message.chat.type == "private":
        await create_user(session=db_session, user_id=message.from_user.id)
    else:
        admins = await message.chat.get_administrators()
        owner_id = next((admin.user.id for admin in admins if admin.status == "creator"), message.from_user.id)
        await create_chat(session=db_session, chat_id=message.chat.id, owner_id=owner_id)

    await message.answer(i18n.msg.hello(name=message.from_user.first_name),parse_mode=ParseMode.MARKDOWN)
