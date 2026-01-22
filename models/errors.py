from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .service_list import Services


class ErrorCode(Enum):
    INVALID_URL = "E001"
    LARGE_FILE = "E002"
    SIZE_CHECK_FAIL = "E003"
    DOWNLOAD_FAILED = "E004"
    DOWNLOAD_CANCELLED = "E005"
    PLAYLIST_INFO_ERROR = "E006"
    SPONSORSHIP_ACTIVATE = "E007"
    METADATA_ERROR = "E008"
    SEND_ERROR = "E009"
    NOT_FOUND = "E404"
    INTERNAL_ERROR = "E500"

@dataclass
class BotError(Exception):
    code: ErrorCode  # For example: "E001"
    url: Optional[str] = None # Media URL
    service: Optional[Services] = None # Service name
    message: Optional[str] = None  # Message for Owner
    critical: bool = False # Send to owner?
    is_logged: bool = False # Need to be logged?
    send_user_message: bool = True # Send error message to user?

    def __str__(self):
        return f"[{self.code.value}] {self.message or 'No message'}" + (f" (URL: {self.url})" if self.url else "")
