import logging

from aiogram.enums import ParseMode
from aiogram.types import ErrorEvent
from fluentogram import TranslatorRunner

from core.config import Config
from core.loader import dp, bot
from models.errors import BotError, ErrorCode
from storage.db.crud import get_chat_settings

logger = logging.getLogger(__name__)
config = Config()

@dp.error()
async def global_error_handler(event: ErrorEvent):
    """Handle all unhandled errors"""
    exception = event.exception
    logger.error(f"Global error handler triggered: {type(exception).__name__}: {exception}")

    # Get message from update (can be from message or callback_query)
    message = None
    if hasattr(event, 'message'):
        message = event.message
    elif hasattr(event, 'callback_query') and event.callback_query:
        message = event.callback_query.message

    if not message:
        logger.error(f"Error without message context: {exception}")
        return

    # Get i18n from workflow_data
    hub = dp.workflow_data.get("_translator_hub")
    if not hub:
        logger.error("TranslatorHub not found in workflow_data")
        await message.answer("❌ An error occurred. Please try again later.")
        return

    # Get user/chat for locale
    user = None
    if hasattr(event, 'from_user'):
        user = event.from_user
    elif hasattr(event, 'callback_query') and event.callback_query:
        user = event.callback_query.from_user

    chat = None
    if hasattr(event, 'chat'):
        chat = event.chat
    elif message:
        chat = message.chat

    lang = "en"

    if chat and chat.type != "private":
        settings = await get_chat_settings(chat.id)
        if settings:
            lang = settings.profile.language
    elif user:
        from storage.db.crud import get_user_settings
        settings = await get_user_settings(user.id)
        if settings:
            lang = settings.profile.language

    i18n: TranslatorRunner = hub.get_translator_by_locale(lang)

    # Handle BotError
    if isinstance(exception, BotError):
        logger.info(f"Handling BotError: code={exception.code}, message={exception.message}")

        from utils.error_messages import get_i18n_error_message
        error_message = get_i18n_error_message(exception.code, i18n)

        if error_message:
            logger.info(f"Sending error message to user: {error_message}")
            await message.answer(error_message)
        else:
            logger.warning(f"No error message defined for code: {exception.code}")

        if exception.critical and config.ADMIN_ID:
            logger.info(f"Sending critical error notification to admin {config.ADMIN_ID}")
            service_name = exception.service.value if exception.service else "Unknown"
            await bot.send_message(
                config.ADMIN_ID,
                f"Sorry, there was an error:\nService: {service_name}\n{exception.url}\n\n<pre>{exception.message}</pre>",
                parse_mode=ParseMode.HTML
            )

        if exception.is_logged:
            logger.error(f"Error: {exception.message}")
    else:
        # Generic error
        await message.answer(i18n.error.generic())
        logger.error(f"Unhandled error: {exception}", exc_info=True)
