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
    filename: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[int] = None
    title: Optional[str] = None
    cover: Optional[Path] = None
    full_cover: Optional[Path] = None
    performer: Optional[str] = None
    original_size: Optional[bool] = None
    is_blured: bool | None = None
