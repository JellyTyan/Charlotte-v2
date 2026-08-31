from aiogram import BaseMiddleware
from aiogram_dialog import ShowMode
# import logging

# logger = logging.getLogger(__name__)


class ForceEditShowModeMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        dialog_manager = data.get("dialog_manager")
        # logger.info(f"ForceEditShowMode: dialog_manager={'FOUND' if dialog_manager else 'MISSING'}")
        if dialog_manager is not None:
            dialog_manager.show_mode = ShowMode.EDIT
        return await handler(event, data)
