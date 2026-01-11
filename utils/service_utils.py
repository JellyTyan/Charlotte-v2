import logging
import asyncio
import os
import random
import uuid
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from models.errors import BotError, ErrorCode

from ytmusicapi import YTMusic

logger = logging.getLogger(__name__)


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
        "allowed_extractors": ["youtube", "youtubetab", "soundcloud", "reddit"],
        "extractor_args": {
                "youtube": {
                    "player_client": ["tv", "web_safari", "web_embedded"]
                },
                "youtubepot-bgutilhttp": {
                    "base_url": ["http://bgutil:4416"]
                }
            }
    }


def get_audio_options(title: str | None = None):
    opts = get_ytdlp_options()
    opts["format"] = "bestaudio"
    if title:
        opts["outtmpl"] = f"storage/temp/{transliterate(title)}.%(ext)s"
    else:
        opts["outtmpl"] = f"storage/temp/{uuid.uuid4()}.%(ext)s"
    opts["postprocessors"] = [
        {
            'key': 'SponsorBlock',
            'api': 'https://sponsor.ajay.app',
            'categories': ['sponsor', 'intro', 'outro', 'selfpromo', 'preview', 'interaction', 'filler'],
        },
        {
            'key': 'ModifyChapters',
            'remove_sponsor_segments': ['sponsor', 'intro', 'outro', 'selfpromo', 'preview', 'interaction', 'filler']
        },
        {
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }
    ]

    cookie_file = random_cookie_file("youtube")
    if cookie_file:
        opts["cookiefile"] = cookie_file

    return opts
