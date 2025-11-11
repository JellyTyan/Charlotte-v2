import asyncio
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Union

from aiogram import types
from aiogram.enums import InputMediaType
from aiogram.utils.media_group import MediaGroupBuilder

from utils import delete_files, truncate_string
from models.media import MediaContent, MediaType
from models.errors import BotError, ErrorCode
from storage.db.crud import get_user_settings, get_chat_settings, create_chat, create_user
from storage.db.models import UserSettings, ChatSettings

logger = logging.getLogger(__name__)


class MediaSender:
    def __init__(self):
        self._files_to_cleanup: List[Path] = []

    async def get_settings(self, chat_id: int, user_id: int) -> Union[UserSettings, ChatSettings]:
        logger.debug(f"Getting settings for chat_id={chat_id}, user_id={user_id}")
        if chat_id < 0:
            settings = await get_chat_settings(chat_id)
            if not settings:
                logger.info(f"Creating new chat {chat_id}")
                await create_chat(chat_id, user_id)
                settings = await get_chat_settings(chat_id)
        else:
            settings = await get_user_settings(user_id)
            if not settings:
                logger.info(f"Creating new user {user_id}")
                await create_user(user_id)
                settings = await get_user_settings(user_id)
        return settings

    async def send(self, message: types.Message, content: List[MediaContent], user_id: Optional[int] = None) -> None:
        if not message.bot:
            raise BotError(code=ErrorCode.DOWNLOAD_FAILED, message="Bot instance not available")

        try:
            media_items, audio_items, gif_items, caption = self._parse_media(content)
            logger.info(f"Sending media: {len(media_items)} media, {len(audio_items)} audio, {len(gif_items)} gif")

            if user_id is None:
                user_id = message.from_user.id if hasattr(message, 'from_user') and message.from_user else message.chat.id
            settings = await self.get_settings(message.chat.id, user_id)

            if media_items:
                await self._send_media_group(message, media_items, caption, settings)

            for audio in audio_items:
                await message.bot.send_chat_action(message.chat.id, "upload_voice")
                await self._send_audio(message, audio, settings)

            for gif in gif_items:
                await message.bot.send_chat_action(message.chat.id, "upload_video")
                await message.answer_animation(
                    animation=types.FSInputFile(gif.path),
                    disable_notification=not settings.send_notifications
                )
                self._files_to_cleanup.append(gif.path)

            logger.info(f"Successfully sent all media to chat {message.chat.id}")

        except BotError:
            raise
        except Exception as e:
            logger.error(f"Media send error: {e}", exc_info=True)
            raise BotError(code=ErrorCode.DOWNLOAD_FAILED, message=str(e), critical=True)
        finally:
            if self._files_to_cleanup:
                logger.debug(f"Cleaning up {len(self._files_to_cleanup)} files")
                await delete_files(self._files_to_cleanup)
                self._files_to_cleanup.clear()

    async def _send_media_group(self, message: types.Message, content: List[MediaContent],
                                caption: Optional[str], settings: Union[UserSettings, ChatSettings]) -> None:
        if not content:
            return

        MEDIA_GROUP_LIMIT = 10
        total_groups = (len(content) + MEDIA_GROUP_LIMIT - 1) // MEDIA_GROUP_LIMIT
        logger.debug(f"Sending {len(content)} items in {total_groups} group(s)")

        for i in range(0, len(content), MEDIA_GROUP_LIMIT):
            group_items = content[i:i + MEDIA_GROUP_LIMIT]
            media_group = MediaGroupBuilder()

            if caption and i == 0 and settings.auto_caption:
                media_group.caption = truncate_string(caption, 1024)

            for item in group_items:
                if item.type == MediaType.PHOTO:
                    media_group.add_photo(media=types.FSInputFile(item.path))
                elif item.type == MediaType.VIDEO:
                    media_group.add_video(
                        media=types.FSInputFile(item.path),
                        supports_streaming=True,
                        width=item.width,
                        height=item.height,
                        duration=item.duration
                    )
                self._files_to_cleanup.append(item.path)

            if message.bot:
                await message.bot.send_chat_action(message.chat.id, "upload_video")
            await message.answer_media_group(
                media=media_group.build(),
                disable_notification=not settings.send_notifications
            )
            logger.debug(f"Sent media group {i // MEDIA_GROUP_LIMIT + 1}/{total_groups}")


    async def _send_audio(self, message: types.Message, audio: MediaContent,
                         settings: Union[UserSettings, ChatSettings]) -> None:
        logger.debug(f"Sending audio: {audio.title or 'Unknown'}")
        if message.bot:
            await message.bot.send_chat_action(message.chat.id, "upload_voice")
        await message.answer_audio(
            audio=types.FSInputFile(audio.path),
            disable_notification=not settings.send_notifications,
            thumbnail=types.FSInputFile(audio.cover) if audio.cover else None,
            title=audio.title,
            duration=audio.duration,
            performer=audio.performer
        )

        if audio.cover and settings.send_music_covers:
            logger.debug("Sending audio cover as document")
            await message.answer_document(
                document=types.FSInputFile(audio.cover),
                disable_notification=not settings.send_notifications
            )

        self._files_to_cleanup.extend([audio.path, audio.cover] if audio.cover else [audio.path])


    def _parse_media(self, content: List[MediaContent]) -> Tuple[List[MediaContent], List[MediaContent],
                                                                     List[MediaContent], Optional[str]]:
        media_items = []
        audio_items = []
        gif_items = []
        caption = None

        for item in content:
            if item.title and not caption:
                caption = item.title

            if item.type in (MediaType.PHOTO, MediaType.VIDEO):
                media_items.append(item)
            elif item.type == MediaType.AUDIO:
                audio_items.append(item)
            elif item.type == MediaType.GIF:
                gif_items.append(item)

        return media_items, audio_items, gif_items, caption
