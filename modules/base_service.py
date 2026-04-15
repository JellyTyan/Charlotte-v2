from abc import ABC, abstractmethod
from models.metadata import MediaMetadata
# todo Remade base service
class BaseService(ABC):
    @abstractmethod
    async def download(self, url: str, *args, **kwargs) -> list:
        """Downloads media"""
        pass

    @abstractmethod
    async def get_info(self, url: str, *args, **kwargs) -> MediaMetadata|None:
        """Getting info about media"""
        pass
