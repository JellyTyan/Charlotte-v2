import logging
import datetime
import json
from datetime import date

from . import database_manager
from sqlalchemy import select, update, func, desc, or_
from .models import Users, UserSettings, Chats, ChatSettings, Statistics, BotSetting
from storage.cache.redis_client import cache_get, cache_set, cache_delete, orm_to_dict, dict_to_orm


async def get_user(user_id: int) -> Users | None:
    """Get user from database

    Args:
        user_id (int): User ID

    Returns:
        Users | None: User object
    """
    cache_key = f"user:{user_id}"
    cached = await cache_get(cache_key)
    if cached:
        return dict_to_orm(Users, cached)

    async with database_manager.async_session() as session:
        result = await session.execute(select(Users).where(Users.user_id == user_id))
        user = result.scalar_one_or_none()
        if user:
            await cache_set(cache_key, orm_to_dict(user), ttl=3600)
        return user

async def create_user(user_id: int) -> Users | None:
    """Create user in database

    Args:
        user_id (int): User ID
    """
    try:
        async with database_manager.async_session() as session:
            stmt = select(Users).where(Users.user_id == user_id)
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()

            if existing_user:
                return existing_user

            user = Users(user_id=user_id)
            settings = UserSettings(user_id=user_id)
            session.add_all([user, settings])
            await session.commit()

            await cache_set(f"user:{user_id}", orm_to_dict(user), ttl=3600)
            await cache_set(f"user_settings:{user_id}", orm_to_dict(settings), ttl=3600)
            return user
    except Exception as e:
        logging.error(e)
        return None

async def get_user_settings(user_id: int) -> UserSettings | None:
    """Get user settings from database

    Args:
        user_id (int): User ID

    Returns:
        UserSettings | None: User settings object
    """
    cache_key = f"user_settings:{user_id}"
    cached = await cache_get(cache_key)
    if cached:
        return dict_to_orm(UserSettings, cached)

    async with database_manager.async_session() as session:
        result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        settings = result.scalar_one_or_none()
        if settings:
            await cache_set(cache_key, orm_to_dict(settings), ttl=3600)
        return settings

async def update_user_premium(user_id: int, is_premium: bool, premium_ends: date):
    async with database_manager.async_session() as session:
        await session.execute(
            update(Users)
            .where(Users.user_id == user_id)
            .values(is_premium=is_premium, premium_ends=premium_ends)
        )
        await session.commit()
    await cache_delete(f"user:{user_id}")

async def update_user_settings(user_id: int, **kwargs):
    ALLOWED_KEYS = {"lang", "send_notifications", "send_raw", "send_music_covers",
                    "send_reactions", "ping_reaction", "auto_caption", "auto_translate_titles",
                    "title_language"
                    }
    safe_kwargs = {k: v for k, v in kwargs.items() if k in ALLOWED_KEYS}

    # Don't execute update if no valid fields to update
    if not safe_kwargs:
        logging.warning(f"No valid fields to update for user {user_id}. Received kwargs: {kwargs}")
        return

    async with database_manager.async_session() as session:
        await session.execute(
            update(UserSettings)
            .where(UserSettings.user_id == user_id)
            .values(safe_kwargs)
        )
        await session.commit()
    await cache_delete(f"user_settings:{user_id}")


async def get_chat(chat_id: int) -> Chats | None:
    """Get chat from database

    Args:
        chat_id (int): User ID

    Returns:
        Chats | None: Chat object
    """
    cache_key = f"chat:{chat_id}"
    cached = await cache_get(cache_key)
    if cached:
        return dict_to_orm(Chats, cached)

    async with database_manager.async_session() as session:
        result = await session.execute(select(Chats).where(Chats.chat_id == chat_id))
        chat = result.scalar_one_or_none()
        if chat:
            await cache_set(cache_key, orm_to_dict(chat), ttl=3600)
        return chat

async def create_chat(chat_id: int, owner_id: int) -> Chats | None:
    """Create chat in database

    Args:
        chat_id (int): Chat ID
        owner_id (int): User ID
    """
    try:
        async with database_manager.async_session() as session:
            chat = Chats(chat_id=chat_id, owner_id=owner_id)
            settings = ChatSettings(chat_id=chat_id)
            session.add_all([chat, settings])
            await session.commit()

            await cache_set(f"chat:{chat_id}", orm_to_dict(chat), ttl=3600)
            await cache_set(f"chat_settings:{chat_id}", orm_to_dict(settings), ttl=3600)
            return chat
    except Exception as e:
        logging.error(e)
        return None

async def get_chat_settings(chat_id: int) -> ChatSettings | None:
    """Get chat settings from database

    Args:
        chat_id (int): Chat ID

    Returns:
        ChatSettings | None: Chat settings object
    """
    cache_key = f"chat_settings:{chat_id}"
    cached = await cache_get(cache_key)
    if cached:
        return dict_to_orm(ChatSettings, cached)

    async with database_manager.async_session() as session:
        result = await session.execute(select(ChatSettings).where(ChatSettings.chat_id == chat_id))
        settings = result.scalar_one_or_none()
        if settings:
            await cache_set(cache_key, orm_to_dict(settings), ttl=3600)
        return settings

async def update_chat_settings(chat_id: int, **kwargs):
    ALLOWED_KEYS = {"lang", "send_notifications", "send_raw", "send_music_covers",
                    "send_reactions", "ping_reaction", "auto_caption", "auto_translate_titles",
                    "title_language", "preferred_services", "blocked_services", "allow_playlists"
                    }
    safe_kwargs = {k: v for k, v in kwargs.items() if k in ALLOWED_KEYS}

    # Don't execute update if no valid fields to update
    if not safe_kwargs:
        logging.warning(f"No valid fields to update for chat {chat_id}. Received kwargs: {kwargs}")
        return

    async with database_manager.async_session() as session:
        await session.execute(
            update(ChatSettings)
            .where(ChatSettings.chat_id == chat_id)
            .values(safe_kwargs)
        )
        await session.commit()
    await cache_delete(f"chat_settings:{chat_id}")


async def create_usage_log(user_id: int, service_name: str, event_type: str, status: str) -> Statistics | None:
    async with database_manager.async_session() as session:
        statistics = Statistics(service_name=service_name, user_id=user_id, event_type=event_type, status=status)
        session.add_all([statistics])
        await session.commit()
        return statistics


async def get_user_counts():
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - datetime.timedelta(days=1)
    week_ago = now - datetime.timedelta(days=7)
    month_ago = now - datetime.timedelta(days=30)

    async with database_manager.async_session() as session:
        results = {}

        # Сегодня
        res = await session.execute(
            select(func.count(func.distinct(Statistics.user_id)))
            .where(Statistics.event_time >= today)
        )
        results["today"] = res.scalar()

        # Вчера
        res = await session.execute(
            select(func.count(func.distinct(Statistics.user_id)))
            .where(Statistics.event_time.between(yesterday, today - datetime.timedelta(microseconds=1)))
        )
        results["yesterday"] = res.scalar()

        # За неделю
        res = await session.execute(
            select(func.count(func.distinct(Statistics.user_id)))
            .where(Statistics.event_time >= week_ago)
        )
        results["week"] = res.scalar()

        # За месяц
        res = await session.execute(
            select(func.count(func.distinct(Statistics.user_id)))
            .where(Statistics.event_time >= month_ago)
        )
        results["month"] = res.scalar()

    return results


async def get_top_services(limit: int = 10):
    async with database_manager.async_session() as session:
        query = (
            select(
                Statistics.service_name,
                func.count().label("usage_count")
            )
            .group_by(Statistics.service_name)
            .order_by(desc("usage_count"))
            .limit(limit)
        )
        result = await session.execute(query)
        return result.all()


async def get_status_stats():
    async with database_manager.async_session() as session:
        query = select(
            func.count().filter(Statistics.status == "complete").label("complete_count"),
            func.count().filter(Statistics.status == "error").label("error_count")
        )
        result = await session.execute(query)
        complete_count, error_count = result.one()
        return {
            "complete": complete_count,
            "error": error_count
        }

async def get_premium_events_by_user(user_id: int):
    async with database_manager.async_session() as session:
        query = (
            select(Statistics)
            .where(
                Statistics.user_id == user_id,
                Statistics.event_type.in_(["buy_premium", "refund_premium"])
            )
            .order_by(Statistics.event_time.desc())
        )
        result = await session.execute(query)
        return result.scalars().all()

async def get_premium_and_donation_stats() -> dict:
    async with database_manager.async_session() as session:
        stmt = select(
            func.count().filter(or_(Users.is_premium == True, Users.is_lifetime_premium == True)).label("premium_count"),
            func.sum(Users.stars_donated).label("total_stars")
        )

        result = await session.execute(stmt)
        row = result.one()

    return {
        "total_premium_users": row.premium_count or 0,
        "total_stars_donated": row.total_stars or 0
    }

async def check_if_user_premium(user_id: int) -> bool:
    user = await get_user(user_id=user_id)
    if user is None:
        await create_user(user_id)
        user = await get_user(user_id=user_id)

    if not user:
        return False

    if user.is_premium:
        if user.is_lifetime_premium:
            return True
        elif user.premium_ends:
            if isinstance(user.premium_ends, datetime.datetime):
                ends = user.premium_ends.date()
            else:
                ends = user.premium_ends
            if ends > datetime.date.today():
                return True

    return False

async def toggle_lifetime_premium(user_id: int) -> bool | None:
    """
    Determines the file type by its extension.

    :param user_id: User id
    :return: bool: True when toggled on premium, False when toggled off premium. None when some error occurs.
    """
    user = await get_user(user_id=user_id)
    if user is None:
        await create_user(user_id)
        user = await get_user(user_id=user_id)

    if not user:
        return None

    if user.is_premium:
        async with database_manager.async_session() as session:
            await session.execute(
                update(Users)
                .where(Users.user_id == user_id)
                .values(is_premium=False, is_lifetime_premium=False)
            )
            await session.commit()
        await cache_delete(f"user:{user_id}")
        return False
    elif not user.is_premium:
        async with database_manager.async_session() as session:
            await session.execute(
                update(Users)
                .where(Users.user_id == user_id)
                .values(is_premium=True, is_lifetime_premium=True)
            )
            await session.commit()
        await cache_delete(f"user:{user_id}")
        return True
    return None

async def ban_user(user_id: int) -> None:
    user = await get_user(user_id=user_id)
    if user is None:
        await create_user(user_id=user_id)
        user = await get_user(user_id=user_id)

    if not user:
        return

    async with database_manager.async_session() as session:
        user.is_banned = True
        session.add(user)
        await session.commit()
    await cache_delete(f"user:{user_id}")

async def unban_user(user_id: int) -> None:
    user = await get_user(user_id=user_id)
    if user is None:
        await create_user(user_id=user_id)
        user = await get_user(user_id=user_id)

    if not user:
        return

    async with database_manager.async_session() as session:
        user.is_banned = False
        session.add(user)
        await session.commit()
    await cache_delete(f"user:{user_id}")

async def list_of_banned_users() -> list[Users]:
    async with database_manager.async_session() as session:
        stmt = select(Users).where(Users.is_banned == True)
        result = await session.execute(stmt)
        return list(result.scalars().all())

async def get_global_settings() -> dict:
    cached = await cache_get("global_settings")
    if cached:
        return cached

    async with database_manager.async_session() as session:
        stmt = select(BotSetting)
        result = await session.execute(stmt)
        settings = result.scalars().all()

    data = {}
    for s in settings:
        try:
            # Попробуем парсить JSON-строки обратно в Python-объекты
            data[s.key] = json.loads(s.value)
        except (json.JSONDecodeError, TypeError):
            data[s.key] = s.value

    await cache_set("global_settings", data, ttl=24000)
    return data


async def update_global_settings(key: str, value) -> None:
    """value может быть str, list, dict — автоматически сериализуем"""
    if not isinstance(value, str):
        value = json.dumps(value)

    async with database_manager.async_session() as session:
        stmt = select(BotSetting).where(BotSetting.key == key)
        result = await session.execute(stmt)
        setting = result.scalars().first()

        if setting:
            setting.value = value
        else:
            setting = BotSetting(key=key, value=value)
            session.add(setting)

        await session.commit()

    await cache_delete("global_settings")
