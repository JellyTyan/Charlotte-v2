import logging

from aiogram import F
from aiogram.types import Message
from fluentogram import TranslatorRunner

from core.config import Config
from models.service_list import Services
from modules.router import service_router as router
from senders.media_sender import MediaSender
from storage.db.crud import get_user, get_chat_settings
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.statistics_helper import log_download_event
from .service import TwitterService

logger = logging.getLogger(__name__)


TWITTER_REGEX = r"https://(?:twitter|x)\.com/\w+/status/\d+"

@router.message(F.text.regexp(TWITTER_REGEX))
async def twitter_handler(message: Message, config: Config, i18n: TranslatorRunner):
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id

    # Start download task
    download_task = await task_manager.add_task(
        user_id,
        download_coro=process_twitter_url(message, config, i18n),
        message=message,
        url=message.text
    )

    # When download completes, queue send task
    if download_task:
        async def send_when_ready():
            try:
                media_content = await download_task
                if media_content:
                    send_manager = MediaSender()
                    await send_manager.send(message, media_content, service="twitter")
            except Exception:
                # Error already logged in download task
                pass

        await task_manager.add_send_task(user_id, send_when_ready())


async def process_twitter_url(message: Message, config: Config, i18n: TranslatorRunner):
    """Download Twitter media and return content"""
    if not message.bot or not message.text:
        return None

    user_id = message.from_user.id if message.from_user else message.chat.id
    url = message.text.strip()
    allow_nsfw = True

    if message.chat.id < 0:
        settings = await get_chat_settings(message.chat.id)
        allow_nsfw = settings.profile.allow_nsfw

    arq = await get_arq_pool('light')

    # Send chat action for user feedback
    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "choose_sticker")

    try:
        # Download content
        user = await get_user(user_id)
        is_premium = user.is_premium if user else False

        if is_premium:
            media_content = await TwitterService(arq=arq).download(url, premium=True, config=config, allow_nsfw=allow_nsfw)
        else:
            media_content = await TwitterService(arq=arq).download(url, allow_nsfw=allow_nsfw)

        # Log success
        await log_download_event(user_id, Services.TWITTER, 'success')

        return media_content

    except Exception as e:
        # Error handling is usually done by task wrapper or specific exception catches if needed
        raise
