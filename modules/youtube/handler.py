from models.errors import ErrorCode
from modules.router import service_router as router
from aiogram import F
from aiogram.types import FSInputFile, Message, CallbackQuery
import logging
from .models import YoutubeCallback
from utils import truncate_string, format_duration
from tasks.task_manager import task_manager

logger = logging.getLogger(__name__)


YOUTUBE_REGEX = r"https?://(?:www\.)?(?:m\.)?(?:youtu\.be/|youtube\.com/(?:shorts/|watch\?v=))([\w-]+)"

@router.message(F.text.regexp(YOUTUBE_REGEX))
async def youtube_handler(message: Message):
    # Check if service is blocked for this chat
    # user_settings = await MediaHandler.get_settings_for_chat(message.chat.id, callback_query.from_user.id)
    # blocked_services = getattr(user_settings, 'blocked_services', [])
    # if service.name + "Service" in blocked_services:
    #     return

    if not message.text or not message.from_user:
        return

    await task_manager.add_task(message.from_user.id, process_youtube_url(message))


async def process_youtube_url(message: Message):
    if not message.bot or not message.text:
        return

    await message.bot.send_chat_action(message.chat.id, "find_location")
    process_message = await message.reply("Processing...")

    from .service import YouTubeService
    from models.errors import BotError

    media_metadata = await YouTubeService().get_info(message.text)
    if media_metadata is None:
        raise BotError(
            code=ErrorCode.METADATA_ERROR,
            message="Failed to get metadata",
            url=message.text,
            is_logged=True
        )

    caption = f"<b>{media_metadata.title}</b>\n\n"
    caption += f"<b>Channel:</b><a href='{media_metadata.performer_url}'> {media_metadata.performer}</a>\n"
    caption += f"<b>Duration:</b> {format_duration(media_metadata.duration) \
        if media_metadata.duration else "00"}\n\n"
    caption += f"{media_metadata.description}"

    await process_message.delete()

    if media_metadata.cover:
        await message.reply_photo(
            photo=FSInputFile(media_metadata.cover),
            caption=truncate_string(caption, 1024),
            reply_markup=media_metadata.keyboard
        )
    else:
        await message.reply(
            truncate_string(caption, 1024),
            reply_markup=media_metadata.keyboard
        )


@router.callback_query(YoutubeCallback.filter())
async def format_choice_handler(callback_query: CallbackQuery, callback_data: YoutubeCallback):
    user_id = callback_query.from_user.id
    message = callback_query.message
    if not isinstance(message, Message):
        return

    from utils.url_cache import get_url

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

    active_count = task_manager.get_active_count(user_id)
    if active_count > 0:
        await callback_query.answer(f"Added to queue ({active_count} in queue)")
    else:
        await callback_query.answer("Starting download...")

    await message.delete()

    await task_manager.add_task(user_id, download_youtube_media(message, url, format_choice, user_id))


async def download_youtube_media(message: Message, url: str, format_choice: str, user_id: int):
    from .service import YouTubeService
    from senders.media_sender import MediaSender

    if message.bot:
        await message.bot.send_chat_action(message.chat.id, "record_video")

    media_content = await YouTubeService().download(url, format_choice)

    send_manager = MediaSender()
    await send_manager.send(message, media_content, user_id)
