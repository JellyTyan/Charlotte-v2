import logging

from aiogram import F
from aiogram.types import Message

from modules.router import service_router as router
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.statistics_helper import log_download_event
from .service import PixivService
from models.service_list import Services

logger = logging.getLogger(__name__)


PIXIV_REGEX = r"https://www\.pixiv\.net/(?:[a-z]{2}/)?artworks/\d+"

@router.message(F.text.regexp(PIXIV_REGEX))
async def pixiv_handler(message: Message):
    if not message.text or not message.from_user:
        return

    await task_manager.add_task(message.from_user.id, process_pixiv_url(message), message)


async def process_pixiv_url(message: Message):
    if not message.bot or not message.text:
        return

    user_id = message.from_user.id if message.from_user else message.chat.id

    try:
        media_content = await PixivService().download(message.text)

        send_manager = MediaSender()
        await send_manager.send(message, media_content, user_id)

        await log_download_event(user_id, Services.PIXIV, 'success')

    except Exception as e:
        logger.error(f"Error processing Pixiv URL: {e}")
        raise e
