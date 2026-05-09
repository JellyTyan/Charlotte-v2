import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.fsm.storage.redis import DefaultKeyBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from storage.cache.redis_client import redis_client

from core.config import Config

config = Config()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is not set")

session = None
if config.TELEGRAM_LOCAL:
    session = AiohttpSession(
        api=TelegramAPIServer.from_base(config.TELEGRAM_SERVER_URL, is_local=True)
    )

# Initialize the Telegram bot with the given token and parse mode set to HTML
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    session=session
)

# Initialize memory storage for the dispatcher
if redis_client is not None:
    storage = RedisStorage(redis=redis_client, key_builder=DefaultKeyBuilder(with_destiny=True))
else:
    storage = MemoryStorage()

# Initialize the dispatcher with the memory storage
dp = Dispatcher(storage=storage)
