import logging

from aiogram import F
from aiogram.types import Message

from modules.router import service_router as router
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.statistics_helper import log_download_event
from .service import PinterestService

logger = logging.getLogger(__name__)


PINTEREST_REGEX = r"https?://(?:www\.)?(?:pinterest\.com/[\w/-]+|pin\.it/[A-Za-z0-9]+)"

@router.message(F.text.regexp(PINTEREST_REGEX))
async def pinterest_handler(message: Message):
    if not message.text or not message.from_user:
        return

    await task_manager.add_task(message.from_user.id, process_pinterest_url(message), message)


async def process_pinterest_url(message: Message):
    if not message.bot or not message.text:
        return

    user_id = message.from_user.id if message.from_user else message.chat.id

    try:
        media_content = await PinterestService().download(message.text)

        send_manager = MediaSender()
        await send_manager.send(message, media_content, user_id)

        await log_download_event(user_id, 'Pinterest', 'success')

    except Exception as e:
        logger.error(f"Error processing Pinterest URL: {e}")
        raise e
