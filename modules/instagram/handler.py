import logging

from aiogram import F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from models.errors import BotError, ErrorCode
from models.service_list import Services
from modules.router import service_router as router
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.statistics_helper import log_download_event
from .service import InstagramService
from .utils import get_cache_key, cache_check

logger = logging.getLogger(__name__)

INSTAGRAM_REGEX = r"https?://(?:www\.)?instagram\.com/(?:p|reels?|tv)/[\w-]+/?"

@router.message(F.text.regexp(INSTAGRAM_REGEX))
async def instagram_handler(message: Message, db_session: AsyncSession):
    url = message.text
    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.bot:
        await message.bot.send_chat_action(chat_id, "choose_sticker")

    send_manager = MediaSender()
    cache_key = get_cache_key(url)
    
    cached = await cache_check(db_session, cache_key)
    if cached:
        await send_manager.send(message, cached, service="instagram", db_session=db_session)
        return

    arq = await get_arq_pool('light')
    service = InstagramService(arq=arq)

    try:
        media_content = await task_manager.run_download(
            user_id=user_id,
            url=url,
            coro=service.download(url)
        )

        if media_content:
            await send_manager.send(message, media_content, service="instagram", cache_key=cache_key, db_session=db_session)

    except BotError as e:
        await log_download_event(db_session, user_id, Services.INSTAGRAM, 'failed_download')
        logger.error(f"Instagram download error: {e}")
        raise e
    except Exception as e:
        await log_download_event(db_session, user_id, Services.INSTAGRAM, 'failed_download')
