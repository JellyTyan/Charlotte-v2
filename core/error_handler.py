import logging
from aiogram.types import ErrorEvent
from aiogram.enums import ParseMode
from models.errors import BotError, ErrorCode
from core.loader import dp, bot
from core.config import Config

logger = logging.getLogger(__name__)
config = Config()

@dp.error()
async def global_error_handler(event: ErrorEvent):
    """Handle all unhandled errors"""
    exception = event.exception
    message = event.update.message

    if not message:
        return

    # Handle BotError
    if isinstance(exception, BotError):
        match exception.code:
            case ErrorCode.INVALID_URL:
                await message.answer("I'm sorry. You may have provided a corrupted link, private content or 18+ content 🤯")
            case ErrorCode.LARGE_FILE:
                await message.answer("Critical error #022 - media file is too large")
            case ErrorCode.SIZE_CHECK_FAIL:
                await message.answer("Wow, you tried to download too heavy media. Don't do this, pleeease 😭")
            case ErrorCode.DOWNLOAD_FAILED:
                await message.answer("Sorry, I couldn't download the media.")
            case ErrorCode.DOWNLOAD_CANCELLED:
                await message.answer("Download canceled.")
            case ErrorCode.PLAYLIST_INFO_ERROR:
                await message.answer("Get playlist items error")
            case ErrorCode.METADATA_ERROR:
                await message.answer("Failed to get media metadata")
            case ErrorCode.INTERNAL_ERROR:
                await message.answer("Sorry, there was an error. Try again later 🧡")

        if exception.critical and config.ADMIN_ID:
            await bot.send_message(
                config.ADMIN_ID,
                f"Sorry, there was an error:\n{exception.url}\n\n<pre>{exception.message}</pre>",
                parse_mode=ParseMode.HTML
            )

        if exception.is_logged:
            logger.error(f"Error: {exception.message}")
    else:
        # Generic error
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")
        logger.error(f"Unhandled error: {exception}", exc_info=True)
