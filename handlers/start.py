import logging

from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatMemberOwner
from aiogram.utils.i18n import gettext as _
from fluentogram import TranslatorRunner
from storage.db.crud import create_user, create_chat

from core.loader import dp

logger = logging.getLogger(__name__)


@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext, i18n: TranslatorRunner):
    if not message.from_user:
        return
    if message.chat.type == "private":
        await create_user(user_id=message.from_user.id)
    else:
        admins = await message.chat.get_administrators()
        for admin in admins:
            if isinstance(admin, ChatMemberOwner):
                await create_chat(chat_id=message.chat.id, owner_id=admin.user.id)

    await message.answer(i18n.msg.hello(name=message.from_user.first_name),parse_mode=ParseMode.MARKDOWN)
