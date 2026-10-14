import logging
import hashlib
import re
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from storage.db.crud import get_media_cache
from models.media import MediaContent, MediaType

logger = logging.getLogger(__name__)

YOUTUBE_ID_REGEX = re.compile(r"https?://(?:www\.)?(?:m\.)?(?:youtu\.be/|youtube\.com/(?:shorts/|watch\?v=))([\w-]+)")


def format_ms_to_hhmmss(ms: int) -> str:
    """90500 -> '00:01:30.500'; whole seconds stay 'HH:MM:SS' as before."""
    seconds, millis = divmod(ms, 1000)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    base = f"{h:02d}:{m:02d}:{s:02d}"
    return f"{base}.{millis:03d}" if millis else base


TIME_PART_REGEX = re.compile(r"([\d:]+)(?:[.,](\d{1,3}))?")


def parse_time_range(time_range_str: str) -> Optional[Tuple[str, str, float, float]]:
    """
    Parse a range string like '01:20-02:45', '1:30 - 2:45', '90-165', '1:20 - inf'
    or with milliseconds after a comma/dot: '1:20,5-1:22,250' (',5' = 500 ms).

    Returns:
        tuple: (start_time_str, end_time_str, start_seconds, end_seconds) or None if invalid.
        end_seconds is -1 for an open end.
    """
    time_range_str = time_range_str.strip()
    parts = re.split(r"\s*to\s*|\s*[-–—]\s*", time_range_str, maxsplit=1)
    if len(parts) != 2:
        return None

    start_part, end_part = parts[0].strip(), parts[1].strip()

    def parse_part(part: str) -> Optional[int]:
        """Returns milliseconds, -1 for an open end, None if invalid."""
        part = part.lower()
        if part in ("inf", "infinity", "end"):
            return -1

        match = TIME_PART_REGEX.fullmatch(part)
        if not match:
            return None
        clock, fraction = match.groups()
        millis = int(fraction.ljust(3, "0")) if fraction else 0

        try:
            int_parts = [int(p) for p in clock.split(":")]
        except ValueError:
            return None

        if len(int_parts) == 1:  # SS
            seconds = int_parts[0]
        elif len(int_parts) == 2:  # MM:SS
            m, s = int_parts
            if s >= 60:
                return None
            seconds = m * 60 + s
        elif len(int_parts) == 3:  # HH:MM:SS
            h, m, s = int_parts
            if s >= 60 or m >= 60:
                return None
            seconds = h * 3600 + m * 60 + s
        else:
            return None
        return seconds * 1000 + millis

    start_ms = parse_part(start_part)
    end_ms = parse_part(end_part)

    if start_ms is None or end_ms is None or start_ms < 0:
        return None

    if end_ms != -1 and start_ms >= end_ms:
        return None

    start_formatted = format_ms_to_hhmmss(start_ms)
    end_formatted = "inf" if end_ms == -1 else format_ms_to_hhmmss(end_ms)

    return start_formatted, end_formatted, start_ms / 1000, -1 if end_ms == -1 else end_ms / 1000


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
