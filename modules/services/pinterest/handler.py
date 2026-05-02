import logging

from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.ext.asyncio import AsyncSession

from models.errors import BotError
from models.service_list import Services
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.statistics_helper import log_download_event
from .service import PinterestService
from .utils import get_cache_key, cache_check

pinterest_router = Router(name="pinterest")

logger = logging.getLogger(__name__)

PINTEREST_REGEX = r"https?://(?:www\.)?(?:pinterest\.com/[\w/-]+|pin\.it/[A-Za-z0-9]+)"

@pinterest_router.message(F.text.regexp(PINTEREST_REGEX))
async def pinterest_handler(message: Message, db_session: AsyncSession):
    url = message.text
    user_id = message.from_user.id

    async with ChatActionSender.choose_sticker(bot=message.bot, chat_id=message.chat.id):
        send_manager = MediaSender()
        cache_key = get_cache_key(url)

        cached = await cache_check(db_session, cache_key)
        if cached:
            await send_manager.send(message, cached, service="pinterest", db_session=db_session)
            return

    arq = await get_arq_pool('light')
    service = PinterestService(arq=arq)

    try:
        async with ChatActionSender.record_video_note(bot=message.bot, chat_id=message.chat.id):
            media_content = await task_manager.run_download(
                user_id=user_id,
                url=url,
                coro=service.download(url)
            )

        if media_content:
            await send_manager.send(message, media_content, service="pinterest", cache_key=cache_key, db_session=db_session)

    except BotError as e:
        await log_download_event(db_session, user_id, Services.PINTEREST, 'failed_download')
        logger.error(f"Pinterest download error: {e}")
        raise e
