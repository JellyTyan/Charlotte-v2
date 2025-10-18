"""Универсальный отправитель сообщений"""

from aiogram import Bot
from aiogram.types import Message
from typing import Union

class MessageSender:
    def __init__(self, bot: Bot):
        self.bot = bot
    
    async def send_message(self, chat_id: int, text: str) -> Message:
        """Отправка текстового сообщения"""
        return await self.bot.send_message(chat_id, text)
    
    async def send_document(self, chat_id: int, document: Union[str, bytes]) -> Message:
        """Отправка документа"""
        return await self.bot.send_document(chat_id, document)