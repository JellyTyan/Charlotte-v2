import asyncio
import json
import logging
import os
import random
import shutil
from typing import List

from models.errors import BotError, ErrorCode
from yt_dlp.utils import sanitize_filename

logger = logging.getLogger(__name__)


def get_ytdlp_options():
    return {
        "outtmpl": f"temp/%(id)s_{sanitize_filename('%(title)s')}.%(ext)s",
        "noplaylist": True,
        "geo_bypass": True,
        "age_limit": 99,
        "retries": 10,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "no_exec": True,
    }


async def get_gallery_dl_info(url: str) -> List[dict]:
    """
    Executes gallery-dl to fetch metadata for a given URL.
    Returns a list of dictionaries containing the metadata.
    """
    from utils.url_validator import validate_url

    if not validate_url(url):
        raise BotError(code=ErrorCode.INVALID_URL, message="Domain not allowed")

    gallery_dl_exe = shutil.which("gallery-dl")
    if not gallery_dl_exe:
         venv_path = os.path.join(os.getcwd(), "venv", "bin", "gallery-dl")
         if os.path.exists(venv_path):
             gallery_dl_exe = venv_path

    if not gallery_dl_exe:
        raise BotError(code=ErrorCode.INTERNAL_ERROR, message="gallery-dl not found")

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
            return []

        output = stdout.decode().strip()
        data = []

        try:
            parsed = json.loads(output)
            if isinstance(parsed, list):
                data = parsed
            else:
                data = [parsed]
        except json.JSONDecodeError:
            for line in output.splitlines():
                if line.strip():
                    try:
                        data.append(json.loads(line))
                    except:
                        pass
        return data

    except Exception as e:
        logger.error(f"Error executing gallery-dl: {e}")
        return []
