import datetime
from sqlalchemy import BigInteger, Boolean, Date, Integer, String, ForeignKey, ARRAY, DateTime
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List


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

    settings: Mapped["UserSettings"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), unique=True)
    lang: Mapped[str] = mapped_column(String(2), default="en")
    send_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    send_raw: Mapped[bool] = mapped_column(Boolean, default=False)
    send_music_covers: Mapped[bool] = mapped_column(Boolean, default=False)
    send_reactions: Mapped[bool] = mapped_column(Boolean, default=True)
    ping_reaction: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_caption: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_translate_titles: Mapped[bool] = mapped_column(Boolean, default=False)
    title_language: Mapped[str] = mapped_column(String(2), default="en")

    # Experimental
    lossless_mode: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["Users"] = relationship(back_populates="settings")


class Chats(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    owner_id: Mapped[int] = mapped_column(BigInteger)

    settings: Mapped["ChatSettings"] = relationship(
        back_populates="chat", uselist=False, cascade="all, delete-orphan"
    )


class ChatSettings(Base):
    __tablename__ = "chat_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.chat_id"), unique=True)
    lang: Mapped[str] = mapped_column(String(2), default="en")
    send_notifications: Mapped[bool] = mapped_column(Boolean, default=True)
    send_raw: Mapped[bool] = mapped_column(Boolean, default=False)
    send_music_covers: Mapped[bool] = mapped_column(Boolean, default=False)
    send_reactions: Mapped[bool] = mapped_column(Boolean, default=True)
    ping_reaction: Mapped[bool] = mapped_column(Boolean, default=False)
    auto_caption: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_translate_titles: Mapped[bool] = mapped_column(Boolean, default=False)
    title_language: Mapped[str] = mapped_column(String(2), default="en")
    preferred_services: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    blocked_services: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    allow_playlists: Mapped[bool] = mapped_column(Boolean, default=True)

    chat: Mapped["Chats"] = relationship(back_populates="settings")


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
