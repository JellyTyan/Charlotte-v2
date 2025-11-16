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
    logger.error(f"Global error handler triggered: {type(exception).__name__}: {exception}")

    # Get message from update (can be from message or callback_query)
    message = event.update.message
    if not message and event.update.callback_query:
        message = event.update.callback_query.message
        logger.debug(f"Got message from callback_query: {message}")

    if not message:
        logger.error(f"Error without message context: {exception}")
        return

    # Handle BotError
    if isinstance(exception, BotError):
        logger.info(f"Handling BotError: code={exception.code}, message={exception.message}")

        error_message = None
        match exception.code:
            case ErrorCode.INVALID_URL:
                error_message = "I'm sorry. You may have provided a corrupted link, private content or 18+ content 🤯"
            case ErrorCode.LARGE_FILE:
                error_message = "Critical error #022 - media file is too large"
            case ErrorCode.SIZE_CHECK_FAIL:
                error_message = "Wow, you tried to download too heavy media. Don't do this, pleeease 😭"
            case ErrorCode.DOWNLOAD_FAILED:
                error_message = "Sorry, I couldn't download the media."
            case ErrorCode.DOWNLOAD_CANCELLED:
                error_message = "Download canceled."
            case ErrorCode.PLAYLIST_INFO_ERROR:
                error_message = "Get playlist items error"
            case ErrorCode.METADATA_ERROR:
                error_message = "Failed to get media metadata"
            case ErrorCode.INTERNAL_ERROR:
                error_message = "Sorry, there was an error. Try again later 🧡"

        if error_message:
            logger.info(f"Sending error message to user: {error_message}")
            await message.answer(error_message)
        else:
            logger.warning(f"No error message defined for code: {exception.code}")

        if exception.critical and config.ADMIN_ID:
            logger.info(f"Sending critical error notification to admin {config.ADMIN_ID}")
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
