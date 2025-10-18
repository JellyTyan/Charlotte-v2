"""Стандартные сценарии обработки сообщений"""

from aiogram import Router
from aiogram.types import Message

router = Router()

@router.message()
async def handle_start(message: Message):
    await message.answer("Привет! Отправь ссылку для скачивания.")