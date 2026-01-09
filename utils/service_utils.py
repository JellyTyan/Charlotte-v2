import logging
import asyncio
import os
import random
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from models.errors import BotError, ErrorCode

from ytmusicapi import YTMusic

logger = logging.getLogger(__name__)


_search_executor = ThreadPoolExecutor(max_workers=5)

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


def get_ytdlp_options():
    return {
        "noplaylist": True,
        "geo_bypass": True,
        "age_limit": 99,
        "retries": 10,
        "restrictfilenames": True,
        "no_exec": True,
        "allowed_extractors": ["youtube", "youtubetab", "soundcloud"],
        "extractor_args": {
                "youtube": {
                    "player_client": ["tv", "web_safari", "web_embedded"]
                },
                "youtubepot-bgutilhttp": {
                    "base_url": ["http://bgutil:4416"]
                }
            }
    }
