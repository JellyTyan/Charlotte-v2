"""Scheduled tasks for maintenance"""
import asyncio
import logging
import datetime
import os
import time
from pathlib import Path
from sqlalchemy import delete, select, update
from aiogram import Bot

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


async def cleanup_old_downloads():
    """Clean old download files - runs every 6 hours"""
    while True:
        try:
            await asyncio.sleep(21600)  # 6 hours

            temp_dir = Path("storage/temp")
            if not temp_dir.exists():
                continue

            cutoff_time = time.time() - 86400  # 24 hours ago
            deleted_count = 0

            for file_path in temp_dir.iterdir():
                if file_path.is_file() and file_path.stat().st_mtime < cutoff_time:
                    file_path.unlink()
                    deleted_count += 1

            if deleted_count > 0:
                logger.info(f"Cleaned {deleted_count} old files from storage/temp (>24 hours)")
        except Exception as e:
            logger.error(f"Failed to clean old downloads: {e}")


async def notify_expired_premium(bot: Bot):
    """Scan and notify users about expired premium - runs every 24 hours"""
    while True:
        try:
            await asyncio.sleep(86400)  # 24 hours

            from storage.db import database_manager
            from storage.db.models import Users

            async with database_manager.async_session() as session:
                now = datetime.datetime.now(datetime.timezone.utc)
                # Query users whose premium has ended
                result = await session.execute(
                    select(Users).where(
                        Users.premium_ends < now,
                        Users.is_lifetime_premium == False
                    )
                )
                users = result.scalars().all()

                notified_count = 0
                for user in users:
                    settings = user.settings_json or {}
                    if not settings.get("premium_expired_notified", False):
                        try:
                            # Send message
                            await bot.send_message(
                                user.user_id,
                                "⚠️ **Your Premium Sponsorship has expired!**\n\n"
                                "Thank you for supporting Charlotte! Your premium features are now disabled.\n"
                                "If you'd like to continue enjoying premium benefits and support the project, "
                                "you can become a sponsor again using /sponsor. 🌟",
                                parse_mode="Markdown"
                            )
                            settings["premium_expired_notified"] = True
                            await session.execute(
                                update(Users)
                                .where(Users.user_id == user.user_id)
                                .values(settings_json=settings)
                            )
                            await session.commit()
                            notified_count += 1
                            # To avoid flooding Telegram API
                            await asyncio.sleep(0.5)
                        except Exception as e:
                            logger.error(f"Failed to notify user {user.user_id} about expired premium: {e}")

                if notified_count > 0:
                    logger.info(f"Notified {notified_count} users about expired premium")

        except Exception as e:
            logger.error(f"Error in notify_expired_premium task: {e}")


def start_scheduled_tasks(bot: Bot):
    """Start all scheduled background tasks"""
    asyncio.create_task(cleanup_old_statistics())
    asyncio.create_task(cleanup_old_downloads())
    asyncio.create_task(notify_expired_premium(bot))
    logger.info("✅ Scheduled tasks started")
