"""Репозиторий для работы с данными"""

from typing import Optional, Dict, Any

class Repository:
    async def save_user(self, user_id: int, data: Dict[str, Any]) -> None:
        """Сохранение данных пользователя"""
        pass
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение данных пользователя"""
        pass