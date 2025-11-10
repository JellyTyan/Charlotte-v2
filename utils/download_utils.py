import logging
import asyncio
from pathlib import Path
from typing import Optional
import httpx
import aiofiles
from models.error_models import BotError, ErrorCode

logger = logging.getLogger(__name__)


async def download_file(
    url: str,
    filename: str,
    max_size: int = 0,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    cookies: Optional[dict] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> Optional[Path]:
    retries = 3

    for attempt in range(retries):
        try:
            if client is None:
                async with httpx.AsyncClient() as temp_client:
                    return await _download_with_client(
                        temp_client, url, filename, params, headers, cookies, max_size
                    )
            else:
                return await _download_with_client(
                    client, url, filename, params, headers, cookies, max_size
                )

        except (httpx.RequestError, BotError) as e:
            if attempt < retries - 1:
                await asyncio.sleep(0.5)
            else:
                raise e

    return None


async def _download_with_client(
    client: httpx.AsyncClient,
    url: str,
    filename: str,
    params: Optional[dict],
    headers: Optional[dict],
    cookies: Optional[dict],
    max_size: int = 100,
) -> Path:
    async with client.stream(
        "GET",
        url,
        params=params,
        headers=headers,
        cookies=cookies,
    ) as response:

        if response.status_code != 200:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Failed to download file: {response.status_code}",
                url=url,
                critical=False,
                is_logged=True,
            )

        content_length = int(response.headers.get("Content-Length", 0))
        if max_size and content_length and content_length > max_size:
            raise BotError(
                code=ErrorCode.SIZE_CHECK_FAIL,
                url=url,
                critical=False,
            )

        total_written = 0
        async with aiofiles.open(filename, "wb") as f:
            async for chunk in response.aiter_bytes(1024):
                total_written += len(chunk)
                if max_size and total_written > max_size:
                    raise BotError(
                        code=ErrorCode.SIZE_CHECK_FAIL,
                        url=url,
                        critical=False,
                    )
                await f.write(chunk)

    return Path(filename)
