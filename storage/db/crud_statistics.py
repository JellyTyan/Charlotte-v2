"""CRUD operations for statistics"""
import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Statistics


async def log_event(
    session: AsyncSession,
    service_name: str,
    user_id: int,
    event_type: str,
    status: str = "success"
) -> Statistics:
    """Log a statistics event"""
    event = Statistics(
        service_name=service_name,
        user_id=user_id,
        event_type=event_type,
        event_time=datetime.datetime.now(datetime.timezone.utc),
        status=status
    )
    session.add(event)
    await session.commit()
    return event


async def get_user_stats(session: AsyncSession, user_id: int, days: int = 30):
    """Get user statistics for last N days"""
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    result = await session.execute(
        select(Statistics)
        .where(Statistics.user_id == user_id)
        .where(Statistics.event_time >= since)
        .order_by(Statistics.event_time.desc())
    )
    return result.scalars().all()


async def get_service_stats(session: AsyncSession, service_name: str, days: int = 30):
    """Get service statistics for last N days"""
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)
    result = await session.execute(
        select(Statistics)
        .where(Statistics.service_name == service_name)
        .where(Statistics.event_time >= since)
        .order_by(Statistics.event_time.desc())
    )
    return result.scalars().all()
