from aiogram import types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from fluentogram import TranslatorRunner
from tasks.task_manager import task_manager

from aiogram import Router
router = Router()

@router.message(Command("cancel"))
async def cancel_command(message: types.Message, state: FSMContext, i18n: TranslatorRunner) -> None:
    user = message.from_user
    if user is None:
        return

    task_manager.cancel_user(user.id)