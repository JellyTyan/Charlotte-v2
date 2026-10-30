"""Scheduled tasks for maintenance"""
import asyncio
import datetime
import logging
import time
from pathlib import Path

from aiogram import Bot
from sqlalchemy import delete

from tasks.music_refresh import music_refresh_loop
from utils.url_cache import cleanup_expired as cleanup_expired_urls

logger = logging.getLogger(__name__)


async def cleanup_old_statistics():
    """Clean statistics older than 90 days - runs daily"""
    while True:
        try:
            await asyncio.sleep(86400)  # 24 hours
            
            from storage.db import database_manager
            from storage.db.models import Statistics
            
            async with database_manager.async_session() as session:
                cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=90)
                result = await session.execute(
                    delete(Statistics).where(Statistics.event_time < cutoff)
                )
                await session.commit()
                deleted = result.rowcount
                
                if deleted > 0:
                    logger.info(f"Cleaned {deleted} old statistics records (>90 days)")
        except Exception as e:
            logger.error(f"Failed to clean old statistics: {e}")


async def purge_departed_daily():
    """Delete users who blocked the bot and chats the bot left more than 30 days ago - runs daily"""
    while True:
        try:
            await asyncio.sleep(86400)  # 24 hours

            from storage.db import database_manager
            from storage.db.crud import purge_departed

            async with database_manager.async_session() as session:
                users, chats = await purge_departed(session)
            if users or chats:
                logger.info(f"Purged {users} users who blocked the bot and {chats} chats the bot left (>30 days)")
        except Exception as e:
            logger.error(f"Failed to purge departed users/chats: {e}")


def _delete_old_files(temp_dir: Path, max_age: float) -> int:
    """Blocking part of the cleanup: removes files older than max_age seconds and empty subdirs."""
    if not temp_dir.exists():
        return 0
    cutoff_time = time.time() - max_age
    deleted_count = 0
    for file_path in temp_dir.rglob("*"):
        try:
            if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                file_path.unlink()
                deleted_count += 1
            elif file_path.is_dir() and not any(file_path.iterdir()):
                file_path.rmdir()
        except Exception:
            logger.debug("best-effort call failed", exc_info=True)
    return deleted_count


async def cleanup_old_downloads():
    """Clean old download files - runs every 6 hours"""
    while True:
        try:
            await asyncio.sleep(21600)  # 6 hours

            deleted_count = await asyncio.to_thread(_delete_old_files, Path("storage/temp"), 86400)  # 24 hours

            if deleted_count > 0:
                logger.info(f"Cleaned {deleted_count} old files from storage/temp (>24 hours)")
        except Exception as e:
            logger.error(f"Failed to clean old downloads: {e}")


async def cleanup_url_cache():
    """Clean expired in-memory URL cache entries - runs every hour"""
    while True:
        await asyncio.sleep(3600)
        try:
            cleanup_expired_urls()
        except Exception as e:
            logger.error(f"Failed to clean url cache: {e}")


# async def notify_expired_premium(bot: Bot):
#     """Scan and notify users about expired premium - runs every 24 hours"""
#     while True:
#         try:
#             await asyncio.sleep(86400)  # 24 hours
# 
#             from storage.db import database_manager
#             from storage.db.models import Users
# 
#             async with database_manager.async_session() as session:
#                 now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
#                 # Query users whose premium has ended
#                 result = await session.execute(
#                     select(Users).where(
#                         Users.premium_ends < now,
#                         Users.is_lifetime_premium == False
#                     )
#                 )
#                 users = result.scalars().all()
# 
#                 notified_count = 0
#                 for user in users:
#                     settings = user.settings_json or {}
#                     if not settings.get("premium_expired_notified", False):
#                         try:
#                             # Send message
#                             await bot.send_message(
#                                 user.user_id,
#                                 "⚠️ **Your Premium Sponsorship has expired!**\n\n"
#                                 "Thank you for supporting Charlotte! Your premium features are now disabled.\n"
#                                 "If you'd like to continue enjoying premium benefits and support the project, "
#                                 "you can become a sponsor again using /sponsor. 🌟",
#                                 parse_mode="Markdown"
#                             )
#                             settings["premium_expired_notified"] = True
#                             await session.execute(
#                                 update(Users)
#                                 .where(Users.user_id == user.user_id)
#                                 .values(settings_json=settings)
#                             )
#                             await session.commit()
#                             notified_count += 1
#                             # To avoid flooding Telegram API
#                             await asyncio.sleep(0.5)
#                         except Exception as e:
#                             logger.error(f"Failed to notify user {user.user_id} about expired premium: {e}")
# 
#                 if notified_count > 0:
#                     logger.info(f"Notified {notified_count} users about expired premium")
# 
#         except Exception as e:
#             logger.error(f"Error in notify_expired_premium task: {e}")
# 
# 
def start_scheduled_tasks(bot: Bot):
    """Start all scheduled background tasks"""
    asyncio.create_task(cleanup_old_statistics())
    asyncio.create_task(purge_departed_daily())
    asyncio.create_task(cleanup_old_downloads())
    asyncio.create_task(cleanup_url_cache())
    asyncio.create_task(music_refresh_loop(bot))
    # asyncio.create_task(notify_expired_premium(bot))
    logger.info("✅ Scheduled tasks started")
