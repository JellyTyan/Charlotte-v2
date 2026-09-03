import asyncio
import json
import logging
from collections import defaultdict
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
    "rate_limited": ErrorCode.INTERNAL_ERROR,
    "internal_error": ErrorCode.INTERNAL_ERROR,
}


def raise_media_core_error(err_data: dict, url: str, service: Services) -> None:
    """Map media-core error code string to BotError and raise it."""
    err_code_str = err_data.get("error", "internal_error")
    code = MEDIA_CORE_ERROR_MAP.get(err_code_str, ErrorCode.INTERNAL_ERROR)
    msg = err_data.get("message") or f"Download error: {err_code_str}"
    is_critical = (err_code_str == "internal_error")
    is_logged = err_code_str in ("internal_error", "not_found", "media_too_large")

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

    if status == "completed":
        return result_data.get("data", {})
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
    status_timeout: float = 20.0,
) -> dict:
    """
    Wait for media-core task completion.
    Polls Redis key `media:result:{task_id}` for fast response.
    Every `status_timeout` (20s), checks `GET /status/{task_id}` on media-core to verify liveness.
    Keeps waiting if status is pending, active, or retry.
    """
    from storage.cache.redis_client import media_redis_client, redis_client

    # media-core writes results to DB 1 (media_redis_client)
    client_to_use = media_redis_client or redis_client
    media_core_url = settings.MEDIA_CORE_URL.rstrip("/")
    elapsed_since_status = 0.0

    # Polling frequency
    check_interval = 0.5 if client_to_use else 1.5

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

        # 1. Try reading result from Redis (DB 1)
        if client_to_use:
            try:
                raw_res = await client_to_use.get(f"media:result:{task_id}")
                if raw_res:
                    data = json.loads(raw_res) if isinstance(raw_res, str) else raw_res
                    return handle_task_result(data, url, service)
            except Exception as e:
                logger.debug(f"Redis get error for task {task_id}: {e}")

        await asyncio.sleep(check_interval)
        elapsed_since_status += check_interval

        # 2. Check /status/{id} on media-core if status_timeout passed or no redis
        if elapsed_since_status >= status_timeout or not client_to_use:
            elapsed_since_status = 0.0
            try:
                res = await http_client.get(
                    f"{media_core_url}/status/{task_id}",
                    timeout=10.0,
                )
                if res.status_code == 404:
                    raise BotError(
                        code=ErrorCode.NOT_FOUND,
                        url=url,
                        service=service,
                        message="Task not found or expired on media-core",
                        is_logged=True,
                        critical=False,
                    )
                if res.status_code == 200:
                    status_data = res.json()
                    task_status = status_data.get("status")

                    # If still in queue or active or retry -> keep waiting
                    if task_status in ("pending", "active", "retry"):
                        continue
                    elif task_status in ("completed", "failed", "cancelled"):
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
        self._user_semaphores = defaultdict(lambda: asyncio.Semaphore(1))
        self._global_semaphore = asyncio.Semaphore(10)

        self._cancelled_users: set[int] = set()
        self._active_tasks: dict[int, asyncio.Task] = {}
        self._active_media_tasks: dict[int, str] = {}

    async def run_media_download(
        self,
        user_id: int,
        url: str,
        service: Services,
        payload: dict[str, Any],
        http_client: httpx.AsyncClient,
    ) -> dict:
        """
        Enqueues task to media-core via POST /enqueue and waits for result.
        Returns the data dictionary on success, or raises BotError on failure/cancellation.
        """
        self._cancelled_users.discard(user_id)
        media_core_url = settings.MEDIA_CORE_URL.rstrip("/")

        async with self._user_semaphores[user_id]:
            async with self._global_semaphore:
                # 1. Enqueue task
                try:
                    res = await http_client.post(
                        f"{media_core_url}/enqueue",
                        json=payload,
                        timeout=15.0,
                    )
                except Exception as e:
                    logger.error(f"Failed to connect to media-core /enqueue: {e}")
                    raise BotError(
                        code=ErrorCode.INTERNAL_ERROR,
                        url=url,
                        service=service,
                        message=f"Failed to connect to media-core: {e}",
                        is_logged=True,
                        critical=True,
                    )

                if res.status_code not in (200, 202):
                    err_text = res.text
                    logger.error(f"Media-core enqueue failed ({res.status_code}): {err_text}")
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
                        message=f"No task_id returned from media-core: {res.text}",
                        is_logged=True,
                        critical=True,
                    )

                self._active_media_tasks[user_id] = task_id

                try:
                    # 2. Wait for result
                    data = await wait_for_media_task(
                        task_id=task_id,
                        url=url,
                        service=service,
                        user_id=user_id,
                        http_client=http_client,
                    )
                    return data
                finally:
                    self._active_media_tasks.pop(user_id, None)
                    self._cancelled_users.discard(user_id)

    async def run_download(self, user_id: int, url: str, coro):
        """Legacy runner for coroutine-based downloads (e.g. lossless-core)."""
        self._cancelled_users.discard(user_id)

        async with self._user_semaphores[user_id]:
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
        Calls POST /cancel/{task_id} on media-core if a media task is running.
        Cancels asyncio.Task if a coroutine task is running.
        """
        self._cancelled_users.add(user_id)
        had_active = False

        # 1. Cancel active media-core task
        media_task_id = self._active_media_tasks.get(user_id)
        if media_task_id:
            had_active = True
            media_core_url = settings.MEDIA_CORE_URL.rstrip("/")
            client = http_client or httpx.AsyncClient()
            try:
                await client.post(
                    f"{media_core_url}/cancel/{media_task_id}",
                    timeout=5.0,
                )
            except Exception as e:
                logger.warning(f"Failed to send cancel to media-core for {media_task_id}: {e}")
            finally:
                if http_client is None:
                    await client.aclose()

        # 2. Cancel active asyncio task (lossless-core, etc.)
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


task_manager = TaskManager()
