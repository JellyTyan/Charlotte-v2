import logging

from aiogram import F
from aiogram.types import Message

from modules.router import service_router as router
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.statistics_helper import log_download_event
from .service import TiktokService
from models.service_list import Services
from models.errors import BotError, ErrorCode

logger = logging.getLogger(__name__)


TIKTOK_REGEX = r"https?://(?:www\.)?(?:tiktok\.com/.*|(vm|vt)\.tiktok\.com/.+)"

@router.message(F.text.regexp(TIKTOK_REGEX))
async def tiktok_handler(message: Message):
    if not message.text or not message.from_user:
        return

    await task_manager.add_task(message.from_user.id, process_tiktok_url(message), message)


async def process_tiktok_url(message: Message):
    if not message.bot or not message.text:
        return

    user_id = message.from_user.id if message.from_user else message.chat.id

    try:
        service = TiktokService()

        # Get metadata
        metadata = await service.get_info(message.text)
        if not metadata:
             raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Failed to fetch metadata",
                url=message.text,
                service=Services.TIKTOK,
                is_logged=True,
                critical=True
            )

        # Download content using metadata
        media_content = await service.download(metadata)

        # Send content
        send_manager = MediaSender()
        await send_manager.send(message, media_content, user_id)

        # Log success
        await log_download_event(user_id, Services.TIKTOK, 'success')

    except Exception as e:
        # Error handling is usually done by task wrapper or specific exception catches if needed
        raise e
