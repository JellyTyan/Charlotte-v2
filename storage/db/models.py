import datetime
from sqlalchemy import BigInteger, Boolean, Date, Integer, String, DateTime, JSON, Text
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    pass

class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    is_lifetime_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    stars_donated: Mapped[int] = mapped_column(Integer, default=0)
    premium_ends: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today)
    last_used: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today, nullable=True)
    settings_json: Mapped[dict] = mapped_column(JSON, default=dict)


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
        DateTime(timezone=True), default=datetime.datetime.now, nullable=False
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
        DateTime(timezone=True), default=datetime.datetime.now, nullable=False
    )


class MediaCache(Base):
    __tablename__ = "mediacache"

    media_id: Mapped[int] = mapped_column(primary_key=True)
    file_id: Mapped[str] = mapped_column(String, nullable=False)
    service: Mapped[str] = mapped_column(String, nullable=False)
    media_type = mapped_column(String)  # 'video', 'audio', 'photo', 'gallery'

    title: Mapped[str] = mapped_column(String, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    author: Mapped[str] = mapped_column(String, nullable=True)
    duration: Mapped[str] = mapped_column(String, nullable=True)

    thumbnail_file_id: Mapped[str] = mapped_column(String, nullable=True)

    platform: Mapped[str] = mapped_column(String)  # 'youtube', 'instagram' и т.д.
    attachments: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.datetime.now, nullable=False
    )