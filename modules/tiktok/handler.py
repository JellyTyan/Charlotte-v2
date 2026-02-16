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
from utils.arq_pool import get_arq_pool

logger = logging.getLogger(__name__)


TIKTOK_REGEX = r"https?://(?:www\.)?(?:tiktok\.com/.*|(vm|vt)\.tiktok\.com/.+)"

@router.message(F.text.regexp(TIKTOK_REGEX))
async def tiktok_handler(message: Message):
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id

    # Start download task
    download_task = await task_manager.add_task(
        user_id,
        download_coro=process_tiktok_url(message),
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


async def process_tiktok_url(message: Message):
    """Download TikTok media and return content"""
    if not message.bot or not message.text:
        return None

    user_id = message.from_user.id if message.from_user else message.chat.id

    arq = await get_arq_pool('light')

    service = TiktokService(arq=arq)

    # Send chat action for user feedback
    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "choose_sticker")

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

    # Log success
    await log_download_event(user_id, Services.TIKTOK, 'success')

    return media_content
