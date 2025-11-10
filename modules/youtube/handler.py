from modules.router import service_router as router
from aiogram import F
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from typing import Optional
import logging

logger = logging.getLogger(__name__)


YOUTUBE_REGEX = r"https?://(?:www\.)?(?:m\.)?(?:youtu\.be/|youtube\.com/(?:shorts/|watch\?v=))([\w-]+)"

class YoutubeCallback(CallbackData, prefix="yt"):
    type: str
    format_id: str
    audio_id: Optional[str] = None
    url_hash: Optional[str] = None
    sponsored: Optional[bool] = False

@router.message(F.text.regexp(YOUTUBE_REGEX))
async def youtube_handler(message: Message):
    # Check if service is blocked for this chat
    # user_settings = await MediaHandler.get_settings_for_chat(message.chat.id, callback_query.from_user.id)
    # blocked_services = getattr(user_settings, 'blocked_services', [])
    # if service.name + "Service" in blocked_services:
    #     return

    if not message.text:
        return

    from .service import YouTubeService
    from models.error_models import BotError

    try:
        media_metadata = await YouTubeService().get_info(message.text)
        if media_metadata is None:
            return await message.reply("No metadata found")

        await message.reply(
            "Choose a format to download:", reply_markup=media_metadata.keyboard
        )
    except BotError as e:
        logger.error(f"YouTube error: {e.message}")
        await message.reply(f"Error: {e.message}")
    except Exception as e:
        logger.error(f"Unexpected error in youtube_handler: {e}")
        await message.reply("An error occurred while processing the video")


@router.callback_query(YoutubeCallback.filter())
async def format_choice_handler(callback_query: CallbackQuery, callback_data: YoutubeCallback):
    user_id = callback_query.from_user.id
    message = callback_query.message
    if not isinstance(message, Message):
        return

    # Check sponsor access for premium formats
    # if callback_data.sponsored:
    #     from utils.sponsor_check import check_sponsor_access
    #     if not await check_sponsor_access(user_id, is_premium_format=True):
    #         await callback_query.answer(_("⭐ This format requires sponsor status"), show_alert=True)
    #         return

    # Get URL from cache using hash
    from utils.url_cache import get_url
    from .service import YouTubeService

    if not callback_data.url_hash:
        await callback_query.answer("Invalid callback data")
        return

    url = get_url(callback_data.url_hash)
    if not url:
        await callback_query.answer("URL expired or not found")
        return

    if callback_data.type == 'video':
        format_choice = f"youtube_video_{callback_data.format_id}+{callback_data.audio_id}"
    else:
        format_choice = f"youtube_audio_{callback_data.format_id}"

    await callback_query.answer("Starting download...")
    await message.delete()

    try:
        media_content = await YouTubeService().download(url, format_choice)

        from sender.message_sender import SendManager
        send_manager = SendManager()
        await send_manager.send_media(media_content, callback_query.message)

    except Exception as e:
        # from utils.error_handler import BotError, ErrorCode, handle_download_error
        # if not isinstance(e, BotError):
        #     e = BotError(
        #         code=ErrorCode.DOWNLOAD_FAILED,
        #         message=str(e),
        #         url=url,
        #         critical=True,
        #         is_logged=True
        #     )
        # await handle_download_error(callback_query.message, e)
        pass
