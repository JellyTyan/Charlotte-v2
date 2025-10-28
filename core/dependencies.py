"""Зависимости для хэндлеров"""

from typing import Dict, Any
from core.config import Config
import logging

def get_config(data: Dict[str, Any]) -> Config:
    """Получение конфига из workflow_data"""
    return data["config"]

def get_logger(data: Dict[str, Any]) -> logging.Logger:
    """Получение логгера из workflow_data"""
    return data["logger"]