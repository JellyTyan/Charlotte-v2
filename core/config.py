"""Global Bot Configuration"""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Config(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    ADMIN_ID: int
    DUMP_CHANNEL_ID: int
    TELEGRAM_API_ID: str
    TELEGRAM_API_HASH: str
    TELEGRAM_LOCAL: bool
    TELEGRAM_SERVER_URL: str
    LOSSLESS_CORE_URL: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @classmethod
    def instance(cls) -> "Config":
        return settings


settings = Config()