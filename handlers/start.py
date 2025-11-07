import logging

from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ChatMemberOwner
from aiogram.utils.i18n import gettext as _

from core.loader import dp

logger = logging.getLogger(__name__)


@dp.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    # if message.chat.type == "private":
    #     await create_user(user_id=message.from_user.id)
    # else:
    #     admins = await message.chat.get_administrators()
    #     for admin in admins:
    #         if isinstance(admin, ChatMemberOwner):
    #             await create_chat(chat_id=message.chat.id, owner_id=admin.user.id)

    await message.answer(
            "Henlooooooooooooooooooooooooooooooooooooooooooooooo\n\n"
            "Nice to meet you, {name}!\n\n"
            "I'm Charlotte - my hobby is pirating content from various resources.\n\n"
            "Use _/help_ for more info on me, commands and everything!\n\n"
            "P.S.: There is Charlotte Basement, where is posted new updates or service status @charlottesbasement 🧡",
        parse_mode=ParseMode.MARKDOWN,
    )
