"""Стандартные сценарии обработки сообщений"""

from aiogram import Router
from aiogram.types import Message
from typing import Dict, Any
from core.dependencies import get_config, get_logger

router = Router()

@router.message()
async def handle_start(message: Message, **data: Dict[str, Any]):
    config = get_config(data)
    logger = get_logger(data)
    
    logger.info(f"User {message.from_user.id} started bot")
    await message.answer("Привет! Отправь ссылку для скачивания.")