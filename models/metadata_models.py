from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from aiogram.types import InlineKeyboardMarkup


class MetadataType(Enum):
    """MetadataType
Selecting the metadata received from the service.

The METADATA type indicates that the data requires further processing on our side.

The AUTODOWNLOAD type signifies that the service has already downloaded the content and it can be sent immediately without any post-processing.

The ERROR type indicates that an error has occurred and must be handled accordingly.
    """
    METADATA = "metadata"        # regular metadata
    AUTODOWNLOAD = "autodownload" # auto-download immediately
    ERROR = "error"              # error occurred


@dataclass
class MediaMetadata:
    type: MetadataType                       # metadata type
    url: str                                 # original URL

    # General info
    title: str | None = None                 # title
    description: str | None = None           # description
    duration: int | None = None              # duration (sec)
    cover: str | None = None                 # thumbnail
    full_size_cover: str | None = None       # HQ thumbnail
    performer: str | None = None             # artist/author
    performer_url: str | None = None
    width: int | None = None                 # width (video/image)
    height: int | None = None                # height

    # Extra service-specific info
    extra: dict = field(default_factory=dict)

    # Media type
    media_type: Literal[
        "video", "audio", "playlist",
        "album", "track", "gallery", "unknown"
    ] = "unknown"

    # Attachments and nested items
    attachments: list["MediaAttachment"] = field(default_factory=list) # formats/files
    items: list["MediaMetadata"] = field(default_factory=list)         # nested objects (e.g. playlist tracks)

    # UI
    keyboard: InlineKeyboardMarkup | None = None # inline buttons
    message: str | None = None                     # response message


@dataclass
class MediaAttachment:
    url: str                                 # direct file/format URL
    format_id: str | None = None             # format ID (yt-dlp etc.)
    mime_type: str | None = None             # MIME type
    size_mb: float | None = None             # file size in MB
    width: int | None = None                 # width (video/image)
    height: int | None = None                # height
    bitrate: int | None = None               # bitrate (audio/video)

    # Extra service-specific info
    extra: dict = field(default_factory=dict)
