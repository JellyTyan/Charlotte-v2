from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .service_list import Services


class ErrorCode(Enum):
    INVALID_URL = "E001"          # Ссылка неправильная или неподдерживаемая
    LARGE_FILE = "E002"           # Файл слишком большой для отправки
    DOWNLOAD_CANCELLED = "E003"   # Загрузка отменена пользователем
    NOT_FOUND = "E004"            # Ничего не найдено (пост удален или ошибка метаданных)
    NOT_ALLOWED = "E005"          # Отключено/запрещено в настройках чата
    INTERNAL_ERROR = "E006"       # Ошибка на стороне сервера / скачивания
    AGE_RESTRICTED = "E007"       # Возрастные ограничения (18+)
    PRIVATE_CONTENT = "E008"      # Приватный контент (требуется авторизация)
    REGION_RESTRICTED = "E009"    # Ограничено по региону (geoblock)



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
