from aiogram import types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from fluentogram import TranslatorRunner
from utils.ephemeral import send_smart_message

from aiogram import Router
router = Router()

@router.message(Command("help"))
async def help_command(message: types.Message, state: FSMContext, i18n: TranslatorRunner) -> None:
    user = message.from_user
    if user is None:
        return

    bot_info = await message.bot.get_me()
    bot_username = bot_info.username or "CharlotteFox_Bot"

    await send_smart_message(
        message,
        i18n.msg.help(bot_username=bot_username),
        for_user_id=user.id,
        parse_mode=ParseMode.HTML,
    )
