import logging

from aiogram import F, Router
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from models.errors import BotError, ErrorCode
from models.service_list import Services
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.statistics_helper import log_download_event
from .service import PixivService
from .utils import get_cache_key, cache_check

pixiv_router = Router(name="pixiv")

logger = logging.getLogger(__name__)


PIXIV_REGEX = r"https://www\.pixiv\.net/(?:[a-z]{2}/)?artworks/\d+"

@pixiv_router.message(F.text.regexp(PIXIV_REGEX))
async def pixiv_handler(message: Message, db_session: AsyncSession):
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id
    url = message.text.strip()
    
    send_manager = MediaSender()
    
    cache_key = get_cache_key(url)
    if not cache_key:
        return

    cached = await cache_check(db_session, cache_key)
    if cached:
        await send_manager.send(message, cached, service="pixiv", db_session=db_session)
        return

    arq = await get_arq_pool('light')
    service = PixivService(arq=arq)

    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "choose_sticker")

    try:
        media_content = await task_manager.run_download(
            user_id=user_id,
            url=url,
            coro=service.download(url)
        )

        if media_content:
            await send_manager.send(message, media_content, service="pixiv", cache_key=cache_key, db_session=db_session)

    except BotError as e:
        await log_download_event(db_session, user_id, Services.PIXIV, 'failed_download')
        raise e
    except Exception as e:
        await log_download_event(db_session, user_id, Services.PIXIV, 'failed_download')
        logger.error(f"Error processing Pixiv URL: {e}")
        raise BotError(
            code=ErrorCode.DOWNLOAD_FAILED,
            message=str(e),
            url=url,
            service=Services.PIXIV,
            is_logged=True
        )
