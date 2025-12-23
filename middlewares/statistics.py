"""Middleware for collecting statistics"""
import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

logger = logging.getLogger(__name__)


class StatisticsMiddleware(BaseMiddleware):
    """Collect statistics on service usage"""
    
    # Map URL patterns to service names
    SERVICE_PATTERNS = {
        'youtube.com': 'YouTube',
        'youtu.be': 'YouTube',
        'spotify.com': 'Spotify',
        'soundcloud.com': 'SoundCloud',
        'music.apple.com': 'AppleMusic',
    }
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message) or not event.text or not event.from_user:
            return await handler(event, data)
        
        # Detect service from URL
        service_name = None
        for pattern, name in self.SERVICE_PATTERNS.items():
            if pattern in event.text:
                service_name = name
                break
        
        if not service_name:
            return await handler(event, data)
        
        # Store service info for later use
        data['_stats_service'] = service_name
        data['_stats_user_id'] = event.from_user.id
        
        # Just pass through - logging happens in handlers after successful send
        return await handler(event, data)
    
    async def _log_event(self, data: Dict[str, Any], service_name: str, user_id: int, event_type: str, status: str):
        """Log event to database"""
        try:
            from storage.db import database_manager
            from storage.db.crud_statistics import log_event
            
            async with database_manager.async_session() as session:
                await log_event(session, service_name, user_id, event_type, status)
        except Exception as e:
            logger.error(f"Failed to log statistics: {e}")
