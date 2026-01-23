import asyncio
import json
import logging
import os
import random
import shutil
import time
from typing import List, Optional

import httpx

from models.errors import BotError, ErrorCode
from utils.user_agents import get_user_agent
from yt_dlp.utils import sanitize_filename
from yt_dlp.networking.impersonate import ImpersonateTarget

logger = logging.getLogger(__name__)

# Rate limiter for TikWM
_tikwm_lock = asyncio.Lock()
_last_tikwm_request_time = 0.0


def random_cookie_file():
    try:
        cookie_dir = "storage/cookies/tiktok"
        if not os.path.exists(cookie_dir):
            return None

        cookie_files = [f for f in os.listdir(cookie_dir) if f.endswith('.txt')]
        return f"{cookie_dir}/{random.choice(cookie_files)}" if cookie_files else None
    except (OSError, IndexError):
        return None


def get_ytdlp_options():
    cookie_file = random_cookie_file()
    return {
        "outtmpl": f"temp/%(id)s_{sanitize_filename('%(title)s')}.%(ext)s",
        "cookiefile": cookie_file,
        "retries": 10,
        "restrictfilenames": True,
        'impersonate': ImpersonateTarget(client='chrome'),
        'referer': 'https://www.tiktok.com/',
        "user_agent": get_user_agent(),
    }


async def get_gallery_dl_info(url: str) -> Optional[dict]:
    """
    Fetches data from gallery-dl.
    Returns the simplified info dict (from the first element's second item).
    """
    from utils.url_validator import validate_url

    if not validate_url(url):
        logger.warning(f"Invalid URL for gallery-dl: {url}")
        return None

    gallery_dl_exe = shutil.which("gallery-dl")
    if not gallery_dl_exe:
         venv_path = os.path.join(os.getcwd(), "venv", "bin", "gallery-dl")
         if os.path.exists(venv_path):
             gallery_dl_exe = venv_path

    if not gallery_dl_exe:
        logger.error("gallery-dl not found")
        return None

    cmd = [gallery_dl_exe, "--dump-json", url]

    try:
        logger.debug(f"Running gallery-dl: {' '.join(cmd)}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            logger.error(f"gallery-dl error: {stderr.decode()}")
            return None

        output = stdout.decode().strip()
        if not output:
            return None

        # Parse logic: expect [[type, data], ...]
        # We want data[0][1]
        try:
            data = json.loads(output)
            if isinstance(data, list) and len(data) > 0:
                first_item = data[0]
                if isinstance(first_item, list) and len(first_item) > 1:
                    return first_item[1]
            return None # Structure mismatch
        except json.JSONDecodeError:
            # Fallback if multiple JSONs (gallery-dl default sometimes)
            # Try to parse first line -> should be [type, data]
            lines = output.splitlines()
            if lines:
                try:
                    first_line_json = json.loads(lines[0])
                    if isinstance(first_line_json, list) and len(first_line_json) > 1:
                        return first_line_json[1]
                except:
                    pass
            return None

    except Exception as e:
        logger.error(f"Error executing gallery-dl: {e}")
        return None


async def get_tikwm_info(url: str):
    global _last_tikwm_request_time

    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'ru',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://www.tikwm.com',
        'referer': 'https://www.tikwm.com/ru/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36',
    }

    data = {
        'url': url,
        'count': '12',
        'cursor': '0',
        'web': '1',
        'hd': '1',
    }

    async with _tikwm_lock:
        current_time = time.time()
        time_since_last_request = current_time - _last_tikwm_request_time
        if time_since_last_request < 1.0:
            await asyncio.sleep(1.0 - time_since_last_request)

        _last_tikwm_request_time = time.time()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://www.tikwm.com/api/",
                headers=headers,
                data=data
            )
            return response.json()


async def convert_video(input_path: str, output_path: str) -> bool:
    """
    Converts/Remuxes video using FFmpeg to fix container issues.
    """
    ffmpeg_exe = shutil.which("ffmpeg")
    if not ffmpeg_exe:
        logger.error("ffmpeg not found")
        return False

    cmd = [
        ffmpeg_exe,
        "-i", input_path,
        "-c", "copy",
        "-map", "0",
        "-y",
        output_path
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logger.error(f"FFmpeg conversion failed: {stderr.decode()}")
            return False

        return True
    except Exception as e:
        logger.error(f"Error executing ffmpeg: {e}")
        return False
