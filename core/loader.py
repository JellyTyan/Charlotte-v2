import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import DefaultKeyBuilder, RedisStorage

from core.config import Config

bot: Bot | None = None
dp: Dispatcher | None = None


def create_bot_and_dispatcher(config: Config) -> tuple[Bot, Dispatcher]:
    global bot, dp

    from storage.cache.redis_client import redis_client

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN is not set")

    session = None
    if config.TELEGRAM_LOCAL:
        session = AiohttpSession(
            api=TelegramAPIServer.from_base(config.TELEGRAM_SERVER_URL, is_local=True)
        )

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session,
    )

    storage = (
        RedisStorage(redis=redis_client, key_builder=DefaultKeyBuilder(with_destiny=True))
        if redis_client is not None
        else MemoryStorage()
    )

    dp = Dispatcher(storage=storage)
    return bot, dp