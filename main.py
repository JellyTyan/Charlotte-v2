from dotenv import load_dotenv
import os

from core.config import Config
from core.logger import setup_logger
from core.bot_commands import set_default_commands
from utils.i18n import create_translator_hub
from middlewares.i18n import TranslatorRunnerMiddleware

load_dotenv()


async def main():
    logger = setup_logger()
    logger.info("🚀 Charlotte-v2 Bot starting...")

    logger.info("📁 Creating storage directories...")
    os.makedirs("storage/temp", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    logger.info("✅ Storage directories created")

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

    from middlewares.db import DbSessionMiddleware
    dp.update.middleware(DbSessionMiddleware(database_manager.async_session))

    translator_hub = create_translator_hub()

    dp["_translator_hub"] = translator_hub

    dp.update.middleware(TranslatorRunnerMiddleware())

    from middlewares.ban_check import BanCheckMiddleware
    dp.update.middleware(BanCheckMiddleware())

    from middlewares.button_owner import UserContextMiddleware, ButtonOwnerMiddleware
    dp.update.outer_middleware(UserContextMiddleware())
    dp.callback_query.middleware(ButtonOwnerMiddleware())

    logger.info("📊 Setting up rate limiter...")
    from middlewares.rate_limiter import RateLimiter
    dp.message.middleware(RateLimiter(rate=10, per=60))
    logger.info("✅ All middlewares registered")

    import core.error_handler
    logger.info("✅ Error handler registered")

    import modules
    from modules.router import service_router
    from modules.payment.handler import payment_router

    dp.include_router(payment_router)
    dp.include_router(service_router)

    import handlers
    logger.info("✅ All handlers registered")

    logger.info("⏰ Starting scheduled tasks...")
    from tasks.scheduled import start_scheduled_tasks
    start_scheduled_tasks()
    logger.info("✅ Scheduled tasks started")

    logger.info("📝 Setting default commands...")
    await set_default_commands()
    logger.info("✅ Default commands set")

    if config.TELEGRAM_LOCAL:
        logger.info("🌐 Starting webhook mode with local Telegram Bot API...")
        from aiohttp import web
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
        
        app = web.Application()
        webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_requests_handler.register(app, path=config.WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, config.WEBAPP_HOST, config.WEBAPP_PORT)
        await site.start()
        
        webhook_url = f"{config.WEBHOOK_HOST}{config.WEBHOOK_PATH}"
        await bot.set_webhook(url=webhook_url, drop_pending_updates=True)
        logger.info(f"✅ Webhook set to {webhook_url}")
        logger.info(f"🎉 Bot started in webhook mode on {config.WEBAPP_HOST}:{config.WEBAPP_PORT}")
        
        import asyncio
        await asyncio.Event().wait()
    else:
        logger.info("🎉 Bot successfully started and ready to receive messages!")
        await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
