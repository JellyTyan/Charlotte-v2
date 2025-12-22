from aiogram import types
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from fluentogram import TranslatorRunner
from tasks.task_manager import task_manager

from core.loader import dp


@dp.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext, i18n: TranslatorRunner) -> None:
    user = message.from_user
    if user is None:
        return

    canceled = await task_manager.cancel_user_tasks(user.id)
    if canceled:
        await message.answer(i18n.get("download-cancel"))
    else:
        await message.answer(i18n.get("download-no-found"))
