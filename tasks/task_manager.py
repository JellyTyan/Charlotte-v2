import asyncio
import logging
from collections import defaultdict
from typing import Dict

logger = logging.getLogger(__name__)


class TaskManager:
    def __init__(self):
        self._user_semaphores: Dict[int, asyncio.Semaphore] = defaultdict(lambda: asyncio.Semaphore(1))
        self._user_tasks: Dict[int, list] = defaultdict(list)

    async def add_task(self, user_id: int, coro):
        """Add task to user's queue using semaphore"""
        async def wrapper():
            async with self._user_semaphores[user_id]:
                logger.info(f"Processing task for user {user_id}")
                try:
                    return await coro
                except Exception as e:
                    logger.error(f"Task failed for user {user_id}: {e}", exc_info=True)
                    raise

        task = asyncio.create_task(wrapper())
        self._user_tasks[user_id].append(task)

        self._user_tasks[user_id] = [t for t in self._user_tasks[user_id] if not t.done()]

        return task

    def get_active_count(self, user_id: int) -> int:
        """Get number of active tasks for user"""
        self._user_tasks[user_id] = [t for t in self._user_tasks[user_id] if not t.done()]
        return len(self._user_tasks[user_id])


task_manager = TaskManager()
