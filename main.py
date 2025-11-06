from dotenv import load_dotenv
load_dotenv()

from aiogram import Bot, Dispatcher
from core.config import Config
from core.logger import setup_logger
from core.bot_commands import set_default_commands

async def main():
    logger = setup_logger()
    logger.info("🚀 Charlotte-v2 Bot starting...")

    logger.info("📋 Loading configuration...")
    config = Config()
    logger.info(f"✅ Configuration loaded. Admin ID: {config.ADMIN_ID}")

    logger.info("🤖 Initializing Bot and Dispatcher...")
    from core.loader import dp, bot

    # Получаем информацию о боте
    bot_info = await bot.get_me()
    logger.info(f"✅ Bot initialized: @{bot_info.username} ({bot_info.first_name})")

    logger.info("⚙️ Setting up workflow data...")
    dp.workflow_data.update(config=config, logger=logger)

    # Регистрация хэндлеров
    from bot.handlers import start

    logger.info("📝 Setting default commands...")
    await set_default_commands()
    logger.info("✅ Default commands set")

    logger.info("🎉 Bot successfully started and ready to receive messages!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
