"""Scheduled tasks for maintenance"""
import asyncio
import logging
import datetime
import os
import time
from pathlib import Path
from sqlalchemy import delete

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


def start_scheduled_tasks():
    """Start all scheduled background tasks"""
    asyncio.create_task(cleanup_old_statistics())
    asyncio.create_task(cleanup_old_downloads())
    logger.info("✅ Scheduled tasks started")
