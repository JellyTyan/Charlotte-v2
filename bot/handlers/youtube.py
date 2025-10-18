"""Интерактивные сценарии для YouTube (выбор качества)"""

from aiogram import Router
from aiogram.types import Message, CallbackQuery

router = Router()

@router.message()
async def handle_youtube_link(message: Message):
    # Обработка YouTube ссылок
    pass

@router.callback_query()
async def handle_quality_selection(callback: CallbackQuery):
    # Обработка выбора качества
    pass