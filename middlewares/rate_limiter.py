import logging

from aiogram import BaseMiddleware
from aiogram.types import Message

from storage.cache import redis_client as redis_module


logger = logging.getLogger(__name__)

class RateLimiter(BaseMiddleware):
    """
    Middleware to control users late limits.
    """
    def __init__(self, rate: int = 10, per: int = 60):
        self.rate = rate
        self.per = per

    async def __call__(self, handler, event, data):
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        client = redis_module.redis_client
        if client is None:
            logger.warning("Redis unavailable, skipping rate limit check")
            return await handler(event, data)

        user_id = event.from_user.id
        requests_key = f"rate_limit:requests:{user_id}"
        notified_key = f"rate_limit:notified:{user_id}"

        current_count = await client.incr(requests_key)
        if current_count == 1:
            await client.expire(requests_key, self.per)

        if current_count > self.rate:
            already_notified = await client.get(notified_key)
            if not already_notified:
                i18n = data.get("i18n")
                msg = i18n.get("too-many-requests") if i18n else "⏳ Too many requests. Please wait."
                await event.answer(msg)
                await client.set(notified_key, "1", ex=self.per)
            return

        return await handler(event, data)