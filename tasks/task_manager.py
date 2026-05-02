import asyncio
from collections import defaultdict


class TaskManager:
    def __init__(self):
        self._user_semaphores = defaultdict(lambda: asyncio.Semaphore(1))
        self._global_semaphore = asyncio.Semaphore(10)

        self._cancelled_users = set()
        self._active_tasks = {}

    async def run_download(self, user_id: int, url: str, coro):
        self._cancelled_users.discard(user_id)

        async with self._user_semaphores[user_id]:
            async with self._global_semaphore:
                task = asyncio.create_task(coro)
                self._active_tasks[user_id] = task

                try:
                    return await task
                except asyncio.CancelledError:
                    from models.errors import BotError, ErrorCode

                    raise BotError(code=ErrorCode.DOWNLOAD_CANCELLED, message="Загрузка отменена пользователем.")
                finally:
                    self._active_tasks.pop(user_id, None)

    def cancel_user(self, user_id: int):
        self._cancelled_users.add(user_id)

        if user_id in self._active_tasks:
            self._active_tasks[user_id].cancel()

    def is_cancelled(self, user_id: int) -> bool:
        if user_id in self._cancelled_users:
            self._cancelled_users.remove(user_id)
            return True
        return False


task_manager = TaskManager()
