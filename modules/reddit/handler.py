import logging

from aiogram import F
from aiogram.types import Message

from modules.router import service_router as router
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.statistics_helper import log_download_event
from .service import RedditService
from models.service_list import Services

logger = logging.getLogger(__name__)


REDDIT_REGEX = r"https:\/\/www\.reddit\.com\/r\/[A-Za-z0-9_]+\/(?:comments\/[A-Za-z0-9]+(?:\/[^\/\s?]+)?|s\/[A-Za-z0-9]+)(?:\?[^\s]*)?"

@router.message(F.text.regexp(REDDIT_REGEX))
async def reddit_handler(message: Message):
    if not message.text or not message.from_user:
        return

    await task_manager.add_task(message.from_user.id, process_reddit_url(message), message)


async def process_reddit_url(message: Message):
    if not message.bot or not message.text:
        return

    user_id = message.from_user.id if message.from_user else message.chat.id

    try:
        # Download content
        media_content = await RedditService().download(message.text)

        # Send content
        send_manager = MediaSender()
        await send_manager.send(message, media_content, user_id)

        # Log success
        await log_download_event(user_id, Services.REDDIT, 'success')

    except Exception as e:
        logger.error(f"Error processing Reddit URL: {e}")
        # Error handling is usually done by task wrapper or specific exception catches if needed
        raise e
