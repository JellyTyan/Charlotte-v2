from abc import ABC, abstractmethod
from typing import Dict, Any
from models.metadata_models import MediaMetadata

class BaseService(ABC):
    @abstractmethod
    async def download(self, url: str, *args, **kwargs) -> list:
        """Downloads media"""
        pass

    @abstractmethod
    async def get_info(self, url: str) -> MediaMetadata|None:
        """Getting info about media"""
        pass
