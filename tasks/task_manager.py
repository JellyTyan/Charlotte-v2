import asyncio
import logging
from collections import defaultdict
from typing import Dict

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self):
        self._user_semaphores: Dict[int, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(1))
        self._user_tasks: Dict[int, list] = defaultdict(list)
        self._pending_urls = defaultdict(set)

    async def add_task(self, user_id: int, coro, message=None, url=None):
        """Add task to user's queue using semaphore"""
        if url and url in self._pending_urls[user_id]:
            logger.warning(f"Duplicate request ignored for user {user_id}")
            return None

        if url:
            self._pending_urls[user_id].add(url)

        # Initial reaction if enabled (before queue)
        if message:
            try:
                from storage.db.crud import get_user_settings, get_chat_settings
                from aiogram.types import ReactionTypeEmoji

                settings = None
                if message.chat.type in ("group", "supergroup"):
                     settings = await get_chat_settings(message.chat.id)
                else:
                     settings = await get_user_settings(user_id)

                if settings and settings.send_reactions:
                     await message.react([ReactionTypeEmoji(emoji="👍")])
            except Exception as e:
                logger.warning(f"Failed to set initial reaction: {e}")

        async def wrapper():
            async with self._user_semaphores[user_id]:
                logger.debug(f"Processing task for user {user_id}")
                try:
                    return await coro
                except Exception as e:
                    logger.error(f"Task failed for user {user_id}: {e}", exc_info=True)

                    # Handle error manually if message provided
                    if message:
                        from models.errors import BotError
                        if isinstance(e, BotError):
                            await self._handle_bot_error(e, message, user_id)

                    # Remove reaction on error if needed?
                    # Usually we might want to change it to '😢' or something?
                    # Or just leave it. User didn't specify error case.
                    raise
                finally:
                    # Remove URL from pending after task completes
                    if url:
                        self._pending_urls[user_id].discard(url)

        task = asyncio.create_task(wrapper())
        self._user_tasks[user_id].append(task)

        self._user_tasks[user_id] = [t for t in self._user_tasks[user_id] if not t.done()]

        return task

    async def _handle_bot_error(self, exception, message, user_id: int):
        """Handle BotError and send message to user"""
        from core.loader import bot, dp
        from core.config import Config
        from aiogram.enums import ParseMode
        from models.errors import ErrorCode

        config = Config()
        hub = dp.workflow_data.get("_translator_hub")
        if not hub:
            await message.answer("❌ An error occurred. Please try again later.")
            return

        # Get user settings for locale
        from storage.db.crud import get_user_settings
        settings = await get_user_settings(user_id)
        lang = settings.lang if settings else "en"
        i18n = hub.get_translator_by_locale(lang)

        # Get error message
        error_message = None
        match exception.code:
            case ErrorCode.INVALID_URL:
                error_message = i18n.error.invalid.url()
            case ErrorCode.LARGE_FILE:
                error_message = i18n.error.large.file()
            case ErrorCode.SIZE_CHECK_FAIL:
                error_message = i18n.error.fail.check()
            case ErrorCode.DOWNLOAD_FAILED:
                error_message = i18n.error.download.error()
            case ErrorCode.DOWNLOAD_CANCELLED:
                error_message = i18n.error.download.canceled()
            case ErrorCode.PLAYLIST_INFO_ERROR:
                error_message = i18n.error.playlist.info()
            case ErrorCode.METADATA_ERROR:
                error_message = i18n.error.metadata()
            case ErrorCode.NOT_FOUND:
                error_message = i18n.error.no.found()
            case ErrorCode.INTERNAL_ERROR:
                error_message = i18n.error.internal()

        if error_message:
            await message.answer(error_message)

        # Log failed statistics
        if hasattr(exception, 'url') and exception.url:
            from middlewares.statistics import StatisticsMiddleware
            from utils.statistics_helper import log_download_event
            service_name = None
            for pattern, name in StatisticsMiddleware.SERVICE_PATTERNS.items():
                if pattern in exception.url:
                    service_name = name
                    break
            if service_name:
                await log_download_event(user_id, service_name, 'failed')

        # Send to admin if critical
        if exception.critical and config.ADMIN_ID:
            await bot.send_message(
                config.ADMIN_ID,
                f"Sorry, there was an error:\n{exception.url}\n\n<pre>{exception.message}</pre>",
                parse_mode=ParseMode.HTML
            )

    def get_active_count(self, user_id: int) -> int:
        """Get number of active tasks for user"""
        self._user_tasks[user_id] = [t for t in self._user_tasks[user_id] if not t.done()]
        return len(self._user_tasks[user_id])

    async def cancel_user_tasks(self, user_id: int) -> int:
        """Cancel all tasks for user"""
        tasks = self._user_tasks.get(user_id, [])
        cancelled_count = 0
        for task in tasks:
            if not task.done():
                task.cancel()
                cancelled_count += 1
        self._user_tasks[user_id] = []
        logger.info(f"Cancelled {cancelled_count} tasks for user {user_id}")
        return cancelled_count


task_manager = TaskManager()
