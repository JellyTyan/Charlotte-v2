from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class MediaType(Enum):
    VIDEO = "video"
    PHOTO = "photo"
    AUDIO = "audio"
    GIF = "gif"

@dataclass
class MediaContent:
    type: MediaType
    path: Optional[Path] = None
    content: Optional[bytes] = None
    telegram_file_id: Optional[str] = None
    telegram_document_file_id: Optional[str] = None
    cover_file_id: Optional[str] = None
    full_cover_file_id: Optional[str] = None
    filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    title: Optional[str] = None
    cover: Optional[Path] = None
    full_cover: Optional[Path] = None
    performer: Optional[str] = None
    is_blurred: bool | None = None

