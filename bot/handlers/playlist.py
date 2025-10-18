"""Обработка плейлистов"""

from aiogram import Router
from aiogram.types import Message

router = Router()

@router.message()
async def handle_playlist(message: Message):
    # Обработка плейлистов
    pass