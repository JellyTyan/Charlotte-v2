import asyncio
import logging
from pathlib import Path
from typing import Optional

import aiofiles
from curl_cffi.requests import AsyncSession, RequestsError

from models.errors import BotError, ErrorCode

logger = logging.getLogger(__name__)


async def download_file(
    url: str,
    filename: str,
    max_size: int = 0,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    cookies: Optional[dict] = None,
    client: Optional[AsyncSession] = None,
) -> Optional[Path]:
    from utils.url_validator import validate_url
    if not validate_url(url):
        raise BotError(
            code=ErrorCode.INVALID_URL,
            message="Domain not allowed",
            url=url
        )

    retries = 3

    for attempt in range(retries):
        try:
            if client is None:
                async with AsyncSession(impersonate="chrome136") as temp_client:
                    return await _download_with_client(
                        temp_client, url, filename, params, headers, cookies, max_size
                    )
            else:
                return await _download_with_client(
                    client, url, filename, params, headers, cookies, max_size
                )

        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(0.5)
            else:
                raise e

    return None


async def _download_with_client(
    client: AsyncSession,
    url: str,
    filename: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    cookies: Optional[dict] = None,
    max_size: int = 1024,
) -> Path:
    try:
        response = await client.get(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            stream=True,
        )
    except RequestsError as e:
        raise BotError(
            code=ErrorCode.DOWNLOAD_FAILED,
            message=f"Network error: {str(e)}",
            url=url,
            critical=False,
            is_logged=True,
        )

    if response.status_code != 200:
        await response.aclose()
        raise BotError(
            code=ErrorCode.DOWNLOAD_FAILED,
            message=f"Failed to download file: {response.status_code}",
            url=url,
            critical=False,
            is_logged=True,
        )

    content_length = response.headers.get("Content-Length")
    if content_length:
        content_length = int(content_length)
        if max_size and content_length > max_size:
            await response.aclose()
            raise BotError(
                code=ErrorCode.SIZE_CHECK_FAIL,
                url=url,
                critical=False,
            )

    total_written = 0

    async with aiofiles.open(filename, "wb") as f:
        async for chunk in response.aiter_content():
            total_written += len(chunk)

            if max_size and total_written > max_size:
                await response.aclose()
                raise BotError(
                    code=ErrorCode.SIZE_CHECK_FAIL,
                    url=url,
                    critical=False,
                )

            await f.write(chunk)

    return Path(filename)
