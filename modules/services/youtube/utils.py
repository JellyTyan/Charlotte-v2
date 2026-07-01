import logging
import hashlib
import re
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from storage.db.crud import get_media_cache
from models.media import MediaContent, MediaType

logger = logging.getLogger(__name__)

YOUTUBE_ID_REGEX = re.compile(r"https?://(?:www\.)?(?:m\.)?(?:youtu\.be/|youtube\.com/(?:shorts/|watch\?v=))([\w-]+)")


def format_seconds_to_hhmmss(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_time_range(time_range_str: str) -> Optional[Tuple[str, str, int, int]]:
    """
    Parse a range string like '01:20-02:45', '1:30 - 2:45', '90-165' or '1:20 - inf'.

    Returns:
        tuple: (start_time_str, end_time_str, start_seconds, end_seconds) or None if invalid.
    """
    time_range_str = time_range_str.strip()
    parts = re.split(r"\s*to\s*|\s*-\s*", time_range_str, maxsplit=1)
    if len(parts) != 2:
        return None

    start_part, end_part = parts[0].strip(), parts[1].strip()

    def parse_part(part: str) -> Optional[int]:
        part = part.lower()
        if part == "inf" or part == "infinity" or part == "end":
            return -1

        # Check if digit-only seconds
        if part.isdigit():
            return int(part)

        # Check MM:SS or HH:MM:SS
        p_parts = part.split(":")
        try:
            int_parts = [int(p) for p in p_parts]
        except ValueError:
            return None

        if len(int_parts) == 1:
            return int_parts[0]
        elif len(int_parts) == 2:  # MM:SS
            m, s = int_parts
            if s < 0 or s >= 60 or m < 0:
                return None
            return m * 60 + s
        elif len(int_parts) == 3:  # HH:MM:SS
            h, m, s = int_parts
            if s < 0 or s >= 60 or m < 0 or m >= 60 or h < 0:
                return None
            return h * 3600 + m * 60 + s
        return None

    start_seconds = parse_part(start_part)
    end_seconds = parse_part(end_part)

    if start_seconds is None or end_seconds is None:
        return None

    if start_seconds < 0:
        return None

    if end_seconds != -1 and start_seconds >= end_seconds:
        return None

    start_formatted = format_seconds_to_hhmmss(start_seconds)
    end_formatted = "inf" if end_seconds == -1 else format_seconds_to_hhmmss(end_seconds)

    return start_formatted, end_formatted, start_seconds, end_seconds


def get_cache_key(url: str, height: int | str = 0, is_audio_only: bool = False, is_topich: bool = False) -> str:
    """Generate a unique cache key based on the video ID, target height, format type, and topich."""
    match = YOUTUBE_ID_REGEX.search(url)
    video_id = match.group(1) if match else url
    
    if is_topich:
        format_type = "topich"
    else:
        format_type = "audio" if is_audio_only else f"{height}p"

    base_str = f"{video_id}:{format_type}"
    hashed = hashlib.md5(base_str.encode('utf-8')).hexdigest()
    
    return f"youtube:{hashed}:topich" if is_topich else f"youtube:{hashed}"


async def cache_check(db_session: AsyncSession, key: str) -> List[MediaContent] | None:
    """Check if the given cache key exists in the database and return the MediaContent if found."""
    cached = await get_media_cache(db_session, key)
    if not cached:
        return None

    media_type = MediaType.AUDIO if "audio" in key else MediaType.VIDEO

    return [MediaContent(
        type=media_type,
        telegram_file_id=cached.telegram_file_id,
        telegram_document_file_id=cached.telegram_document_file_id,
        cover_file_id=cached.data.cover,
        full_cover_file_id=cached.data.full_cover,
        title=cached.data.title,
        performer=cached.data.author,
        duration=cached.data.duration,
        width=cached.data.width,
        height=cached.data.height,
        is_blurred=cached.data.is_blurred
    )]
