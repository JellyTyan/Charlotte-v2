"""Scheduled tasks for maintenance"""
import asyncio
import logging
import datetime
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


def start_scheduled_tasks():
    """Start all scheduled background tasks"""
    asyncio.create_task(cleanup_old_statistics())
    logger.info("✅ Scheduled tasks started")
