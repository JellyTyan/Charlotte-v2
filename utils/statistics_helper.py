"""Helper for logging statistics"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from models.service_list import Services

logger = logging.getLogger(__name__)


async def log_download_event(session: AsyncSession, user_id: int, service: Services, status: str = "success"):
    """Log download event to statistics"""
    try:
        from storage.db.crud_statistics import log_event
        await log_event(session, service.value, user_id, 'download', status)
    except Exception as e:
        logger.error(f"Failed to log statistics: {e}")
