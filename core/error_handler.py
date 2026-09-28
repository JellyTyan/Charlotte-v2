import logging
import traceback

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import Chat, ErrorEvent, Message, User
from fluentogram import TranslatorRunner

from core.alert_manager import send_admin_alert
from models.errors import BotError
from storage.db import database_manager
from storage.db.crud import get_chat_settings, get_user_settings

logger = logging.getLogger(__name__)

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
        await _notify_user(message, exception, i18n, user=user)

    if exception.critical:
        service_name = exception.service.value if exception.service else "Unknown"
        err_code_val = exception.code.value if hasattr(exception.code, "value") else str(exception.code)
        alert_key = f"boterror_{service_name}_{err_code_val}"
        await send_admin_alert(
            bot=bot,
            title=f"Service Alert: {service_name}",
            message=exception.message or f"Code {err_code_val}",
            context={
                "Service": service_name,
                "URL": exception.url,
                "Error Code": err_code_val,
                "User": str(user.id) if user else None,
            },
            alert_key=alert_key,
            cooldown_seconds=300,
        )

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


async def _notify_user(
    message: Message,
    exception: BotError,
    i18n: TranslatorRunner,
    user: User | None = None,
) -> None:
    from middlewares.button_owner import register_message_owner
    from utils.ephemeral import send_smart_message
    from utils.error_messages import get_error_keyboard, get_i18n_error_message
    error_message = get_i18n_error_message(exception.code, i18n)
    if not error_message:
        logger.warning(f"No error message defined for code: {exception.code}")
        return
    try:
        owner_id = user.id if user else (message.from_user.id if message.from_user else None)
        reply_markup = get_error_keyboard(i18n, owner_id=owner_id)
        sent = await send_smart_message(message, error_message, for_user_id=owner_id, reply_markup=reply_markup)
        if owner_id and sent and getattr(sent, "ephemeral_message_id", None) is None:
            await register_message_owner(sent, owner_id)
        if sent and hasattr(sent, "message_id"):
            from utils.message_context import save_message_context
            await save_message_context(sent.chat.id, sent.message_id, {
                "url": exception.url,
                "service": exception.service.value if exception.service else None,
                "error_code": exception.code.value if hasattr(exception.code, "value") else str(exception.code),
                "error_message": exception.message,
            })
    except TelegramAPIError as e:
        logger.warning(f"Failed to notify user: {e}")


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
            tb = traceback.format_exc()
            logger.error(f"Error without message context: {exception}", exc_info=exception)
            event_type = getattr(event.update, "event_type", "unknown")
            alert_key = f"unhandled_nomessage_{type(exception).__name__}"
            await send_admin_alert(
                bot=bot,
                title=f"Error in {event_type} Update",
                message=str(exception),
                traceback_str=tb,
                alert_key=alert_key,
                cooldown_seconds=300,
            )
            return

        hub = dp.workflow_data.get("_translator_hub")
        if not hub:
            logger.error("TranslatorHub not found in workflow_data")
            try:
                from middlewares.button_owner import register_message_owner
                from utils.ephemeral import send_smart_message
                from utils.error_messages import get_error_keyboard
                user, chat = _extract_user_and_chat(event.update)
                owner_id = user.id if user else (message.from_user.id if message.from_user else None)
                reply_markup = get_error_keyboard(None, owner_id=owner_id)
                sent = await send_smart_message(message, "❌ An error occurred. Please try again later.", for_user_id=owner_id, reply_markup=reply_markup)
                if owner_id and sent and getattr(sent, "ephemeral_message_id", None) is None:
                    await register_message_owner(sent, owner_id)
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
                from middlewares.button_owner import register_message_owner
                from utils.ephemeral import send_smart_message
                from utils.error_messages import get_error_keyboard
                owner_id = user.id if user else (message.from_user.id if message.from_user else None)
                reply_markup = get_error_keyboard(i18n, owner_id=owner_id)
                sent = await send_smart_message(message, i18n.error.generic(), for_user_id=owner_id, reply_markup=reply_markup)
                if owner_id and sent and getattr(sent, "ephemeral_message_id", None) is None:
                    await register_message_owner(sent, owner_id)
            except TelegramAPIError:
                pass

            tb = traceback.format_exc()
            logger.error(f"Unhandled error: {exception}", exc_info=exception)
            alert_key = f"unhandled_{type(exception).__name__}_{exception.__traceback__.tb_lineno if exception.__traceback__ else 0}"
            await send_admin_alert(
                bot=bot,
                title=f"Unhandled Exception: {type(exception).__name__}",
                message=str(exception),
                context={
                    "User ID": str(user.id) if user else (str(message.from_user.id) if message and message.from_user else None),
                    "Chat ID": str(chat.id) if chat else (str(message.chat.id) if message and hasattr(message, "chat") else None),
                },
                traceback_str=tb,
                alert_key=alert_key,
                cooldown_seconds=300,
            )