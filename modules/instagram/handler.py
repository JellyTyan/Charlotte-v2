import logging

from aiogram import F
from aiogram.types import Message

from modules.router import service_router as router
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.statistics_helper import log_download_event
from .service import InstagramService
from models.service_list import Services

logger = logging.getLogger(__name__)


INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reel|tv)/[\w-]+(?:/\d+)?"

@router.message(F.text.regexp(INSTAGRAM_REGEX))
async def instagram_handler(message: Message):
    if not message.text or not message.from_user:
        return

    await task_manager.add_task(message.from_user.id, process_instagram_url(message), message)


async def process_instagram_url(message: Message):
    if not message.bot or not message.text:
        return

    user_id = message.from_user.id if message.from_user else message.chat.id

    from utils.arq_pool import get_arq_pool

    arq = await get_arq_pool('light')

    try:
        if message.bot:
            await message.bot.send_chat_action(message.chat.id, "choose_sticker")
        # Download content
        media_content = await InstagramService(arq=arq).download(message.text)

        # Send content
        send_manager = MediaSender()
        await send_manager.send(message, media_content, user_id)

        # Log success
        await log_download_event(user_id, Services.INSTAGRAM, 'success')

    except Exception as e:
        logger.error(f"Error processing Instagram URL: {e}")
        # Re-raise to let task manager handle it
        raise e
