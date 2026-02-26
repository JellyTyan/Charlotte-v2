import logging

from aiogram import F
from aiogram.types import Message

from modules.router import service_router as router
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.statistics_helper import log_download_event
from models.service_list import Services

logger = logging.getLogger(__name__)


PINTEREST_REGEX = r"https?://(?:www\.)?(?:pinterest\.com/[\w/-]+|pin\.it/[A-Za-z0-9]+)"

@router.message(F.text.regexp(PINTEREST_REGEX))
async def pinterest_handler(message: Message):
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id

    # Start download task
    download_task = await task_manager.add_task(
        user_id,
        download_coro=process_pinterest_url(message),
        message=message
    )

    # When download completes, queue send task
    if download_task:
        async def send_when_ready():
            try:
                media_content = await download_task
                if media_content:
                    send_manager = MediaSender()
                    await send_manager.send(message, media_content, user_id, service="pinterest")
            except Exception as e:
                # Error already logged in download task
                pass

        await task_manager.add_send_task(user_id, send_when_ready())


async def process_pinterest_url(message: Message):
    """Download Pinterest media and return content"""
    if not message.bot or not message.text:
        return None

    user_id = message.from_user.id if message.from_user else message.chat.id

    from utils.arq_pool import get_arq_pool
    from .service import PinterestService

    # Initialize ARQ pool
    arq = await get_arq_pool('light')

    try:
        # Send chat action for visual feedback
        if message.bot:
            await message.bot.send_chat_action(message.chat.id, "choose_sticker")

        # Download content
        service = PinterestService(arq=arq)
        media_content = await service.download(message.text)

        # Log success
        await log_download_event(user_id, Services.PINTEREST, 'success')

        return media_content

    except Exception as e:
        logger.error(f"Error processing Pinterest URL: {e}")
        # Re-raise to let task manager handle it
        raise e
