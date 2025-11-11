import logging
from datetime import date

from . import database_manager
from sqlalchemy import select, update
from .models import Users, UserSettings, Chats, ChatSettings


async def get_user(user_id: int) -> Users | None:
    """Get user from database

    Args:
        user_id (int): User ID

    Returns:
        Users | None: User object
    """
    async with database_manager.async_session() as session:
        result = await session.execute(select(Users).where(Users.user_id == user_id))
        return result.scalar_one_or_none()

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
    async with database_manager.async_session() as session:
        result = await session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        return result.scalar_one_or_none()

async def update_user_premium(user_id: int, is_premium: bool, premium_ends: date):
    async with database_manager.async_session() as session:
        await session.execute(
            update(Users)
            .where(Users.user_id == user_id)
            .values(is_premium=is_premium, premium_ends=premium_ends)
        )
        await session.commit()

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


async def get_chat(chat_id: int) -> Chats | None:
    """Get chat from database

    Args:
        chat_id (int): User ID

    Returns:
        Chats | None: Chat object
    """
    async with database_manager.async_session() as session:
        result = await session.execute(select(Chats).where(Chats.chat_id == chat_id))
        return result.scalar_one_or_none()

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
    async with database_manager.async_session() as session:
        result = await session.execute(select(ChatSettings).where(ChatSettings.chat_id == chat_id))
        settings = result.scalar_one_or_none()
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
