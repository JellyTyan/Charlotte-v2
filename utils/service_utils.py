import asyncio
import os
import random
import uuid
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import httpx
from models.errors import BotError, ErrorCode
from models.service_list import Services


_search_executor = ThreadPoolExecutor(max_workers=5)


CYRILLIC_TO_LATIN = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo', 'ж': 'zh',
    'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o',
    'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu',
    'я': 'ya',
    'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh',
    'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N', 'О': 'O',
    'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'Ts',
    'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu',
    'Я': 'Ya'
}


def transliterate(text: str) -> str:
    return ''.join(CYRILLIC_TO_LATIN.get(c, c) for c in text)

async def search_music(performer: str, title: str) -> Optional[str]:
    try:
        loop = asyncio.get_running_loop()
        yt = await loop.run_in_executor(
            _search_executor,
            YTMusic
        )

        search_results = await loop.run_in_executor(
            _search_executor,
            lambda: yt.search(f"{performer} - {title}", limit=10, filter="songs")
        )

        for track in search_results:
            if not track.get('duration'):
                continue

            if track['duration_seconds'] <= 600:
                return f"https://music.youtube.com/watch?v={track['videoId']}"

        raise BotError(
            code=ErrorCode.NOT_FOUND,
            message=f"Failed to search music for {performer} - {title}",
            critical=False,
            is_logged=True
        )

    except BotError:
        raise
    except Exception as e:
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Failed to search music",
            critical=True,
            is_logged=True
        )


def random_cookie_file(path: str) -> Optional[str]:
    try:
        cookie_dir = f"storage/cookies/{path}"
        if not os.path.exists(cookie_dir):
            return None

        cookie_files = [f for f in os.listdir(cookie_dir) if f.endswith('.txt')]
        return f"{cookie_dir}/{random.choice(cookie_files)}" if cookie_files else None
    except (OSError, IndexError):
        return None


def handle_lossless_response(response: httpx.Response, url: str, service: Services) -> dict:
    """
    Parses response from lossless-core, maps error codes to ErrorCode enum,
    and raises structured BotError on failure.
    """
    data = None
    try:
        data = response.json()
    except Exception:
        pass

    is_error = False
    error_code_str = None
    error_msg = None

    if data and isinstance(data, dict):
        if data.get("status") == "error" or response.status_code != 200:
            is_error = True
            err_obj = data.get("error", {})
            if isinstance(err_obj, dict):
                error_code_str = err_obj.get("code")
                error_msg = err_obj.get("message")
            if not error_msg:
                error_msg = data.get("message")
    elif response.status_code != 200:
        is_error = True
        error_msg = response.text

    if not is_error:
        if data and "data" in data:
            return data["data"]
        return data

    # Default fallback mapped code
    mapped_code = ErrorCode.INTERNAL_ERROR

    if error_code_str:
        if error_code_str in ("UNSUPPORTED_SERVICE", "INVALID_INPUT"):
            mapped_code = ErrorCode.INVALID_URL
        elif error_code_str == "TRACK_NOT_FOUND":
            mapped_code = ErrorCode.NOT_FOUND
        elif error_code_str == "PREVIEW_ONLY":
            mapped_code = ErrorCode.PREVIEW_ONLY
        # DOWNLOAD_FAILED, LOSSLESS_FAILED → INTERNAL_ERROR (default)
    else:
        # Fallback based on HTTP status code
        if response.status_code == 400:
            mapped_code = ErrorCode.INVALID_URL
        elif response.status_code == 404:
            mapped_code = ErrorCode.NOT_FOUND
        elif response.status_code == 422:
            mapped_code = ErrorCode.PREVIEW_ONLY
        # 500/502/503 → INTERNAL_ERROR (default)

    # Check for region restriction in error message (overrides above)
    if error_msg:
        err_lower = error_msg.lower()
        if any(keyword in err_lower for keyword in ("geo", "country", "region", "geoblock")):
            mapped_code = ErrorCode.REGION_RESTRICTED

    raise BotError(
        code=mapped_code,
        url=url,
        service=service,
        message=f"Lossless Core Error ({response.status_code}): {error_msg or 'Unknown error'}",
        is_logged=True,
        critical=False,
    )

