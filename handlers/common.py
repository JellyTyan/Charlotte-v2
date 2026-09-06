import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from fluentogram import TranslatorRunner

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("close_error"))
async def handle_close_error(callback: CallbackQuery, i18n: TranslatorRunner | None = None) -> None:
    """
    Handle clicking the 'Close' button on an error message.
    Deletes the error message. In group chats, checks if user is message owner or chat admin.
    """
    data_parts = callback.data.split(":", 1)
    owner_id_str = data_parts[1] if len(data_parts) > 1 and data_parts[1] else None

    chat = callback.message.chat if callback.message else None
    if chat and chat.id < 0 and owner_id_str:
        try:
            owner_id = int(owner_id_str)
        except ValueError:
            owner_id = None

        if owner_id and callback.from_user.id != owner_id:
            # Check if clicker is admin or creator in this chat
            is_admin = False
            try:
                member = await callback.bot.get_chat_member(chat_id=chat.id, user_id=callback.from_user.id)
                if member.status in ("creator", "administrator"):
                    is_admin = True
            except Exception as e:
                logger.warning(f"Failed to check admin status for {callback.from_user.id} in {chat.id}: {e}")

            if not is_admin:
                alert_text = i18n.get("not-your-request") if i18n else "❌ Это не ваш запрос"
                await callback.answer(alert_text, show_alert=True)
                return

    if callback.message:
        try:
            await callback.message.delete()
        except TelegramBadRequest as e:
            logger.debug(f"Could not delete error message: {e}")

    await callback.answer()
