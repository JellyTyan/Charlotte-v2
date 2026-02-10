import logging

from aiogram import F
from aiogram.types import Message

from models.errors import BotError, ErrorCode
from modules.router import service_router as router
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.statistics_helper import log_download_event
from .service import RedditService
from models.service_list import Services

logger = logging.getLogger(__name__)


REDDIT_REGEX = r"https?:\/\/(?:www\.|old\.|new\.)?reddit\.com\/(?:r\/[A-Za-z0-9_]+\/)?(?:comments\/[A-Za-z0-9]+(?:\/[^\/\s?]+)?|s\/[A-Za-z0-9]+|gallery\/[A-Za-z0-9]+)(?:\/)?(?:\?[^\s]*)?"

@router.message(F.text.regexp(REDDIT_REGEX))
async def reddit_handler(message: Message):
    if not message.text or not message.from_user:
        return

    await task_manager.add_task(message.from_user.id, process_reddit_url(message), message)


async def process_reddit_url(message: Message):
    if not message.bot or not message.text:
        return

    user_id = message.from_user.id if message.from_user else message.chat.id

    # Get ARQ pool
    arq = await get_arq_pool('light')

    # Send chat action for user feedback
    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "choose_sticker")

    try:
        # Pass arq to service
        service = RedditService(arq=arq)

        reddit_info = await service.get_info(message.text)
        if not reddit_info:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                url = message.text,
                service=Services.REDDIT,
                message="Failed to get Reddit post metadata",
                critical=False,
                is_logged=True,
            )

        media_content = await service.download(reddit_info)

        # Send content
        send_manager = MediaSender()
        await send_manager.send(message, media_content, user_id)

        # Log success
        await log_download_event(user_id, Services.REDDIT, 'success')

    except Exception as e:
        logger.error(f"Error processing Reddit URL: {e}")
        raise e
