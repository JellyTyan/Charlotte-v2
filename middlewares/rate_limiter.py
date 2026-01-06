from collections import defaultdict
import time
from aiogram import BaseMiddleware
from aiogram.types import Message

class RateLimiter(BaseMiddleware):
    def __init__(self, rate: int = 10, per: int = 60):
        self.rate = rate
        self.per = per
        self._user_requests = defaultdict(list)
        self._user_notified = defaultdict(float)

    async def __call__(self, handler, event, data):
        if not isinstance(event, Message) or not event.from_user:
            return await handler(event, data)

        user_id = event.from_user.id
        now = time.time()

        self._user_requests[user_id] = [
            req_time for req_time in self._user_requests[user_id]
            if now - req_time < self.per
        ]

        if len(self._user_requests[user_id]) >= self.rate:
            if now - self._user_notified.get(user_id, 0) > self.per:
                await event.answer("⏳ Too many requests. Please wait.")
                self._user_notified[user_id] = now
            return

        self._user_requests[user_id].append(now)
        return await handler(event, data)
