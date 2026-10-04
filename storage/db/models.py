import datetime
from datetime import timezone
from typing import Any
from sqlalchemy import BigInteger, Boolean, Date, Integer, String, DateTime, JSON, Text, Index, Computed
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    pass

class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_lifetime_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    stars_donated: Mapped[int] = mapped_column(Integer, default=0)
    premium_ends: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=True)
    last_used: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today, nullable=True)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)

    @property
    def is_premium(self) -> bool:
        if self.is_lifetime_premium:
            return True
        if not self.premium_ends:
            return False

        premium_ends = self.premium_ends
        if isinstance(premium_ends, datetime.date) and not isinstance(premium_ends, datetime.datetime):
            premium_ends = datetime.datetime.combine(premium_ends, datetime.time.max)

        # If premium_ends is naive, compare with naive utcnow
        now = datetime.datetime.now(timezone.utc)
        if getattr(premium_ends, 'tzinfo', None) is None:
            now = now.replace(tzinfo=None)
        return premium_ends > now


class Chats(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    owner_id: Mapped[int] = mapped_column(BigInteger)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)


class Statistics(Base):
    __tablename__ = "statistics"

    event_id: Mapped[int] = mapped_column(primary_key=True)
    service_name: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_time: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), nullable=True)


class BotSetting(Base):
    __tablename__ = "bot_settings"

    key = mapped_column(String, primary_key=True)
    value = mapped_column(String)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    payload: Mapped[str] = mapped_column(String, nullable=False)
    telegram_payment_charge_id: Mapped[str] = mapped_column(String, nullable=False)
    provider_payment_charge_id: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="completed")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.datetime.now(timezone.utc), nullable=False
    )


class MediaCache(Base):
    __tablename__ = "mediacache"

    media_id: Mapped[int] = mapped_column(primary_key=True)

    # Unique key like "yt:dQw4w9WgXcQ" or "ig:p_123")
    cache_key: Mapped[str] = mapped_column(String, unique=True, nullable=False)

    # ID file in Telgeram. May be null if gallery
    telegram_file_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # ID raw file in Telegram.
    telegram_document_file_id: Mapped[str | None] = mapped_column(String, nullable=True)

    media_type: Mapped[str] = mapped_column(String, nullable=False)  # 'video', 'audio', 'gallery'
    platform: Mapped[str] = mapped_column(String, nullable=False)  # 'youtube', 'instagram', 'tiktok'

    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(timezone.utc),
        nullable=False
    )


class UserSaves(Base):
    __tablename__ = "user_saves"
    __table_args__ = (
        Index("ix_user_saves_user_label", "user_id", "label"),
        Index("ix_user_saves_search_vector", "search_vector", postgresql_using="gin"),
        Index("ix_user_saves_label_trgm", "label", postgresql_using="gin", postgresql_ops={"label": "gin_trgm_ops"}),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    telegram_file_id: Mapped[str] = mapped_column(String, nullable=False)
    # NULL у записей, созданных до миграции b7c8d9e0f1a2 — для них дубли ищутся по telegram_file_id
    file_unique_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)  # 'video', 'photo', 'audio', 'gif'
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    uses_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(timezone.utc),
        nullable=False
    )
    # Заполняется самой БД (миграция a1b2c3d4e5f6); deferred — не тянем в каждый SELECT
    search_vector: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('russian', coalesce(label, '') || ' ' || coalesce(title, '') || ' ' || coalesce(caption, ''))",
            persisted=True,
        ),
        deferred=True,
    )


class PublicSavesBan(Base):
    __tablename__ = "public_saves_bans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(timezone.utc),
        nullable=False
    )

