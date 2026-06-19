"""Helper for logging statistics"""
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from models.service_list import Services
from models.errors import ErrorCode

logger = logging.getLogger(__name__)


async def log_download_event(
    session: AsyncSession,
    user_id: int,
    service: Services,
    status: str = "success",
    error_code: Optional[ErrorCode] = None
):
    """Log download event to statistics"""
    if status == "failed_download" and error_code in (
        ErrorCode.DOWNLOAD_CANCELLED,
        ErrorCode.NOT_FOUND,
        ErrorCode.INVALID_URL,
        ErrorCode.NOT_ALLOWED,
        ErrorCode.LARGE_FILE,
        ErrorCode.AGE_RESTRICTED,
        ErrorCode.PRIVATE_CONTENT,
        ErrorCode.REGION_RESTRICTED
    ):
        logger.debug(f"Skipping statistics log for non-technical error: {error_code}")
        return

    try:
        from storage.db.crud_statistics import log_event
        await log_event(session, service.value, user_id, 'download', status)
    except Exception as e:
        logger.error(f"Failed to log statistics: {e}")
