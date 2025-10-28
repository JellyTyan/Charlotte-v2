from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from config.secrets import BOT_TOKEN
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer

# Initialize the Telegram bot with the given token and parse mode set to HTML
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

# Initialize memory storage for the dispatcher
storage = MemoryStorage()

# Initialize the dispatcher with the memory storage
dp = Dispatcher(storage=storage)