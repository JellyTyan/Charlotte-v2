from aiogram import types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.i18n import gettext as _
from fluentogram import TranslatorRunner

from core.loader import dp


@dp.message(Command("help"))
async def help_command(message: types.Message, state: FSMContext, i18n: TranslatorRunner) -> None:
    user = message.from_user
    if user is None:
        return

    await message.reply(i18n.msg.help(), parse_mode=ParseMode.HTML)
