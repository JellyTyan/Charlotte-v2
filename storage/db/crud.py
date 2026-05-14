import logging
import datetime
import json
from datetime import date

from sqlalchemy import select, update, func, desc, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from .models import Users, Chats, Statistics, BotSetting, MediaCache
from storage.cache.redis_client import cache_get, cache_set, cache_delete, orm_to_dict, dict_to_orm
from models.settings import UserSettingsJson, ChatSettingsJson
from models.media_cache import MediaCacheDTO


def _get_db():
    from . import database_manager
    return database_manager


async def get_user(session: AsyncSession, user_id: int) -> Users | None:
    """Get user from database

    Args:
        session (AsyncSession): Database session
        user_id (int): User ID

    Returns:
        Users | None: User object
    """
    cache_key = f"user:{user_id}"
    cached = await cache_get(cache_key)
    if cached:
        return dict_to_orm(Users, cached)

    result = await session.execute(select(Users).where(Users.user_id == user_id))
    user = result.scalar_one_or_none()
    if user:
        await cache_set(cache_key, orm_to_dict(user), ttl=3600)
    return user

async def create_user(session: AsyncSession, user_id: int) -> Users | None:
    """Create user in database

    Args:
        session (AsyncSession): Database session
        user_id (int): User ID
    """
    stmt = select(Users).where(Users.user_id == user_id)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        return existing_user

    user = Users(user_id=user_id)
    session.add(user)
    await session.flush()

    await cache_set(f"user:{user_id}", orm_to_dict(user), ttl=3600)
    return user

async def get_user_settings(session: AsyncSession, user_id: int) -> UserSettingsJson:
    """Get user settings from database

    Args:
        session (AsyncSession): Database session
        user_id (int): User ID

    Returns:
        UserSettings | None: User settings object
    """
    cache_key = f"user_settings:{user_id}"
    cached = await cache_get(cache_key)
    if cached:
        return UserSettingsJson.model_validate(cached)

    result = await session.execute(select(Users.settings_json).where(Users.user_id == user_id))
    settings = result.scalar_one_or_none()
    if settings:
        await cache_set(cache_key, settings, ttl=3600)
        return UserSettingsJson.model_validate(settings)
    else:
        return UserSettingsJson.model_validate({})

async def update_user_premium(session: AsyncSession, user_id: int, premium_ends: datetime.datetime):
    await session.execute(
        update(Users)
        .where(Users.user_id == user_id)
        .values(premium_ends=premium_ends)
    )
    await cache_delete(f"user:{user_id}")

async def grant_sponsorship(session: AsyncSession, user_id: int, days: int, stars_donated: int = 0):
    user = await get_user(session, user_id)
    if not user:
        user = await create_user(session, user_id)
        
    current_end = user.premium_ends if user.premium_ends else datetime.datetime.now(datetime.timezone.utc)
    
    if isinstance(current_end, datetime.date) and not isinstance(current_end, datetime.datetime):
        current_end = datetime.datetime.combine(current_end, datetime.time.min).replace(tzinfo=datetime.timezone.utc)
        
    # If it's already expired, start from now
    if current_end < datetime.datetime.now(datetime.timezone.utc):
        current_end = datetime.datetime.now(datetime.timezone.utc)
        
    new_end = current_end + datetime.timedelta(days=days)
    
    # Reset notification flag
    settings = user.settings_json or {}
    settings["premium_expired_notified"] = False
    
    await session.execute(
        update(Users)
        .where(Users.user_id == user_id)
        .values(
            premium_ends=new_end,
            stars_donated=Users.stars_donated + stars_donated,
            settings_json=settings
        )
    )
    await cache_delete(f"user:{user_id}")

async def update_user_settings(session: AsyncSession, user_id: int, settings: UserSettingsJson):
    await session.execute(
        update(Users)
        .where(Users.user_id == user_id)
        .values(settings_json=settings.model_dump(mode="json"))
    )
    await cache_delete(f"user_settings:{user_id}")


async def get_chat(session: AsyncSession, chat_id: int) -> Chats | None:
    """Get chat from database

    Args:
        session (AsyncSession): Database session
        chat_id (int): User ID

    Returns:
        Chats | None: Chat object
    """
    cache_key = f"chat:{chat_id}"
    cached = await cache_get(cache_key)
    if cached:
        return dict_to_orm(Chats, cached)

    result = await session.execute(select(Chats).where(Chats.chat_id == chat_id))
    chat = result.scalar_one_or_none()
    if chat:
        await cache_set(cache_key, orm_to_dict(chat), ttl=3600)
    return chat

async def create_chat(session: AsyncSession, chat_id: int, owner_id: int) -> Chats | None:
    """Create chat in database

    Args:
        session (AsyncSession): Database session
        chat_id (int): Chat ID
        owner_id (int): User ID
    """
    stmt = select(Chats).where(Chats.chat_id == chat_id)
    result = await session.execute(stmt)
    existing_chat = result.scalar_one_or_none()

    if existing_chat:
        return existing_chat

    chat = Chats(chat_id=chat_id, owner_id=owner_id)
    session.add(chat)
    await session.flush()

    await cache_set(f"chat:{chat_id}", orm_to_dict(chat), ttl=3600)
    return chat

async def get_chat_settings(session: AsyncSession, chat_id: int) -> ChatSettingsJson:
    """Get chat settings from database

    Args:
        session (AsyncSession): Database session
        chat_id (int): Chat ID

    Returns:
        ChatSettingsJson | None: Chat settings object
    """
    cache_key = f"chat_settings:{chat_id}"
    cached = await cache_get(cache_key)
    if cached:
        return ChatSettingsJson.model_validate(cached)

    result = await session.execute(select(Chats.settings_json).where(Chats.chat_id == chat_id))
    settings = result.scalar_one_or_none()
    if settings is not None:
        await cache_set(cache_key, settings, ttl=3600)
        return ChatSettingsJson.model_validate(settings)
    else:
        return ChatSettingsJson.model_validate({})

async def update_chat_settings(session: AsyncSession, chat_id: int, settings: ChatSettingsJson):
    settings_dict = settings.model_dump(mode="json")
    await session.execute(
        update(Chats)
        .where(Chats.chat_id == chat_id)
        .values(settings_json=settings_dict)
    )
    await cache_delete(f"chat_settings:{chat_id}")


async def create_usage_log(session: AsyncSession, user_id: int, service_name: str, event_type: str, status: str) -> Statistics | None:
    statistics = Statistics(service_name=service_name, user_id=user_id, event_type=event_type, status=status)
    session.add(statistics)
    return statistics


async def create_payment_log(session: AsyncSession, user_id: int, amount: int, currency: str, payload: str,
                            telegram_payment_charge_id: str, provider_payment_charge_id: str = None):
    from .models import Payment
    payment = Payment(
        user_id=user_id,
        amount=amount,
        currency=currency,
        payload=payload,
        telegram_payment_charge_id=telegram_payment_charge_id,
        provider_payment_charge_id=provider_payment_charge_id
    )
    session.add(payment)
    return payment


async def update_payment_status(session: AsyncSession, telegram_payment_charge_id: str, status: str):
    from .models import Payment
    await session.execute(
        update(Payment)
        .where(Payment.telegram_payment_charge_id == telegram_payment_charge_id)
        .values(status=status)
    )


async def get_last_payment(session: AsyncSession, user_id: int):
    from .models import Payment
    result = await session.execute(
        select(Payment)
        .where(Payment.user_id == user_id)
        .order_by(desc(Payment.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_payment_by_charge_id(session: AsyncSession, telegram_payment_charge_id: str):
    from .models import Payment
    result = await session.execute(
        select(Payment)
        .where(Payment.telegram_payment_charge_id == telegram_payment_charge_id)
    )
    return result.scalar_one_or_none()


async def get_user_counts(session: AsyncSession):
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday = today - datetime.timedelta(days=1)
    week_ago = now - datetime.timedelta(days=7)
    month_ago = now - datetime.timedelta(days=30)

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


async def get_top_services(session: AsyncSession, limit: int = 10):
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


async def get_status_stats(session: AsyncSession):
    query = select(
        func.count().filter(Statistics.status == "success").label("complete_count"),
        func.count().filter(Statistics.status == "failed").label("error_count")
    )
    result = await session.execute(query)
    complete_count, error_count = result.one()
    return {
        "complete": complete_count,
        "error": error_count
    }

async def get_premium_events_by_user(session: AsyncSession, user_id: int):
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

async def get_premium_and_donation_stats(session: AsyncSession) -> dict:
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) # fallback
    stmt = select(
        func.count().filter(or_(Users.premium_ends > now, Users.is_lifetime_premium == True)).label("premium_count"),
        func.sum(Users.stars_donated).label("total_stars")
    )

    result = await session.execute(stmt)
    row = result.one()

    return {
        "total_premium_users": row.premium_count or 0,
        "total_stars_donated": row.total_stars or 0
    }

async def check_if_user_premium(session: AsyncSession, user_id: int) -> bool:
    user = await get_user(session=session, user_id=user_id)
    if user is None:
        await create_user(session=session, user_id=user_id)
        user = await get_user(session=session, user_id=user_id)

    if not user:
        return False

    return user.is_premium

async def toggle_lifetime_premium(session: AsyncSession, user_id: int) -> bool | None:
    """
    Determines the file type by its extension.

    :param user_id: User id
    :param session: AsyncSession
    :return: bool: True when toggled on premium, False when toggled off premium. None when some error occurs.
    """
    user = await get_user(session=session, user_id=user_id)
    if user is None:
        await create_user(session=session, user_id=user_id)
        user = await get_user(session=session, user_id=user_id)

    if not user:
        return None

    if user.is_premium and user.is_lifetime_premium:
        await session.execute(
            update(Users)
            .where(Users.user_id == user_id)
            .values(is_lifetime_premium=False)
        )
        await cache_delete(f"user:{user_id}")
        return False
    elif not user.is_lifetime_premium:
        await session.execute(
            update(Users)
            .where(Users.user_id == user_id)
            .values(is_lifetime_premium=True)
        )
        await cache_delete(f"user:{user_id}")
        return True
    return None

async def ban_user(session: AsyncSession, user_id: int) -> None:
    user = await get_user(session=session, user_id=user_id)
    if user is None:
        await create_user(session=session, user_id=user_id)
        user = await get_user(session=session, user_id=user_id)

    if not user:
        return

    user.is_banned = True
    session.add(user)
    await cache_delete(f"user:{user_id}")

async def unban_user(session: AsyncSession, user_id: int) -> None:
    user = await get_user(session=session, user_id=user_id)
    if user is None:
        await create_user(session=session, user_id=user_id)
        user = await get_user(session=session, user_id=user_id)

    if not user:
        return

    user.is_banned = False
    session.add(user)
    await cache_delete(f"user:{user_id}")

async def list_of_banned_users(session: AsyncSession) -> list[Users]:
    stmt = select(Users).where(Users.is_banned == True)
    result = await session.execute(stmt)
    return list(result.scalars().all())

async def get_global_settings(session: AsyncSession) -> dict:
    cached = await cache_get("global_settings")
    if cached:
        return cached

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


async def update_global_settings(session: AsyncSession, key: str, value) -> None:
    """value может быть str, list, dict — автоматически сериализуем"""
    if not isinstance(value, str):
        value = json.dumps(value)

    stmt = select(BotSetting).where(BotSetting.key == key)
    result = await session.execute(stmt)
    setting = result.scalars().first()

    if setting:
        setting.value = value
    else:
        setting = BotSetting(key=key, value=value)
        session.add(setting)

    await cache_delete("global_settings")


async def get_db_overview_stats(session: AsyncSession) -> dict:
    """
    Returns total counts of users and chats in the database,
    along with the count of inactive ones (no activity in the last 30 days).
    Inactive users: those with no Statistics records in the last 30 days.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    month_ago = now - datetime.timedelta(days=30)

    # Total users & chats
    res = await session.execute(select(func.count()).select_from(Users))
    total_users = res.scalar() or 0

    res = await session.execute(select(func.count()).select_from(Chats))
    total_chats = res.scalar() or 0

    # Active users: distinct user_ids in Statistics for last 30 days
    res = await session.execute(
        select(func.count(func.distinct(Statistics.user_id)))
        .where(Statistics.event_time >= month_ago)
    )
    active_users = res.scalar() or 0
    inactive_users = max(total_users - active_users, 0)

    # Cache count
    res = await session.execute(select(func.count()).select_from(MediaCache))
    total_cached = res.scalar() or 0

    return {
        "total_users": total_users,
        "total_chats": total_chats,
        "inactive_users": inactive_users,
        "total_cached": total_cached,
    }


async def get_list_user_ids(session: AsyncSession) -> list[int]:
    stmt = select(Users.user_id).where(Users.is_banned == False)
    result = await session.execute(stmt)
    return [row[0] for row in result.fetchall()]

async def get_news_subscribers_ids(session: AsyncSession) -> list[int]:
    # Get users who are not banned
    stmt_users = select(Users.user_id, Users.settings_json).where(Users.is_banned == False)
    result_users = await session.execute(stmt_users)
    users = result_users.fetchall()

    # Get all chats
    stmt_chats = select(Chats.chat_id, Chats.settings_json)
    result_chats = await session.execute(stmt_chats)
    chats = result_chats.fetchall()

    subscriber_ids = []

    for user_id, settings_json in users:
        settings_dict = settings_json if isinstance(settings_json, dict) else {}
        profile = settings_dict.get('profile', {})
        news_spam = profile.get('news_spam', False)  # defaults to False
        if news_spam:
            subscriber_ids.append(user_id)

    for chat_id, settings_json in chats:
        settings_dict = settings_json if isinstance(settings_json, dict) else {}
        profile = settings_dict.get('profile', {})
        news_spam = profile.get('news_spam', False)  # defaults to False
        if news_spam:
            subscriber_ids.append(chat_id)

    return subscriber_ids

async def get_all_chat_ids(session: AsyncSession) -> list[int]:
    stmt = select(Chats.chat_id)
    result = await session.execute(stmt)
    return [row[0] for row in result.fetchall()]

async def get_cache_counts_by_service(session: AsyncSession) -> dict[str, int]:
    """Returns a mapping of service_name to count of cached files."""
    stmt = select(MediaCache.platform, func.count()).group_by(MediaCache.platform)
    result = await session.execute(stmt)
    return {row[0]: row[1] for row in result.all()}


async def get_media_cache(session: AsyncSession, cache_key: str) -> MediaCacheDTO | None:
    """Ищет медиа в кэше по уникальному ключу (например, 'yt:123')"""

    stmt = select(MediaCache).where(MediaCache.cache_key == cache_key)
    result = await session.execute(stmt)
    db_obj = result.scalar_one_or_none()

    if not db_obj:
        return None

    return MediaCacheDTO.model_validate(db_obj, from_attributes=True)


async def upsert_media_cache(session: AsyncSession, dto: MediaCacheDTO) -> MediaCacheDTO:
    """Создает новую запись или обновляет существующую за 1 SQL-запрос"""

    values_to_insert = dto.model_dump(exclude_none=True)

    stmt = insert(MediaCache).values(**values_to_insert)

    do_update_stmt = stmt.on_conflict_do_update(
        index_elements=['cache_key'],
        set_=stmt.excluded
    ).returning(MediaCache)

    result = await session.execute(do_update_stmt)

    updated_obj = result.scalar_one()
    return MediaCacheDTO.model_validate(updated_obj, from_attributes=True)


async def delete_media_cache(session: AsyncSession, cache_key: str) -> bool:
    """Удаляет запись из кэша (например, если файл удалили с серверов Telegram)"""

    stmt = delete(MediaCache).where(MediaCache.cache_key == cache_key).returning(MediaCache.media_id)
    result = await session.execute(stmt)

    deleted_id = result.scalar_one_or_none()
    return deleted_id is not None