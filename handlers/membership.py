"""The bot's own membership: blocked/unblocked in DM, added/kicked/muted/promoted in groups, group → supergroup."""
import logging

from aiogram import F, Router
from aiogram.types import ChatMemberUpdated, Message
from sqlalchemy.ext.asyncio import AsyncSession

from storage.db.crud import mark_user_blocked, migrate_chat, remember_bot_status

logger = logging.getLogger(__name__)

router = Router()


@router.my_chat_member()
async def on_my_chat_member(event: ChatMemberUpdated, db_session: AsyncSession) -> None:
    member = event.new_chat_member
    if event.chat.type == "private":
        # kicked = the user blocked the bot; anything else = unblocked / started again
        await mark_user_blocked(db_session, event.chat.id, blocked=member.status == "kicked")
    else:
        # DB row + bot_can_post cache updated right away: no waiting for the cache to expire after an unmute
        await remember_bot_status(db_session, event.chat.id, member, owner_id=event.from_user.id)
    await db_session.commit()
    logger.info(f"Bot status in {event.chat.id}: {event.old_chat_member.status} -> {member.status}")


@router.message(F.migrate_to_chat_id)
async def on_group_migrated(message: Message, db_session: AsyncSession) -> None:
    await migrate_chat(db_session, message.chat.id, message.migrate_to_chat_id)
    await db_session.commit()
    logger.info(f"Chat {message.chat.id} migrated to supergroup {message.migrate_to_chat_id}")
