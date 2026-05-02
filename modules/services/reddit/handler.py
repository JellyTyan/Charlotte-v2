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
from storage.db.crud import get_chat_settings
from utils.statistics_helper import log_download_event
from .service import RedditService
from .utils import get_cache_key, cache_check

reddit_router = Router(name="reddit")

logger = logging.getLogger(__name__)

REDDIT_REGEX = r"https?:\/\/(?:www\.|old\.|new\.)?reddit\.com\/(?:r\/[A-Za-z0-9_]+\/)?(?:comments\/[A-Za-z0-9]+(?:\/[^\/\s?]+)?|s\/[A-Za-z0-9]+|gallery\/[A-Za-z0-9]+)(?:\/)?"

@reddit_router.message(F.text.regexp(REDDIT_REGEX))
async def reddit_handler(message: Message, db_session: AsyncSession):
    if not message.text or not message.from_user:
        return

    url = message.text
    chat_id = message.chat.id
    user_id = message.from_user.id

    async with ChatActionSender.choose_sticker(bot=message.bot, chat_id=message.chat.id):
        send_manager = MediaSender()
        cache_key = get_cache_key(url)

        cached = await cache_check(db_session, cache_key)
        if cached:
            await send_manager.send(message, cached, service="reddit", db_session=db_session)
            return

        allow_nsfw = True
        if chat_id < 0:
            settings = await get_chat_settings(db_session, chat_id)
            allow_nsfw = settings.profile.allow_nsfw

        arq = await get_arq_pool('light')
        service = RedditService(arq=arq)

    try:
        async with ChatActionSender.record_video_note(bot=message.bot, chat_id=message.chat.id):
            media_content = await task_manager.run_download(
                user_id=user_id,
                url=url,
                coro=service.download(url, allow_nsfw=allow_nsfw)
            )

        if media_content:
            await send_manager.send(message, media_content, service="reddit", cache_key=cache_key, db_session=db_session)

    except BotError as e:
        await log_download_event(db_session, user_id, Services.REDDIT, 'failed_download')
        logger.error(f"Reddit download error: {e}")
        raise e
