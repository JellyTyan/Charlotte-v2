import logging

from aiogram import F
from aiogram.types import Message

from modules.router import service_router as router
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.statistics_helper import log_download_event
from .service import PixivService
from models.service_list import Services

logger = logging.getLogger(__name__)


PIXIV_REGEX = r"https://www\.pixiv\.net/(?:[a-z]{2}/)?artworks/\d+"

@router.message(F.text.regexp(PIXIV_REGEX))
async def pixiv_handler(message: Message):
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id

    # Start download task
    download_task = await task_manager.add_task(
        user_id,
        download_coro=process_pixiv_url(message),
        message=message
    )

    # When download completes, queue send task
    if download_task:
        async def send_when_ready():
            try:
                media_content = await download_task
                if media_content:
                    send_manager = MediaSender()
                    await send_manager.send(message, media_content, user_id)
            except Exception as e:
                # Error already logged in download task
                pass

        await task_manager.add_send_task(user_id, send_when_ready())


async def process_pixiv_url(message: Message):
    """Download Pixiv media and return content"""
    if not message.bot or not message.text:
        return None

    user_id = message.from_user.id if message.from_user else message.chat.id

    # Get ARQ pool
    arq = await get_arq_pool('light')

    # Send chat action for user feedback
    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "choose_sticker")

    try:
        # Pass arq to service
        service = PixivService(arq=arq)
        media_content = await service.download(message.text)

        await log_download_event(user_id, Services.PIXIV, 'success')

        return media_content

    except Exception as e:
        logger.error(f"Error processing Pixiv URL: {e}")
        raise e
