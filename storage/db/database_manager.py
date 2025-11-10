import logging
import os

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from .models import Base

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO)
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
        # db_url = "postgresql+asyncpg://charlotte:charlottepass@localhost/charlotte"
        echo = os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true"

        self.engine = create_async_engine(db_url, echo=echo, future=True)
        self.async_session = async_sessionmaker(self.engine, expire_on_commit=False)

        logger.info("Подключение к базе данных успешно")
        self._initialized = True

    async def init_db(self):
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("База данных инициализирована")
        except SQLAlchemyError as e:
            logger.exception(f"Ошибка при инициализации базы данных: {e}")

    async def close(self):
        await self.engine.dispose()
        logger.info("Подключение к базе данных закрыто")
