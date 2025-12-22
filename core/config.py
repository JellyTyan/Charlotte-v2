"""Global Bot Configuration"""

import os
from dataclasses import dataclass

@dataclass
class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///charlotte.db")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", 0))
    SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_SECRET: str = os.getenv("SPOTIFY_SECRET", "")
    APPLE_MUSIC_TOKEN: str = os.getenv("APPLEMUSIC_DEV_TOKEN", "")
