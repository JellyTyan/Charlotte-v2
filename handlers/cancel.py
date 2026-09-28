import httpx
from aiogram import types, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from fluentogram import TranslatorRunner
from tasks.task_manager import task_manager

router = Router()

@router.message(Command("cancel"))
async def cancel_command(
    message: types.Message,
    state: FSMContext,
    i18n: TranslatorRunner,
    http_client: httpx.AsyncClient = None,
) -> None:
    user = message.from_user
    if user is None:
        return

    await task_manager.cancel_user(user.id, http_client)
    await state.clear()

    from utils.ephemeral import send_smart_message
    await send_smart_message(message, i18n.get("action-cancelled"), for_user_id=user.id)