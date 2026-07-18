import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from aiogram.types import ErrorEvent, Message, User, Chat
from fluentogram import TranslatorRunner

from core.config import Config, settings
from models.errors import BotError
from storage.db import database_manager
from storage.db.crud import get_chat_settings, get_user_settings
from utils import escape_html

logger = logging.getLogger(__name__)
config = Config()

_IGNORABLE_TG_ERRORS = {
    "TOPIC_CLOSED",
    "TOPIC_DELETED",
    "MESSAGE_NOT_MODIFIED",
    "MESSAGE_TO_DELETE_NOT_FOUND",
    "MESSAGE_TO_EDIT_NOT_FOUND",
}


def _is_ignorable_tg_error(exception: TelegramBadRequest) -> bool:
    return any(code in str(exception) for code in _IGNORABLE_TG_ERRORS)


def _extract_message(update) -> Message | None:
    if update.message:
        return update.message
    if update.callback_query:
        return update.callback_query.message
    return None


def _extract_user_and_chat(update) -> tuple[User | None, Chat | None]:
    if update.message:
        return update.message.from_user, update.message.chat
    if update.callback_query:
        chat = update.callback_query.message.chat if update.callback_query.message else None
        return update.callback_query.from_user, chat
    return None, None


async def _resolve_language(chat: Chat | None, user: User | None) -> str:
    try:
        async with database_manager.async_session() as session:
            if chat and chat.type != "private":
                settings = await get_chat_settings(session, chat.id)
            elif user:
                settings = await get_user_settings(session, user.id)
            else:
                return "en"
            return settings.profile.language if settings else "en"
    except Exception as db_err:
        logger.error(f"Failed to resolve language: {db_err}")
        return "en"


async def _handle_bot_error(
    exception: BotError,
    message: Message,
    user: User | None,
    chat: Chat | None,
    i18n: TranslatorRunner,
    bot: Bot,
) -> None:
    if exception.service:
        await _log_download_failure(exception, user, chat)

    if exception.send_user_message:
        await _notify_user(message, exception, i18n)

    if exception.critical:
        await _notify_admin(bot, exception)

    if exception.is_logged:
        logger.error(f"Error: {exception.message}")


async def _log_download_failure(exception: BotError, user: User | None, chat: Chat | None) -> None:
    user_id = user.id if user else (chat.id if chat else None)
    if not user_id:
        return
    from utils.statistics_helper import log_download_event
    async with database_manager.async_session() as session:
        await log_download_event(
            session, user_id=user_id, service=exception.service,
            status="failed_download", error_code=exception.code,
        )
        await session.commit()


async def _notify_user(message: Message, exception: BotError, i18n: TranslatorRunner) -> None:
    from utils.error_messages import get_i18n_error_message
    error_message = get_i18n_error_message(exception.code, i18n)
    if not error_message:
        logger.warning(f"No error message defined for code: {exception.code}")
        return
    try:
        await message.answer(error_message)
    except TelegramAPIError as e:
        logger.warning(f"Failed to notify user: {e}")


async def _notify_admin(bot: Bot, exception: BotError) -> None:
    if not settings.ADMIN_ID:
        return
    service_name = exception.service.value if exception.service else "Unknown"
    text = (
        f"Sorry, there was an error:\nService: {service_name}\n"
        f"{escape_html(exception.url)}\n\n<pre>{escape_html(exception.message)}</pre>"
    )
    try:
        await bot.send_message(settings.ADMIN_ID, text, parse_mode=ParseMode.HTML)
    except TelegramAPIError as e:
        logger.error(f"Failed to notify admin: {e}")


def register_error_handler(dp: Dispatcher, bot: Bot) -> None:
    @dp.error()
    async def global_error_handler(event: ErrorEvent):
        exception = event.exception
        logger.error(f"Global error handler triggered: {type(exception).__name__}: {exception}")

        if isinstance(exception, TelegramBadRequest) and _is_ignorable_tg_error(exception):
            logger.info(f"Ignoring non-actionable Telegram error: {exception}")
            return

        message = _extract_message(event.update)
        if not message:
            logger.error(f"Error without message context: {exception}", exc_info=True)
            return

        hub = dp.workflow_data.get("_translator_hub")
        if not hub:
            logger.error("TranslatorHub not found in workflow_data")
            try:
                await message.answer("❌ An error occurred. Please try again later.")
            except TelegramAPIError:
                pass
            return

        user, chat = _extract_user_and_chat(event.update)
        lang = await _resolve_language(chat, user)
        i18n: TranslatorRunner = hub.get_translator_by_locale(lang)

        if isinstance(exception, BotError):
            logger.info(f"Handling BotError: code={exception.code}, message={exception.message}")
            await _handle_bot_error(exception, message, user, chat, i18n, bot)
        else:
            try:
                await message.answer(i18n.error.generic())
            except TelegramAPIError:
                pass
            logger.error(f"Unhandled error: {exception}", exc_info=True)