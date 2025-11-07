from modules.router import service_router as router
from aiogram import F
from aiogram.types import Message
import re

YOUTUBE_REGEX = r"https?://(?:www\.)?(?:m\.)?(?:youtu\.be/|youtube\.com/(?:shorts/|watch\?v=))([\w-]+)"

@router.message(F.text.regexp(YOUTUBE_REGEX))
async def youtube_handler(message: Message):
    await message.answer("Youtube")
