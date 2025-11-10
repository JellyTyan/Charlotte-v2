"""Global Bot Configuration"""

import os
from dataclasses import dataclass

@dataclass
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///charlotte.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", 0))
