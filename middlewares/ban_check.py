import datetime
import logging

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, ChatMemberUpdated, ChosenInlineResult, InlineQuery, Update

from storage.db.crud import create_user, ensure_chat, get_user, get_chat_settings, remember_bot_status, touch_user

logger = logging.getLogger(__name__)


def _as_date(value):
    """last_used is a DATE, but comes back as a datetime from the Redis user cache (dict_to_orm)."""
    return value.date() if isinstance(value, datetime.datetime) else value


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        from_user = data.get("event_from_user")
        chat = data.get("event_chat")

        target_event = getattr(event, "event", event)
        if isinstance(event, Update) and event.event:
            target_event = event.event

        user_id = from_user.id if from_user else None
        chat_id = chat.id if chat else None

        if not user_id and target_event and getattr(target_event, "from_user", None):
            user_id = target_event.from_user.id

        session = data.get("db_session")
        if session and user_id:
            # 1. Global ban check
            user = await get_user(session, user_id)
            # Someone using the bot directly (DM, inline, buttons) gets a row; a group member who just chats does not:
            # privacy mode is off, otherwise the whole group would land in users
            # (a "blocked the bot" event also comes from the DM chat — it is not activity)
            direct = not isinstance(target_event, ChatMemberUpdated) and (
                (chat_id is not None and chat_id > 0) or isinstance(target_event, (InlineQuery, ChosenInlineResult, CallbackQuery))
            )
            if user is None and direct:
                user, _ = await create_user(session, user_id)
            lang = from_user.language_code if from_user else None
            if direct and user and not user.is_banned and (
                _as_date(user.last_used) != datetime.date.today() or user.blocked_at
                or (lang and getattr(user, "language_code", None) != lang)
            ):
                await touch_user(session, user_id, lang)  # group downloads touch it in log_download_event
            if chat_id and chat_id < 0 and await ensure_chat(session, chat_id, user_id):
                try:  # fill the bot's status right away instead of waiting for a link or the full check
                    bot = data["bot"]
                    await remember_bot_status(session, chat_id, await bot.get_chat_member(chat_id, (await bot.me()).id))
                except Exception:
                    logger.debug("bot status probe failed", exc_info=True)
            if user and user.is_banned:
                if isinstance(target_event, CallbackQuery):
                    i18n = data.get("i18n")
                    alert_text = i18n.get("banned-global") if i18n else "🚫 You are globally banned."
                    try:
                        await target_event.answer(alert_text, show_alert=True)
                    except Exception:
                        logger.debug("best-effort call failed", exc_info=True)
                elif isinstance(target_event, InlineQuery):
                    try:
                        await target_event.answer([], cache_time=1, is_personal=True)
                    except Exception:
                        logger.debug("best-effort call failed", exc_info=True)
                return

            # 2. Chat / Group ban check
            if chat_id and chat_id < 0:
                chat_settings = await get_chat_settings(session, chat_id)
                if chat_settings and user_id in chat_settings.profile.banned_users:
                    if isinstance(target_event, CallbackQuery):
                        i18n = data.get("i18n")
                        alert_text = i18n.get("banned-chat") if i18n else "🚫 You are banned in this chat."
                        try:
                            await target_event.answer(alert_text, show_alert=True)
                        except Exception:
                            logger.debug("best-effort call failed", exc_info=True)
                    return

            try:
                await session.commit()
            except Exception:
                await session.rollback()

        return await handler(event, data)

