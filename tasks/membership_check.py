"""One full pass over users and chats (admin «🔍 Check DB» button): who blocked the bot, where the bot still is.

Only marks rows (users.blocked_at, chats.bot_status/left_at); the daily purge in tasks/scheduled.py deletes them
30 days later. Users are probed with a "typing" action (no message; alive users see "typing…" for a moment),
chats with getChatMember on the bot itself (invisible).
"""
import asyncio
import datetime
import logging
import time
from collections.abc import Awaitable, Callable

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from sqlalchemy import select, update

from storage.cache.redis_client import cache_delete, cache_get, cache_set
from storage.db import database_manager
from storage.db.crud import mark_chat_gone, remember_bot_status
from storage.db.models import Chats, Users

logger = logging.getLogger(__name__)

DELAY = 0.04  # ~25 requests/s, under Telegram's global limit
LAST_KEY = "membership_check:last"
RUNNING_KEY = "membership_check:running"
# "chat not found" for nearly everyone means the token is not the bot these users talk to (dev bot on a prod DB)
WRONG_BOT_SHARE = 0.8


async def _call(fn):
    while True:
        try:
            return await fn()
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after + 1)


def _gone(e: TelegramBadRequest) -> bool:
    return "not found" in e.message or "upgraded" in e.message


async def is_running() -> bool:
    return bool(await cache_get(RUNNING_KEY))


async def run_check(bot: Bot, progress: Callable[[str], Awaitable[None]] | None = None) -> dict:
    started = time.monotonic()
    await cache_set(RUNNING_KEY, {"ok": True}, ttl=3600)
    try:
        me = await bot.me()
        async with database_manager.async_session() as s:
            users = (await s.execute(select(Users.user_id))).scalars().all()
            chats = (await s.execute(select(Chats.chat_id))).scalars().all()

        reachable, blocked, no_dm, errors = [], [], 0, 0
        for i, uid in enumerate(users, 1):
            try:
                await _call(lambda uid=uid: bot.send_chat_action(uid, "typing"))
                reachable.append(uid)
            except TelegramForbiddenError:  # blocked the bot / account deleted
                blocked.append(uid)
            except TelegramBadRequest as e:
                if _gone(e):  # never opened the DM (group-only user): alive, just unreachable here
                    no_dm += 1
                else:
                    errors += 1
            except Exception:
                errors += 1
            if progress and i % 100 == 0:
                await progress(f"👤 users {i}/{len(users)}")
            await asyncio.sleep(DELAY)

        members, gone_chats = {}, {}
        for cid in chats:
            try:
                members[cid] = await _call(lambda cid=cid: bot.get_chat_member(cid, me.id))
            except TelegramForbiddenError as e:
                gone_chats[cid] = e.message
            except TelegramBadRequest as e:
                if _gone(e):
                    gone_chats[cid] = e.message
                else:
                    errors += 1
            except Exception:
                errors += 1
            await asyncio.sleep(DELAY)

        left = len(gone_chats) + sum(m.status in ("left", "kicked") for m in members.values())
        result = {
            "at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "bot": me.username, "seconds": round(time.monotonic() - started),
            "users": len(users), "reachable": len(reachable), "blocked": len(blocked), "no_dm": no_dm,
            "chats": len(chats), "chats_present": len(chats) - left, "chats_gone": left, "errors": errors,
            "applied": False,
        }
        if (users and no_dm > len(users) * WRONG_BOT_SHARE) or (chats and len(gone_chats) > len(chats) * WRONG_BOT_SHARE):
            logger.warning(f"Membership check NOT applied, looks like the wrong bot: {result}")
            return result

        now = datetime.datetime.now(datetime.timezone.utc)
        async with database_manager.async_session() as s:
            if blocked:  # keep the first blocked_at: it is the 30-day clock
                await s.execute(update(Users).where(Users.user_id.in_(blocked), Users.blocked_at.is_(None)).values(blocked_at=now))
            if reachable:
                await s.execute(update(Users).where(Users.user_id.in_(reachable)).values(blocked_at=None))
            for cid, member in members.items():
                await remember_bot_status(s, cid, member)
            for cid, reason in gone_chats.items():
                await mark_chat_gone(s, cid, reason)
            await s.commit()
        for uid in blocked + reachable:
            await cache_delete(f"user:{uid}")

        result["applied"] = True
        await cache_set(LAST_KEY, result, ttl=90 * 86400)
        logger.info(f"Membership check done: {result}")
        return result
    finally:
        await cache_delete(RUNNING_KEY)


def format_report(r: dict) -> str:
    head = f"🔍 <b>DB check</b> as @{r['bot']} · {r['seconds']} s\n\n"
    body = (
        f"👤 Users {r['users']}: ✅ reachable {r['reachable']} · 🚫 blocked {r['blocked']} · "
        f"👥 never opened DM {r['no_dm']}\n"
        f"💬 Chats {r['chats']}: ✅ present {r['chats_present']} · 🚪 gone {r['chats_gone']}\n"
    )
    if r["errors"]:
        body += f"⚠️ unclear answers (left as is): {r['errors']}\n"
    if not r["applied"]:
        return head + body + (
            "\n❗ <b>Not applied</b>: almost everyone is «chat not found» — "
            f"is @{r['bot']} the bot these users talk to?"
        )
    return head + body + (
        "\nMarked. Blocked users and gone chats are deleted 30 days later "
        "(banned, donors and premium are kept)."
    )
