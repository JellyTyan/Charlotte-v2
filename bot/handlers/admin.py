"""Админ-команды"""

from aiogram import Router
from aiogram.types import Message

router = Router()

@router.message()
async def handle_admin_commands(message: Message):
    # Админ команды
    pass