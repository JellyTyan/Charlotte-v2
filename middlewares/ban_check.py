from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from storage.db.crud import get_user, get_chat_settings

class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = None
        chat_id = None

        if isinstance(event, Message):
            if event.from_user:
                user_id = event.from_user.id
            if event.chat:
                chat_id = event.chat.id
        elif isinstance(event, CallbackQuery):
            if event.from_user:
                user_id = event.from_user.id
            if event.message and event.message.chat:
                chat_id = event.message.chat.id

        session = data.get("db_session")
        if session and user_id:
            user = await get_user(session, user_id)
            if user and user.is_banned:
                if isinstance(event, CallbackQuery):
                    i18n = data.get("i18n")
                    alert_text = i18n.get("banned-global") if i18n else "🚫 You are globally banned."
                    await event.answer(alert_text, show_alert=True)
                return

            # Check for group bans
            if chat_id and chat_id < 0:
                chat_settings = await get_chat_settings(session, chat_id)
                if chat_settings and user_id in chat_settings.profile.banned_users:
                    if isinstance(event, CallbackQuery):
                        i18n = data.get("i18n")
                        alert_text = i18n.get("banned-chat") if i18n else "🚫 You are banned in this chat."
                        await event.answer(alert_text, show_alert=True)
                    return

        return await handler(event, data)
