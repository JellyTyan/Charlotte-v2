from aiogram import F
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from models.service_list import Services
from modules.router import service_router as router
from senders.media_sender import MediaSender
from tasks.task_manager import task_manager
from utils.arq_pool import get_arq_pool
from utils.statistics_helper import log_download_event
from .service import TwitchService


TWITCH_REGEX = (
    r"https?://(?:www\.)?twitch\.tv/\w+/clip/\S+"
    r"|https?://clips\.twitch\.tv/\S+"
)


@router.message(F.text.regexp(TWITCH_REGEX))
async def twitch_handler(message: Message, db_session: AsyncSession):
    if not message.text or not message.from_user:
        return

    user_id = message.from_user.id

    download_task = await task_manager.add_task(
        user_id,
        download_coro=process_twitch_url(message, db_session),
        message=message,
    )

    if download_task:
        async def send_when_ready():
            try:
                media_content = await download_task
                if media_content:
                    sender = MediaSender()
                    await sender.send(message, media_content, service="twitch", db_session=db_session)
            except Exception:
                pass

        await task_manager.add_send_task(user_id, send_when_ready())


async def process_twitch_url(message: Message, db_session: AsyncSession):
    """Download a Twitch clip and return MediaContent list."""
    if not message.bot or not message.text:
        return None

    user_id = message.from_user.id if message.from_user else message.chat.id

    arq = await get_arq_pool("heavy")
    service = TwitchService(arq=arq)

    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "upload_video")

    media_content = await service.download(message.text)

    await log_download_event(db_session, user_id, Services.TWITCH, "success")

    return media_content
