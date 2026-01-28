import logging

from aiogram import F
from aiogram.types import Message

from modules.router import service_router as router
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.statistics_helper import log_download_event
from .service import TwitterService
from models.service_list import Services
from core.config import Config
from fluentogram import TranslatorRunner

logger = logging.getLogger(__name__)


TWITTER_REGEX = r"https://(?:twitter|x)\.com/\w+/status/\d+"

@router.message(F.text.regexp(TWITTER_REGEX))
async def twitter_handler(message: Message, config: Config, i18n: TranslatorRunner):
    if not message.text or not message.from_user:
        return

    await task_manager.add_task(message.from_user.id, process_twitter_url(message, config, i18n), message, message.text)


async def process_twitter_url(message: Message, config: Config, i18n: TranslatorRunner):
    if not message.bot or not message.text:
        return

    user_id = message.from_user.id if message.from_user else message.chat.id
    url = message.text.strip()

    try:
        # Download content
        from storage.db.crud import get_user
        user = await get_user(user_id)
        is_premium = user.is_premium if user else False
        
        if is_premium:
            media_content = await TwitterService().download(url, premium=True, config=config)
        else:
            media_content = await TwitterService().download(url)

        # Send content
        send_manager = MediaSender()
        await send_manager.send(message, media_content, user_id)

        # Log success
        await log_download_event(user_id, Services.TWITTER, 'success')

    except Exception as e:
        # Error handling is usually done by task wrapper or specific exception catches if needed
        raise e
