from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery

from storage.db.crud import get_user


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = None
        if isinstance(event, Message) and event.from_user:
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery) and event.from_user:
            user_id = event.from_user.id

        if user_id:
            user = await get_user(user_id)
            if user and user.is_banned:
                # We can either ignore the update or answer it.
                # If it's a message, we might want to reply (or not, to avoid spam).
                # If it's a callback, we MUST answer to stop the loading animation.

                if isinstance(event, CallbackQuery):
                    await event.answer("🚫 You are banned.", show_alert=True)
                elif isinstance(event, Message):
                    # Ideally we check if we already notified them recently to avoid spam loops?
                    # For now just silent ignore or simple reply.
                    # Choosing to effectively ignore processing but maybe log/print?
                    # Let's simple ignore to not feed trolls, or maybe send 1 msg.
                    pass

                return # Stop processing

        return await handler(event, data)
