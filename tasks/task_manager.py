import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

import httpx

from core.config import settings
from models.errors import BotError, ErrorCode
from models.service_list import Services

logger = logging.getLogger(__name__)

MEDIA_CORE_ERROR_MAP: dict[str, ErrorCode] = {
    "not_found": ErrorCode.NOT_FOUND,
    "login_required": ErrorCode.PRIVATE_CONTENT,
    "private_media": ErrorCode.PRIVATE_CONTENT,
    "nsfw_not_allowed": ErrorCode.AGE_RESTRICTED,
    "media_too_large": ErrorCode.LARGE_FILE,
    "country_blocked": ErrorCode.REGION_RESTRICTED,
    "members_only": ErrorCode.PRIVATE_CONTENT,
    "invalid_url": ErrorCode.INVALID_URL,
    "not_supported": ErrorCode.NOT_ALLOWED,
    "preview_only": ErrorCode.PREVIEW_ONLY,
    "track_not_found": ErrorCode.NOT_FOUND,
    "download_failed": ErrorCode.INTERNAL_ERROR,
    "rate_limited": ErrorCode.INTERNAL_ERROR,
    "internal_error": ErrorCode.INTERNAL_ERROR,
}


def raise_media_core_error(err_data: dict, url: str, service: Services) -> None:
    """Map media-core error code string to BotError and raise it."""
    err_code_str = err_data.get("error", "internal_error")
    code = MEDIA_CORE_ERROR_MAP.get(err_code_str, ErrorCode.INTERNAL_ERROR)
    msg = err_data.get("message") or f"Download error: {err_code_str}"
    is_critical = err_code_str in ("internal_error", "download_failed", "rate_limited")
    is_logged = err_code_str in ("internal_error", "not_found", "media_too_large", "download_failed", "rate_limited")

    raise BotError(
        code=code,
        url=url,
        service=service,
        message=msg,
        is_logged=is_logged,
        critical=is_critical,
    )


def handle_task_result(result_data: dict, url: str, service: Services) -> dict:
    """Process a finished media-core task result dictionary."""
    status = result_data.get("status")

    if status in ("completed", "success", "done"):
        return result_data.get("data", result_data)
    elif "items" in result_data:
        return result_data
    elif status == "failed":
        raise_media_core_error(result_data, url, service)
    elif status == "cancelled":
        raise BotError(
            code=ErrorCode.DOWNLOAD_CANCELLED,
            url=url,
            service=service,
            message="Загрузка отменена пользователем.",
            is_logged=False,
            critical=False,
        )
    else:
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            url=url,
            service=service,
            message=f"Unknown task status: {status}",
            is_logged=True,
            critical=True,
        )


async def wait_for_media_task(
    task_id: str,
    url: str,
    service: Services,
    user_id: int,
    http_client: httpx.AsyncClient,
    status_timeout: float = 3.0,
    base_url: Optional[str] = None,
    result_prefix: str = "media:result:",
) -> dict:
    """
    Wait for media-core or lossless-core task completion.
    Polls Redis keys on both media_redis_client and redis_client for fast response.
    Every `status_timeout` (3s), checks `GET /status/{task_id}` to verify liveness.
    Keeps waiting if status is pending, active, or retry.
    """
    from storage.cache.redis_client import media_redis_client, redis_client

    clients_to_use = [c for c in (media_redis_client, redis_client) if c is not None]
    target_url = (base_url or settings.MEDIA_CORE_URL).rstrip("/")
    elapsed_since_status = 0.0

    # Polling frequency
    check_interval = 0.5 if clients_to_use else 1.5

    while True:
        # Check if cancelled by /cancel command
        if task_manager.is_user_cancelled(user_id):
            raise BotError(
                code=ErrorCode.DOWNLOAD_CANCELLED,
                url=url,
                service=service,
                message="Загрузка отменена пользователем.",
                is_logged=False,
                critical=False,
            )

        # 1. Try reading result from Redis (checks both DB 1 and DB 0)
        for c in clients_to_use:
            try:
                raw_res = await c.get(f"{result_prefix}{task_id}")
                if raw_res:
                    data = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
                    return handle_task_result(data, url, service)
            except Exception as e:
                logger.debug(f"Redis get error for task {task_id}: {e}")

        await asyncio.sleep(check_interval)
        elapsed_since_status += check_interval

        # 2. Check /status/{id} if status_timeout passed or no redis
        if elapsed_since_status >= status_timeout or not clients_to_use:
            elapsed_since_status = 0.0
            try:
                res = await http_client.get(
                    f"{target_url}/status/{task_id}",
                    timeout=10.0,
                )
                if res.status_code == 404:
                    raise BotError(
                        code=ErrorCode.NOT_FOUND,
                        url=url,
                        service=service,
                        message="Task not found or expired on backend core",
                        is_logged=True,
                        critical=False,
                    )
                if res.status_code == 200:
                    status_data = res.json()
                    task_status = status_data.get("status")

                    # If still in queue or active or retry -> keep waiting
                    if task_status in ("pending", "active", "retry"):
                        continue
                    elif task_status in ("completed", "success", "done", "failed", "cancelled") or "items" in status_data:
                        return handle_task_result(status_data, url, service)
                    elif task_status == "error":
                        raise BotError(
                            code=ErrorCode.INTERNAL_ERROR,
                            url=url,
                            service=service,
                            message=status_data.get("message", "Task error"),
                            is_logged=True,
                            critical=True,
                        )
                else:
                    logger.warning(f"Unexpected response from /status/{task_id}: {res.status_code} {res.text}")
            except httpx.RequestError as e:
                logger.warning(f"Network error checking /status/{task_id}: {e}")
            except BotError:
                raise
            except Exception as e:
                logger.error(f"Error checking status for {task_id}: {e}")


class TaskManager:
    def __init__(self):
        self._user_locks: dict[int, tuple[asyncio.Semaphore, int]] = {}
        self._global_semaphore = asyncio.Semaphore(10)

        self._cancelled_users: set[int] = set()
        self._active_tasks: dict[int, asyncio.Task] = {}
        self._active_media_tasks: dict[int, str] = {}

    @asynccontextmanager
    async def _user_lock(self, user_id: int):
        """Dynamic user semaphore with reference counting to prevent memory leak"""
        if user_id not in self._user_locks:
            self._user_locks[user_id] = (asyncio.Semaphore(1), 0)

        sem, ref_count = self._user_locks[user_id]
        self._user_locks[user_id] = (sem, ref_count + 1)

        await sem.acquire()
        try:
            yield
        finally:
            sem.release()
            current = self._user_locks.get(user_id)
            if current:
                cur_sem, cur_count = current
                if cur_count <= 1:
                    self._user_locks.pop(user_id, None)
                else:
                    self._user_locks[user_id] = (cur_sem, cur_count - 1)

    async def run_media_download(
        self,
        user_id: int,
        url: str,
        service: Services,
        payload: dict[str, Any],
        http_client: httpx.AsyncClient,
        base_url: Optional[str] = None,
        result_prefix: Optional[str] = None,
    ) -> dict:
        """
        Enqueues task to media-core or lossless-core via POST /enqueue and waits for result.
        Returns the data dictionary on success, or raises BotError on failure/cancellation.
        """
        self._cancelled_users.discard(user_id)
        target_url = (base_url or settings.MEDIA_CORE_URL).rstrip("/")
        if result_prefix is None:
            result_prefix = "lossless:result:" if target_url == settings.LOSSLESS_CORE_URL.rstrip("/") else "media:result:"

        async with self._user_lock(user_id):
            async with self._global_semaphore:
                # 1. Enqueue task
                try:
                    res = await http_client.post(
                        f"{target_url}/enqueue",
                        json=payload,
                        timeout=15.0,
                    )
                except Exception as e:
                    logger.error(f"Failed to connect to {target_url}/enqueue: {e}")
                    raise BotError(
                        code=ErrorCode.INTERNAL_ERROR,
                        url=url,
                        service=service,
                        message=f"Failed to connect to backend: {e}",
                        is_logged=True,
                        critical=True,
                    )

                if res.status_code not in (200, 202):
                    err_text = res.text
                    logger.error(f"Enqueue failed on {target_url} ({res.status_code}): {err_text}")
                    raise BotError(
                        code=ErrorCode.INTERNAL_ERROR,
                        url=url,
                        service=service,
                        message=f"Enqueue failed ({res.status_code}): {err_text}",
                        is_logged=True,
                        critical=True,
                    )

                enqueue_data = res.json()
                task_id = enqueue_data.get("task_id")
                if not task_id:
                    raise BotError(
                        code=ErrorCode.INTERNAL_ERROR,
                        url=url,
                        service=service,
                        message=f"No task_id returned from backend: {res.text}",
                        is_logged=True,
                        critical=True,
                    )

                self._active_media_tasks[user_id] = (task_id, target_url)

                try:
                    # 2. Wait for result
                    data = await wait_for_media_task(
                        task_id=task_id,
                        url=url,
                        service=service,
                        user_id=user_id,
                        http_client=http_client,
                        base_url=target_url,
                        result_prefix=result_prefix,
                    )
                    return data
                finally:
                    self._active_media_tasks.pop(user_id, None)
                    self._cancelled_users.discard(user_id)

    async def run_download(self, user_id: int, url: str, coro):
        """Legacy runner for coroutine-based downloads (e.g. lossless-core)."""
        self._cancelled_users.discard(user_id)

        async with self._user_lock(user_id):
            async with self._global_semaphore:
                task = asyncio.create_task(coro)
                self._active_tasks[user_id] = task

                try:
                    return await task
                except asyncio.CancelledError:
                    raise BotError(code=ErrorCode.DOWNLOAD_CANCELLED, message="Загрузка отменена пользователем.")
                finally:
                    self._active_tasks.pop(user_id, None)

    async def cancel_user(self, user_id: int, http_client: Optional[httpx.AsyncClient] = None) -> bool:
        """
        Cancels active downloads for user_id.
        Calls POST /cancel/{task_id} on media-core or lossless-core if a task is running.
        Cancels asyncio.Task if a coroutine task is running.
        """
        self._cancelled_users.add(user_id)
        had_active = False

        # 1. Cancel active core task (media-core or lossless-core)
        task_info = self._active_media_tasks.get(user_id)
        if task_info:
            had_active = True
            if isinstance(task_info, tuple):
                task_id, target_url = task_info
            else:
                task_id = task_info
                target_url = settings.MEDIA_CORE_URL.rstrip("/")

            client = http_client or httpx.AsyncClient()
            try:
                await client.post(
                    f"{target_url}/cancel/{task_id}",
                    timeout=5.0,
                )
            except Exception as e:
                logger.warning(f"Failed to send cancel to {target_url} for {task_id}: {e}")
            finally:
                if http_client is None:
                    await client.aclose()

        # 2. Cancel active asyncio task (lossless-core legacy, etc.)
        if user_id in self._active_tasks:
            self._active_tasks[user_id].cancel()
            had_active = True

        return had_active

    def is_cancelled(self, user_id: int) -> bool:
        """Check and consume cancellation flag (used in playlist loops)."""
        if user_id in self._cancelled_users:
            self._cancelled_users.remove(user_id)
            return True
        return False

    def is_user_cancelled(self, user_id: int) -> bool:
        """Check if user has cancelled without consuming flag."""
        return user_id in self._cancelled_users

    def is_user_busy(self, user_id: int) -> bool:
        """Check if user has an active download in progress."""
        if user_id in self._user_locks:
            sem, _ = self._user_locks[user_id]
            return sem.locked()
        return False


task_manager = TaskManager()
