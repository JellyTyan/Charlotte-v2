"""Helper for logging statistics"""
import logging

logger = logging.getLogger(__name__)


async def log_download_event(user_id: int, service_name: str, status: str = "success"):
    """Log download event to statistics"""
    try:
        from storage.db import database_manager
        from storage.db.crud_statistics import log_event
        
        async with database_manager.async_session() as session:
            await log_event(session, service_name, user_id, 'download', status)
    except Exception as e:
        logger.error(f"Failed to log statistics: {e}")
