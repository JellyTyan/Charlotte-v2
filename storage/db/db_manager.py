import logging
import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .models import Base

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger(__name__)


class DatabaseManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://charlotte:charlottepass@localhost/charlotte")
        echo = os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true"
        pool_size = int(os.getenv("DB_POOL_SIZE", "20"))
        max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        pool_timeout = int(os.getenv("DB_POOL_TIMEOUT", "30"))

        self.engine = create_async_engine(
            db_url,
            echo=echo,
            future=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=1800,
            pool_pre_ping=True,
        )
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)

        logger.info("Connection to the database successful")
        self._initialized = True

    async def init_db(self):
        try:
            async with self.engine.begin() as conn:
                # нужен для GIN-индекса gin_trgm_ops на user_saves.label
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
                await conn.run_sync(Base.metadata.create_all)
            logger.info("The database has been initialized.")
        except SQLAlchemyError as e:
            logger.exception(f"Error during database initialization: {e}")

    async def close(self):
        await self.engine.dispose()
        logger.info("Connection to the database is closed")
