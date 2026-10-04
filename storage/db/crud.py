import logging
import datetime
import json
from datetime import date

from sqlalchemy import select, update, func, desc, or_, and_, delete, cast, case, text, literal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from .models import Users, Chats, Statistics, BotSetting, MediaCache, UserSaves, PublicSavesBan
from storage.cache.redis_client import cache_get, cache_set, cache_delete, orm_to_dict, dict_to_orm
from models.settings import UserSettingsJson, ChatSettingsJson
from models.media_cache import MediaCacheDTO
from utils.search_utils import escape_ilike, query_variants


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

async def create_user(session: AsyncSession, user_id: int) -> tuple[Users, bool]:
    stmt = select(Users).where(Users.user_id == user_id)
    result = await session.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        return existing_user, False

    user = Users(user_id=user_id)
    session.add(user)
    await session.flush()

    await cache_set(f"user:{user_id}", orm_to_dict(user), ttl=3600)
    return user, True

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
    if premium_ends and getattr(premium_ends, 'tzinfo', None) is not None:
        premium_ends = premium_ends.replace(tzinfo=None)
    await session.execute(
        update(Users)
        .where(Users.user_id == user_id)
        .values(premium_ends=premium_ends)
    )
    await cache_delete(f"user:{user_id}")

async def grant_sponsorship(session: AsyncSession, user_id: int, days: int, stars_donated: int = 0):
    user = await get_user(session, user_id)
    if not user:
        user, _ = await create_user(session, user_id)
        
    now_naive = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    current_end = user.premium_ends if user.premium_ends else now_naive
    
    if isinstance(current_end, datetime.date) and not isinstance(current_end, datetime.datetime):
        current_end = datetime.datetime.combine(current_end, datetime.time.min)
        
    if getattr(current_end, 'tzinfo', None) is not None:
        current_end = current_end.replace(tzinfo=None)
        
    # If it's already expired, start from now
    if current_end < now_naive:
        current_end = now_naive
        
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


async def add_donation_stars(
    session: AsyncSession,
    user_id: int,
    stars: int,
) -> tuple[int, int, datetime.datetime | None]:
    """
    Adds donated stars to the user and calculates earned sponsorship months.
    Uses row-level locking (with_for_update) to prevent race conditions on concurrent payments.
    Returns: (earned_months, progress_to_next_100, new_premium_ends)
    """
    stmt = select(Users).where(Users.user_id == user_id).with_for_update()
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        user, _ = await create_user(session, user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

    old_stars = user.stars_donated or 0
    new_stars = old_stars + stars

    old_milestones = old_stars // 100
    new_milestones = new_stars // 100
    earned_months = new_milestones - old_milestones
    progress = new_stars % 100

    now_naive = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    current_end = user.premium_ends

    new_end = current_end
    if earned_months > 0 and not user.is_lifetime_premium:
        days_to_add = earned_months * 30
        if current_end:
            if isinstance(current_end, datetime.date) and not isinstance(current_end, datetime.datetime):
                current_end = datetime.datetime.combine(current_end, datetime.time.min)
            if getattr(current_end, "tzinfo", None) is not None:
                current_end = current_end.replace(tzinfo=None)
            if current_end < now_naive:
                current_end = now_naive
        else:
            current_end = now_naive

        new_end = current_end + datetime.timedelta(days=days_to_add)

    settings = dict(user.settings_json or {})
    settings["premium_expired_notified"] = False

    update_vals = {
        "stars_donated": new_stars,
        "settings_json": settings,
    }
    if earned_months > 0 and not user.is_lifetime_premium:
        update_vals["premium_ends"] = new_end

    await session.execute(
        update(Users)
        .where(Users.user_id == user_id)
        .values(**update_vals)
    )
    await cache_delete(f"user:{user_id}")
    return earned_months, progress, new_end


async def refund_donation_stars(
    session: AsyncSession,
    user_id: int,
    stars: int,
) -> tuple[int, datetime.datetime | None]:
    """
    Deducts refunded stars from user and adjusts sponsorship if milestones were lost.
    Returns: (new_stars, new_premium_ends)
    """
    stmt = select(Users).where(Users.user_id == user_id).with_for_update()
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if not user:
        return 0, None

    old_stars = user.stars_donated or 0
    new_stars = max(0, old_stars - stars)

    old_milestones = old_stars // 100
    new_milestones = new_stars // 100
    lost_months = max(0, old_milestones - new_milestones)

    now_naive = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
    current_end = user.premium_ends
    new_end = current_end

    if lost_months > 0 and current_end and not user.is_lifetime_premium:
        if isinstance(current_end, datetime.date) and not isinstance(current_end, datetime.datetime):
            current_end = datetime.datetime.combine(current_end, datetime.time.min)
        if getattr(current_end, "tzinfo", None) is not None:
            current_end = current_end.replace(tzinfo=None)

        days_to_sub = lost_months * 30
        new_end = current_end - datetime.timedelta(days=days_to_sub)
        if new_end < now_naive:
            new_end = None

    update_vals = {
        "stars_donated": new_stars,
    }
    if lost_months > 0 and not user.is_lifetime_premium:
        update_vals["premium_ends"] = new_end

    await session.execute(
        update(Users)
        .where(Users.user_id == user_id)
        .values(**update_vals)
    )
    await cache_delete(f"user:{user_id}")
    return new_stars, new_end


async def sync_historical_donations(session: AsyncSession) -> int:
    """
    Synchronizes historical completed support donations from the 'payments' table into 'users.stars_donated'.
    Variant B: For users who donated >= 100 stars and don't have active premium, grants earned sponsorship.
    Returns: count of updated users.
    """
    from .models import Payment

    stmt = (
        select(Payment.user_id, func.sum(Payment.amount).label("total_stars"))
        .where(
            Payment.status == "completed",
            Payment.currency == "XTR",
            or_(
                Payment.payload.like("support_%"),
                Payment.payload.like("sponsor_%"),
            ),
        )
        .group_by(Payment.user_id)
    )
    result = await session.execute(stmt)
    records = result.all()

    updated_count = 0
    now_naive = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)

    for user_id, total_stars in records:
        if not total_stars or total_stars <= 0:
            continue

        user_stmt = select(Users).where(Users.user_id == user_id).with_for_update()
        user_res = await session.execute(user_stmt)
        user = user_res.scalar_one_or_none()

        if not user:
            user, _ = await create_user(session, user_id)
            user_res = await session.execute(user_stmt)
            user = user_res.scalar_one_or_none()

        current_stars = user.stars_donated or 0
        if current_stars >= total_stars:
            continue

        new_stars = total_stars
        old_milestones = current_stars // 100
        new_milestones = new_stars // 100
        earned_months = max(0, new_milestones - old_milestones)

        update_vals = {
            "stars_donated": new_stars,
        }

        if earned_months > 0 and not user.is_lifetime_premium:
            current_end = user.premium_ends
            if current_end:
                if isinstance(current_end, datetime.date) and not isinstance(current_end, datetime.datetime):
                    current_end = datetime.datetime.combine(current_end, datetime.time.min)
                if getattr(current_end, "tzinfo", None) is not None:
                    current_end = current_end.replace(tzinfo=None)
                if current_end < now_naive:
                    current_end = now_naive
            else:
                current_end = now_naive

            days_to_add = earned_months * 30
            new_end = current_end + datetime.timedelta(days=days_to_add)
            update_vals["premium_ends"] = new_end

            settings = dict(user.settings_json or {})
            settings["premium_expired_notified"] = False
            update_vals["settings_json"] = settings

        await session.execute(
            update(Users)
            .where(Users.user_id == user_id)
            .values(**update_vals)
        )
        await cache_delete(f"user:{user_id}")
        updated_count += 1

    return updated_count


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
        func.count().filter(Statistics.status == "failed_download").label("error_count")
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
        await create_user(session=session, user_id=user_id)  # noqa: F841
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
        await create_user(session=session, user_id=user_id)  # noqa: F841
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
    res = await session.execute(
        update(Users).where(Users.user_id == user_id).values(is_banned=True)
    )
    if res.rowcount == 0:
        session.add(Users(user_id=user_id, is_banned=True))
        await session.flush()
    await cache_delete(f"user:{user_id}")

async def unban_user(session: AsyncSession, user_id: int) -> None:
    res = await session.execute(
        update(Users).where(Users.user_id == user_id).values(is_banned=False)
    )
    if res.rowcount == 0:
        session.add(Users(user_id=user_id, is_banned=False))
        await session.flush()
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

    await cache_set("global_settings", data, ttl=86400)
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
    stmt_users = (
        select(Users.user_id)
        .where(
            Users.is_banned == False,
            or_(
                Users.settings_json["profile"]["news_spam"].as_boolean() == True,
                Users.settings_json["profile"]["news_spam"].as_string() == "true",
            ),
        )
    )
    result_users = await session.execute(stmt_users)
    user_ids = [row[0] for row in result_users.fetchall()]

    stmt_chats = (
        select(Chats.chat_id)
        .where(
            or_(
                Chats.settings_json["profile"]["news_spam"].as_boolean() == True,
                Chats.settings_json["profile"]["news_spam"].as_string() == "true",
            ),
        )
    )
    result_chats = await session.execute(stmt_chats)
    chat_ids = [row[0] for row in result_chats.fetchall()]

    return user_ids + chat_ids

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


async def get_media_cache_entry_by_file_id(
    session: AsyncSession, file_id: str
) -> tuple[int, MediaCacheDTO] | None:
    """Finds media cache entry and its media_id by telegram file_id."""
    stmt = select(MediaCache).where(
        or_(
            MediaCache.telegram_file_id == file_id,
            MediaCache.telegram_document_file_id == file_id,
        )
    )
    result = await session.execute(stmt)
    db_obj = result.scalar_one_or_none()
    if db_obj:
        return db_obj.media_id, MediaCacheDTO.model_validate(db_obj, from_attributes=True)

    try:
        stmt_json = select(MediaCache).where(
            cast(MediaCache.data, String).contains(file_id)
        ).limit(1)
        res_json = await session.execute(stmt_json)
        db_obj = res_json.scalar_one_or_none()
        if db_obj:
            return db_obj.media_id, MediaCacheDTO.model_validate(db_obj, from_attributes=True)
    except Exception:
        pass

    return None


async def upsert_media_cache(session: AsyncSession, dto: MediaCacheDTO) -> MediaCacheDTO:
    """Создает новую запись или обновляет существующую за 1 SQL-запрос"""

    values_to_insert = dto.model_dump(exclude_none=True)

    stmt = insert(MediaCache).values(**values_to_insert)

    do_update_stmt = stmt.on_conflict_do_update(
        index_elements=['cache_key'],
        set_=stmt.excluded
    ).returning(MediaCache)

    result = await session.execute(do_update_stmt)
    await session.commit()

    updated_obj = result.scalar_one()
    return MediaCacheDTO.model_validate(updated_obj, from_attributes=True)


async def delete_media_cache(session: AsyncSession, cache_key: str) -> bool:
    """Удаляет запись из кэша (например, если файл удалили с серверов Telegram)"""

    stmt = delete(MediaCache).where(MediaCache.cache_key == cache_key).returning(MediaCache.media_id)
    result = await session.execute(stmt)
    await session.commit()

    deleted_id = result.scalar_one_or_none()
    return deleted_id is not None


async def clear_all_media_cache(session: AsyncSession) -> int:
    """Удаляет все записи из кэша. Возвращает количество удаленных записей."""
    stmt = delete(MediaCache)
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount


# ==========================================
# USER SAVES (МЕДИАТЕКА) & CACHED MUSIC SEARCH
# ==========================================

async def save_user_media(
    session: AsyncSession,
    user_id: int,
    label: str,
    telegram_file_id: str,
    media_type: str,
    title: str | None = None,
    caption: str | None = None,
    is_public: bool = False,
    file_unique_id: str | None = None,
) -> UserSaves:
    """Сохранить медиа в медиатеку пользователя"""
    save = UserSaves(
        user_id=user_id,
        label=label.strip(),
        telegram_file_id=telegram_file_id,
        file_unique_id=file_unique_id,
        media_type=media_type,
        title=title,
        caption=caption,
        is_public=is_public,
        is_approved=False,
    )
    session.add(save)
    await session.commit()
    return save


async def get_save_by_id(session: AsyncSession, save_id: int) -> UserSaves | None:
    """Получить сохранёнку по ID"""
    stmt = select(UserSaves).where(UserSaves.id == save_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def toggle_save_public(session: AsyncSession, user_id: int, save_id: int) -> UserSaves | None:
    """Отправить в публичную библиотеку или вернуть в личную."""
    save = await get_save_by_id(session, save_id)
    if not save or save.user_id != user_id:
        return None

    save.is_public = not save.is_public
    save.is_approved = False
    await session.commit()
    return save


async def increment_save_uses(session: AsyncSession, save_id: int, user_id: int | None = None) -> bool:
    """Увеличить счётчик использований сохранёнки (только если использует другой пользователь)"""
    stmt = update(UserSaves).where(UserSaves.id == save_id)
    if user_id is not None:
        stmt = stmt.where(UserSaves.user_id != user_id)
    stmt = stmt.values(uses_count=UserSaves.uses_count + 1)
    result = await session.execute(stmt)
    await session.commit()
    return bool(result.rowcount and result.rowcount > 0)


# Порог strict_word_similarity для нечёткого поиска по целым словам.
# Опечатки: «снае»→«санае» = 0.375, «лижит»→«лижет» = 0.333. Шум: «снае»→«нае*ал» = 0.286.
FUZZY_WORD_THRESHOLD = 0.33


async def _search_saves(session: AsyncSession, base, query: str, order: list, limit: int) -> list[UserSaves]:
    """Общий поиск по сохранёнкам.

    1. Полнотекст (search_vector, стемминг) ИЛИ подстрока ILIKE по label/title/caption —
       одним запросом, чтобы частично набранное слово («кот» → «котики») тоже находилось.
    2. Если пусто — нечёткий pg_trgm по отдельным словам label (опечатки):
       «снае» находит и «Санае», и «Санае Лижет рейму».
    Ошибочная раскладка (ghbdtn → привет) и транслит (санае ⇄ sanae) учитываются в обоих шагах.
    """
    if not query.strip():
        result = await session.execute(base.order_by(*order).limit(limit))
        return list(result.scalars().all())

    variants = query_variants(query)

    # websearch_to_tsquery понимает «or» и никогда не падает на пользовательском вводе
    ts_query = func.websearch_to_tsquery(text("'russian'::regconfig"), " or ".join(variants))
    conditions = [UserSaves.search_vector.op("@@")(ts_query)]
    for v in variants:
        pattern = f"%{escape_ilike(v)}%"
        conditions += [
            UserSaves.label.ilike(pattern, escape="\\"),
            UserSaves.title.ilike(pattern, escape="\\"),
            UserSaves.caption.ilike(pattern, escape="\\"),
        ]

    result = await session.execute(base.where(or_(*conditions)).order_by(*order).limit(limit))
    rows = list(result.scalars().all())
    if rows:
        return rows

    # `q <<% label` — есть ли в label целое слово, похожее на q (strict_word_similarity), идёт через GIN-индекс.
    # Обычный `%` сравнивает с названием целиком: лишние слова в «Санае Лижет рейму» топили сходство.
    # Нестрогий `<%` засчитывает кусок слова и тянет шум («снае» → «Нае*ал»).
    # Дефолтный порог 0.5 слишком строг для коротких слов: одна опечатка в «санае» даёт 0.375.
    await session.execute(select(func.set_config("pg_trgm.strict_word_similarity_threshold", str(FUZZY_WORD_THRESHOLD), True)))
    fuzzy = or_(*[literal(v).op("<<%")(UserSaves.label) for v in variants])
    score = func.greatest(*[func.strict_word_similarity(v, UserSaves.label) for v in variants])
    result = await session.execute(base.where(fuzzy).order_by(score.desc(), *order).limit(limit))
    return list(result.scalars().all())


async def search_user_saves(
    session: AsyncSession,
    user_id: int,
    query: str = "",
    limit: int = 20,
    media_types: tuple[str, ...] | None = None,
) -> list[UserSaves]:
    """Поиск по сохранёнкам пользователя (или последние, если query пустой)."""
    base = select(UserSaves).where(UserSaves.user_id == user_id)
    if media_types:
        base = base.where(UserSaves.media_type.in_(media_types))
    return await _search_saves(session, base, query, [UserSaves.created_at.desc()], limit)


async def search_public_saves(
    session: AsyncSession,
    query: str = "",
    exclude_user_id: int | None = None,
    limit: int = 20,
    media_types: tuple[str, ...] | None = None,
) -> list[UserSaves]:
    """Поиск по публичной библиотеке: сначала популярные, затем свежие."""
    base = select(UserSaves).where(
        UserSaves.is_public.is_(True),
        UserSaves.is_approved.is_(True),
    )
    if exclude_user_id:
        base = base.where(UserSaves.user_id != exclude_user_id)
    if media_types:
        base = base.where(UserSaves.media_type.in_(media_types))
    return await _search_saves(session, base, query, [UserSaves.uses_count.desc(), UserSaves.created_at.desc()], limit)


async def get_user_saves(
    session: AsyncSession,
    user_id: int,
    offset: int = 0,
    limit: int = 10,
    media_types: tuple[str, ...] | None = None,
) -> list[UserSaves]:
    """Получить список сохранёнок пользователя с опциональной фильтрацией по типам медиа"""
    stmt = select(UserSaves).where(UserSaves.user_id == user_id)
    if media_types:
        stmt = stmt.where(UserSaves.media_type.in_(media_types))
    stmt = stmt.order_by(UserSaves.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def delete_user_save(session: AsyncSession, user_id: int, save_id: int) -> bool:
    """Удалить сохранёнку по ID"""
    stmt = delete(UserSaves).where(
        UserSaves.id == save_id,
        UserSaves.user_id == user_id,
    )
    result = await session.execute(stmt)
    return bool(result.rowcount and result.rowcount > 0)


async def get_user_saves_count(
    session: AsyncSession,
    user_id: int,
    media_types: tuple[str, ...] | None = None,
) -> int:
    """Количество сохранёнок пользователя с опциональной фильтрацией по типам медиа."""
    stmt = select(func.count()).select_from(UserSaves).where(UserSaves.user_id == user_id)
    if media_types:
        stmt = stmt.where(UserSaves.media_type.in_(media_types))
    result = await session.execute(stmt)
    return result.scalar() or 0


def _same_media(telegram_file_id: str, file_unique_id: str | None):
    """Тот же файл: по file_unique_id, а для старых записей без него — по file_id."""
    cond = UserSaves.telegram_file_id == telegram_file_id
    return or_(cond, UserSaves.file_unique_id == file_unique_id) if file_unique_id else cond


async def get_save_by_file_id(
    session: AsyncSession, user_id: int, telegram_file_id: str, file_unique_id: str | None = None
) -> UserSaves | None:
    """Найти личную сохранёнку пользователя с тем же файлом (дубль медиа)."""
    stmt = select(UserSaves).where(
        UserSaves.user_id == user_id,
        _same_media(telegram_file_id, file_unique_id),
    ).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_save_by_label(
    session: AsyncSession, user_id: int, label: str
) -> UserSaves | None:
    """Найти личную сохранёнку пользователя по названию без учёта регистра (дубль названия)."""
    stmt = select(UserSaves).where(
        UserSaves.user_id == user_id,
        func.lower(UserSaves.label) == label.strip().lower(),
    ).limit(1)
    return (await session.execute(stmt)).scalar_one_or_none()


async def get_public_save_by_file_id(
    session: AsyncSession,
    telegram_file_id: str,
    file_unique_id: str | None = None,
    exclude_save_id: int | None = None,
) -> UserSaves | None:
    """Найти публичный мем (одобренный или на модерации) с тем же файлом."""
    stmt = select(UserSaves).where(
        _same_media(telegram_file_id, file_unique_id),
        UserSaves.is_public.is_(True),
    )
    if exclude_save_id is not None:
        stmt = stmt.where(UserSaves.id != exclude_save_id)
    return (await session.execute(stmt.limit(1))).scalar_one_or_none()


async def replace_save_media(
    session: AsyncSession,
    save_id: int,
    user_id: int,
    new_file_id: str,
    new_media_type: str,
    new_title: str | None = None,
    new_caption: str | None = None,
    new_file_unique_id: str | None = None,
) -> UserSaves | None:
    """Заменить медиафайл в сохранёнке (при конфликте названия).

    Сбрасывает is_approved в False, если сохранёнка публичная.
    """
    save = await get_save_by_id(session, save_id)
    if not save or save.user_id != user_id:
        return None
    save.telegram_file_id = new_file_id
    save.file_unique_id = new_file_unique_id
    save.media_type = new_media_type
    if new_title is not None:
        save.title = new_title
    if new_caption is not None:
        save.caption = new_caption
    if save.is_public:
        save.is_approved = False  # сброс модерации при замене медиа
    await session.commit()
    return save


async def rename_user_save(
    session: AsyncSession,
    save_id: int,
    user_id: int,
    new_label: str,
) -> UserSaves | None:
    """Переименовать сохранёнку.

    Если сохранёнка была одобрена публично (is_public=True, is_approved=True),
    переименование автоматически сбрасывает is_approved в False — требуется
    повторная модерация.
    """
    save = await get_save_by_id(session, save_id)
    if not save or save.user_id != user_id:
        return None
    new_label = new_label.strip()
    if new_label != save.label and save.is_public and save.is_approved:
        save.is_approved = False  # публичный мем требует повторной модерации
    save.label = new_label
    await session.commit()
    return save


async def get_pending_public_save(session: AsyncSession) -> UserSaves | None:
    stmt = (
        select(UserSaves)
        .where(UserSaves.is_public.is_(True), UserSaves.is_approved.is_(False))
        .order_by(UserSaves.created_at.asc())
        .limit(1)
    )
    return (await session.execute(stmt)).scalar_one_or_none()


async def moderate_public_save(session: AsyncSession, save_id: int, approve: bool) -> UserSaves | None:
    save = await get_save_by_id(session, save_id)
    if not save or not save.is_public or save.is_approved:
        return None
    if approve:
        save.is_approved = True
    else:
        save.is_public = False
    await session.commit()
    return save


MUSIC_PLATFORMS = (
    "spotify",
    "applemusic",
    "apple_music",
    "deezer",
    "soundcloud",
    "ytmusic",
    "youtube",
)


def _calc_music_fuzzy_score(query: str, author: str, title: str) -> float:
    """
    Вычисляет коэффициент схожести (0.0 - 1.0) между поисковым запросом и треком (автор/название).
    Учитывает как прямую схожесть строки, так и пословное совпадение.
    """
    from difflib import SequenceMatcher

    q = query.lower().strip()
    full1 = f"{author} {title}".lower().strip()
    full2 = f"{title} {author}".lower().strip()

    score1 = SequenceMatcher(None, q, full1).ratio()
    score2 = SequenceMatcher(None, q, full2).ratio()
    best_direct = max(score1, score2)

    q_words = q.split()
    t_words = full1.split()
    if q_words and t_words:
        word_scores = []
        for qw in q_words:
            best_w = max(SequenceMatcher(None, qw, tw).ratio() for tw in t_words)
            word_scores.append(best_w)
        token_score = sum(word_scores) / len(word_scores)
    else:
        token_score = 0.0

    return max(best_direct, token_score)


async def search_cached_music(
    session: AsyncSession,
    query: str,
    limit: int = 15,
    platforms: tuple[str, ...] | None = MUSIC_PLATFORMS,
) -> list[MediaCacheDTO]:
    """
    Поиск по кэшированной музыке с поддержкой:
    1. Всех музыкальных сервисов + YouTube audio
    2. Регистронезависимой проверки платформ
    3. Мульти-словного поиска (Артист + Название в любом порядке)
    4. Fuzzy / опечаточного fallback-поиска по похожести (если точных совпадений мало)
    """
    stmt = (
        select(MediaCache)
        .where(
            MediaCache.media_type == "audio",
            MediaCache.telegram_file_id.isnot(None),
            func.lower(MediaCache.platform) != "tiktok",
            ~MediaCache.cache_key.like("%:lossless%"),
            or_(
                MediaCache.telegram_document_file_id.is_(None),
                MediaCache.telegram_file_id != MediaCache.telegram_document_file_id,
            ),
        )
    )
    if platforms:
        lower_platforms = [p.lower() for p in platforms if p.lower() != "tiktok"]
        stmt = stmt.where(func.lower(MediaCache.platform).in_(lower_platforms))

    clean_query = query.strip()
    if not clean_query:
        # Без запроса — последние добавленные треки
        stmt = stmt.order_by(MediaCache.created_at.desc()).limit(limit)
        result = await session.execute(stmt)
        rows = result.scalars().all()
        return [MediaCacheDTO.model_validate(row, from_attributes=True) for row in rows]

    words = [w for w in clean_query.split() if w]
    found_rows: list[MediaCache] = []
    seen_ids: set[int] = set()

    relevance_rank = case(
        (MediaCache.data["title"].as_string().ilike(clean_query), 1),
        (MediaCache.data["title"].as_string().ilike(f"{clean_query}%"), 2),
        (MediaCache.data["title"].as_string().ilike(f"%{clean_query}%"), 3),
        else_=4,
    )

    # 1. Поиск: ВСЕ слова присутствуют (в названии или авторе)
    word_filters = [
        or_(
            MediaCache.data["title"].as_string().ilike(f"%{w}%"),
            MediaCache.data["author"].as_string().ilike(f"%{w}%"),
        )
        for w in words
    ]
    and_stmt = (
        stmt.where(and_(*word_filters))
        .order_by(relevance_rank, MediaCache.created_at.desc())
        .limit(limit)
    )
    res = await session.execute(and_stmt)
    for row in res.scalars().all():
        if row.media_id not in seen_ids:
            seen_ids.add(row.media_id)
            found_rows.append(row)

    # 2. Если результатов мало и слов больше одного — ищем совпадение хотя бы одного слова
    if len(found_rows) < limit and len(words) > 1:
        or_stmt = stmt.where(or_(*word_filters))
        if seen_ids:
            or_stmt = or_stmt.where(~MediaCache.media_id.in_(seen_ids))
        or_stmt = or_stmt.order_by(relevance_rank, MediaCache.created_at.desc()).limit(limit - len(found_rows))
        res = await session.execute(or_stmt)
        for row in res.scalars().all():
            if row.media_id not in seen_ids:
                seen_ids.add(row.media_id)
                found_rows.append(row)

    # 3. Fuzzy / опечаточный поиск (если точных совпадений нет или меньше лимита)
    if len(found_rows) < limit:
        cand_stmt = stmt
        if seen_ids:
            cand_stmt = cand_stmt.where(~MediaCache.media_id.in_(seen_ids))
        cand_stmt = cand_stmt.order_by(MediaCache.created_at.desc()).limit(200)
        candidates = (await session.execute(cand_stmt)).scalars().all()

        scored_candidates = []
        for cand in candidates:
            data = cand.data or {}
            c_title = data.get("title") if isinstance(data, dict) else getattr(data, "title", None)
            c_author = data.get("author") if isinstance(data, dict) else getattr(data, "author", None)
            score = _calc_music_fuzzy_score(clean_query, c_author or "", c_title or "")
            if score >= 0.55:
                scored_candidates.append((score, cand))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        for _, cand in scored_candidates[: limit - len(found_rows)]:
            if cand.media_id not in seen_ids:
                seen_ids.add(cand.media_id)
                found_rows.append(cand)

    return [MediaCacheDTO.model_validate(row, from_attributes=True) for row in found_rows]


async def ban_user_from_public_saves(session: AsyncSession, user_id: int) -> bool:
    """Заблокировать пользователю возможность предлагать мемы в публичную библиотеку."""
    stmt = select(PublicSavesBan).where(PublicSavesBan.user_id == user_id)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if not existing:
        ban = PublicSavesBan(user_id=user_id)
        session.add(ban)
        await session.commit()
    await cache_set(f"public_saves_banned:{user_id}", {"banned": True}, ttl=86400)
    return True


async def unban_user_from_public_saves(session: AsyncSession, user_id: int) -> bool:
    """Разблокировать пользователю возможность предлагать мемы."""
    stmt = delete(PublicSavesBan).where(PublicSavesBan.user_id == user_id)
    res = await session.execute(stmt)
    await session.commit()
    await cache_delete(f"public_saves_banned:{user_id}")
    return bool(res.rowcount and res.rowcount > 0)


async def is_user_public_saves_banned(session: AsyncSession, user_id: int) -> bool:
    """Проверить, заблокирован ли пользователь от публикации мемов."""
    cached = await cache_get(f"public_saves_banned:{user_id}")
    if cached is not None and isinstance(cached, dict):
        return bool(cached.get("banned", False))

    stmt = select(PublicSavesBan).where(PublicSavesBan.user_id == user_id)
    res = (await session.execute(stmt)).scalar_one_or_none()
    is_banned = res is not None
    await cache_set(f"public_saves_banned:{user_id}", {"banned": is_banned}, ttl=3600)
    return is_banned


async def list_public_saves_banned_users(session: AsyncSession) -> list[int]:
    """Получить список ID всех заблокированных от предложки пользователей."""
    stmt = select(PublicSavesBan.user_id).order_by(PublicSavesBan.created_at.desc())
    res = await session.execute(stmt)
    return list(res.scalars().all())


