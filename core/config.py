"""Global Bot Configuration"""

import os
from dataclasses import dataclass

@dataclass
class Config:
    DATABASE_URL: str = os.getenv("DATABASE_URL", os.getenv("DB_URL", "sqlite:///charlotte.db"))
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    ADMIN_ID: int = int(os.getenv("ADMIN_ID", 0))
    SPOTIFY_CLIENT_ID: str = os.getenv("SPOTIFY_CLIENT_ID", "")
    SPOTIFY_SECRET: str = os.getenv("SPOTIFY_SECRET", "")
    APPLE_MUSIC_TOKEN: str = os.getenv("APPLEMUSIC_DEV_TOKEN", "")
    TWITTER_CSRF_TOKEN: str = os.getenv("CSRF_TOKEN", "")
    TWITTER_AUTH_TOKEN: str = os.getenv("AUTH_TOKEN", "")

    # Telegram API Server Config
    TELEGRAM_API_ID: str = os.getenv("TELEGRAM_API_ID", "")
    TELEGRAM_API_HASH: str = os.getenv("TELEGRAM_API_HASH", "")
    TELEGRAM_LOCAL: bool = os.getenv("TELEGRAM_LOCAL", "False").lower() == "true"
    TELEGRAM_SERVER_URL: str = os.getenv("TELEGRAM_SERVER_URL", "http://nginx:80")
