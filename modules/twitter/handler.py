from aiogram import F
from aiogram.types import Message
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from core.config import Config
from models.errors import BotError
from models.service_list import Services
from modules.router import service_router as router
from senders.media_sender import MediaSender
from storage.db.crud import get_user, get_chat_settings
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.statistics_helper import log_download_event
from .service import TwitterService
from .utils import get_cache_key, cache_check

logger = logging.getLogger(__name__)

TWITTER_REGEX = r"https://(?:twitter|x)\.com/\w+/status/\d+"

@router.message(F.text.regexp(TWITTER_REGEX))
async def twitter_handler(message: Message, config: Config, i18n: TranslatorRunner, db_session: AsyncSession):
    if not message.text or not message.from_user:
        return

    url = message.text.strip()
    chat_id = message.chat.id
    user_id = message.from_user.id

    if message.bot:
        await message.bot.send_chat_action(chat_id, "choose_sticker")

    send_manager = MediaSender()
    cache_key = get_cache_key(url)

    cached = await cache_check(db_session, cache_key)
    if cached:
        await send_manager.send(message, cached, service="twitter", db_session=db_session)
        return

    allow_nsfw = True
    if chat_id < 0:
        settings = await get_chat_settings(db_session, chat_id)
        allow_nsfw = settings.profile.allow_nsfw

    user = await get_user(db_session, user_id)
    is_premium = user.is_premium if user else False

    arq = await get_arq_pool('light')
    service = TwitterService(arq=arq)

    if is_premium:
        coro = service.download(url, premium=True, config=config, allow_nsfw=allow_nsfw)
    else:
        coro = service.download(url, allow_nsfw=allow_nsfw)

    try:
        media_content = await task_manager.run_download(
            user_id=user_id,
            url=url,
            coro=coro
        )

        if media_content:
            await send_manager.send(message, media_content, service="twitter", cache_key=cache_key, db_session=db_session)

    except BotError as e:
        await log_download_event(db_session, user_id, Services.TWITTER, 'failed_download')
        logger.error(f"Twitter download error: {e}")
        raise e
