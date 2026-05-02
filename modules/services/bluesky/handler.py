import logging
from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Config
from models.errors import BotError, ErrorCode
from models.service_list import Services
from senders.media_sender import MediaSender
from storage.db.crud import get_chat_settings
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.statistics_helper import log_download_event
from .service import BlueSkyService
from .utils import get_cache_key, cache_check

bluesky_router = Router(name="bluesky")

logger = logging.getLogger(__name__)

BLUESKY_REGEX = r"https:\/\/bsky\.app\/profile\/[^\/]+\/post\/[a-z0-9]+"

@bluesky_router.message(F.text.regexp(BLUESKY_REGEX))
async def bluesky_handler(message: Message, config: Config, i18n: TranslatorRunner, db_session: AsyncSession):
    user_id = message.from_user.id
    url = message.text.strip()

    async with ChatActionSender.choose_sticker(bot=message.bot, chat_id=message.chat.id):
        send_manager = MediaSender()

        cache_key = get_cache_key(url)
        if not cache_key:
            return

        cached = await cache_check(db_session, cache_key)
        if cached:
            await send_manager.send(message, cached, service="bluesky", db_session=db_session)
            return

        allow_nsfw = True
        if message.chat.id < 0:
            settings = await get_chat_settings(db_session, message.chat.id)
            allow_nsfw = settings.profile.allow_nsfw

    arq = await get_arq_pool('light')
    service = BlueSkyService(arq=arq)

    try:
        async with ChatActionSender.record_video_note(bot=message.bot, chat_id=message.chat.id):
            media_content = await task_manager.run_download(
                user_id=user_id,
                url=url,
                coro=service.download(url, allow_nsfw=allow_nsfw)
            )

        if media_content:
            await send_manager.send(message, media_content, service="bluesky", cache_key=cache_key, db_session=db_session)

    except BotError as e:
        await log_download_event(db_session, user_id, Services.BLUESKY, 'failed_download')
        raise e
    except Exception as e:
        await log_download_event(db_session, user_id, Services.BLUESKY, 'failed_download')
        logger.error(f"Error processing BlueSky URL: {e}")
        raise BotError(
            code=ErrorCode.DOWNLOAD_FAILED,
            message=str(e),
            url=url,
            service=Services.BLUESKY,
            is_logged=True
        )
