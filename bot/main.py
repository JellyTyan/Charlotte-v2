"""Точка входа для Telegram бота Charlotte-v2"""

from aiogram import Bot, Dispatcher
from core.config import Config
from core.logger import setup_logger

async def main():
    config = Config()
    logger = setup_logger()

    logger.info("Bot is starting...")
    
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
    
    # Передаем конфиг через workflow_data
    dp.workflow_data.update(config=config, logger=logger)
    
    # Регистрация хэндлеров
    from bot.handlers import universal, youtube, playlist, premium, admin
    
    logger.info("Bot is started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())