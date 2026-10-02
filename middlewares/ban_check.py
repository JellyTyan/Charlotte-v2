from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, InlineQuery, Update

from storage.db.crud import get_user, get_chat_settings


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
            if user and user.is_banned:
                if isinstance(target_event, CallbackQuery):
                    i18n = data.get("i18n")
                    alert_text = i18n.get("banned-global") if i18n else "🚫 You are globally banned."
                    try:
                        await target_event.answer(alert_text, show_alert=True)
                    except Exception:
                        pass
                elif isinstance(target_event, InlineQuery):
                    try:
                        await target_event.answer([], cache_time=1, is_personal=True)
                    except Exception:
                        pass
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
                            pass
                    return

            try:
                await session.commit()
            except Exception:
                await session.rollback()

        return await handler(event, data)

