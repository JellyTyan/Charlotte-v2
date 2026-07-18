import asyncio
import os

import httpx
from aiogram_dialog import setup_dialogs
from dotenv import load_dotenv

from core.bot_commands import set_default_commands
from core.config import settings
from core.error_handler import register_error_handler
from core.loader import create_bot_and_dispatcher
from core.logger import setup_logger
from handlers import user_router, admin_router
from middlewares.ban_check import BanCheckMiddleware
from middlewares.button_owner import UserContextMiddleware, ButtonOwnerMiddleware
from middlewares.db import DbSessionMiddleware
from middlewares.force_edit_show_mode import ForceEditShowModeMiddleware
from middlewares.i18n import TranslatorRunnerMiddleware
from middlewares.rate_limiter import RateLimiter
from modules.inline.handler import inline_router
from modules.payment.router import payment_router
from modules.services.router import service_router
from storage.cache.redis_client import init_redis
from storage.db import database_manager
from tasks.scheduled import start_scheduled_tasks
from utils.i18n import create_translator_hub

load_dotenv()


async def main():
    logger = setup_logger()
    logger.info("🚀 Charlotte-v2 Bot starting...")

    logger.info("📁 Creating storage directories...")
    os.makedirs("storage/temp", exist_ok=True)
    logger.info("✅ Storage directories created")

    logger.info("📋 Initializing DataBase...")
    await database_manager.init_db()

    logger.info("📋 Initializing Redis Client...")
    await init_redis()

    logger.info("📋 Loading configuration...")
    logger.info(f"✅ Configuration loaded. Admin ID: {settings.ADMIN_ID}")

    logger.info("🤖 Initializing Bot and Dispatcher...")
    bot, dp = create_bot_and_dispatcher(settings)

    bot_info = await bot.get_me()
    logger.info(f"✅ Bot initialized: @{bot_info.username} ({bot_info.first_name})")

    logger.info("⚙️ Setting up workflow data...")
    core_client = httpx.AsyncClient(
        base_url=settings.LOSSLESS_CORE_URL,
        timeout=None,
    )
    dp.workflow_data.update(
        http_client=core_client,
        config=settings,
        logger=logger,
    )

    logger.info("⚙️ Setting up middlewares...")
    translator_hub = create_translator_hub()
    dp["_translator_hub"] = translator_hub

    dp.update.middleware(DbSessionMiddleware(database_manager.async_session))
    dp.update.middleware(TranslatorRunnerMiddleware())
    dp.update.middleware(BanCheckMiddleware())
    dp.update.outer_middleware(UserContextMiddleware())
    dp.callback_query.middleware(ButtonOwnerMiddleware())
    dp.message.middleware(RateLimiter(rate=10, per=60))
    logger.info("✅ All middlewares registered")

    logger.info("⚙️ Registering routers...")
    dp.include_router(user_router)
    dp.include_router(payment_router)
    dp.include_router(admin_router)
    dp.include_router(inline_router)
    dp.include_router(service_router)

    setup_dialogs(dp)
    dp.update.outer_middleware(ForceEditShowModeMiddleware())
    logger.info("✅ All handlers registered")

    register_error_handler(dp, bot)
    logger.info("✅ Error handler registered")

    logger.info("⏰ Starting scheduled tasks...")
    start_scheduled_tasks(bot)
    logger.info("✅ Scheduled tasks started")

    logger.info("📝 Setting default commands...")
    await set_default_commands(bot)
    logger.info("✅ Default commands set")

    dp.shutdown.register(on_shutdown)

    logger.info("🎉 Bot successfully started and ready to receive messages!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, skip_updates=True)


async def on_shutdown(dispatcher):
    core_client: httpx.AsyncClient = dispatcher.workflow_data.get("http_client")
    if core_client:
        await core_client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
