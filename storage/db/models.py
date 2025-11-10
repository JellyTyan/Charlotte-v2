import datetime
from sqlalchemy import BigInteger, Boolean, Date, Integer, String, ForeignKey, ARRAY
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import List


class Base(AsyncAttrs, DeclarativeBase):
    pass

class Users(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    stars_donated: Mapped[int] = mapped_column(Integer, default=0)
    premium_ends: Mapped[datetime.date] = mapped_column(Date, default=datetime.date.today)
    banned: Mapped[bool] = mapped_column(Boolean, default=False)

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
