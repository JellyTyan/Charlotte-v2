"""Базовый класс для сервисов"""

from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseService(ABC):
    @abstractmethod
    async def download(self, url: str, **kwargs) -> Dict[str, Any]:
        """Скачивание контента"""
        pass
    
    @abstractmethod
    async def get_info(self, url: str) -> Dict[str, Any]:
        """Получение информации о контенте"""
        pass