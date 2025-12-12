from dotenv import load_dotenv
load_dotenv()

from core.config import Config
from core.logger import setup_logger
from core.bot_commands import set_default_commands
from utils.i18n import create_translator_hub
from middlewares.i18n import TranslatorRunnerMiddleware


async def main():
    logger = setup_logger()
    logger.info("🚀 Charlotte-v2 Bot starting...")

    logger.info("📋 Initializing DataBase...")
    from storage.db import database_manager
    await database_manager.init_db()

    logger.info("📋 Initializing Redis Client...")
    from storage.cache.redis_client import init_redis
    await init_redis()

    logger.info("📋 Loading configuration...")
    config = Config()
    logger.info(f"✅ Configuration loaded. Admin ID: {config.ADMIN_ID}")

    logger.info("🤖 Initializing Bot and Dispatcher...")
    from core.loader import dp, bot

    bot_info = await bot.get_me()
    logger.info(f"✅ Bot initialized: @{bot_info.username} ({bot_info.first_name})")

    logger.info("⚙️ Setting up workflow data...")
    dp.workflow_data.update(config=config, logger=logger)

    logger.info("⚙️ Setting up translation...")
    translator_hub = create_translator_hub()

    dp["_translator_hub"] = translator_hub

    dp.update.middleware(TranslatorRunnerMiddleware())

    import core.error_handler
    logger.info("✅ Error handler registered")


    import modules
    from modules.router import service_router
    dp.include_router(service_router)

    import handlers
    logger.info("✅ All handlers registered")

    logger.info("📝 Setting default commands...")
    await set_default_commands()
    logger.info("✅ Default commands set")

    logger.info("🎉 Bot successfully started and ready to receive messages!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
