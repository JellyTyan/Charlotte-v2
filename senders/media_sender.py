import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple, Union

from aiogram import Bot, types
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.exceptions import TelegramEntityTooLarge

from utils import delete_files, truncate_string
from models.media import MediaContent, MediaType
from models.errors import BotError, ErrorCode
from storage.db.crud import get_user_settings, get_chat_settings, create_chat, create_user
from models.settings import UserSettingsJson, ChatSettingsJson
from utils import translate_text
import random

REACTION_EMOJIS = [
    "👍", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🎉", "🤩", "🙏", "👌", "🕊", "😍", "🐳", "❤‍🔥", "🌭", "💯", "🤣", "⚡", "🍌", "🏆", "🍾", "💋", "👻", "👨‍💻", "👀", "🎃", "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🆒", "💘", "🦄", "😘",  "😎", "👾"
]

logger = logging.getLogger(__name__)


class MediaSender:
    def __init__(self):
        self._files_to_cleanup: List[Path] = []

    async def get_settings(self, chat_id: int, user_id: int) -> Union[UserSettingsJson, ChatSettingsJson]:
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
        if not settings:
             raise BotError(code=ErrorCode.INTERNAL_ERROR, message="Failed to load settings")
        return settings

    def _get_setting(self, settings: Union[UserSettingsJson, ChatSettingsJson], key: str, service_name: Optional[str] = None):
        if key in ("notifications", "reactions", "allow_playlists", "title_language"):
            return getattr(settings.profile, key, False if key != "title_language" else "en")

        svc_key_map = {
            "send_raw": "raw", "auto_caption": "caption", "auto_translate_titles": "translate_caption",
            "send_music_covers": "send_covers", "lossless_mode": "lossless"
        }
        target_key = svc_key_map.get(key, key)

        if service_name and hasattr(settings.services, service_name):
            svc_settings = getattr(settings.services, service_name)
            if hasattr(svc_settings, target_key):
                return getattr(svc_settings, target_key)
        return False

    async def send(self, message: types.Message, content: List[MediaContent], user_id: Optional[int] = None, skip_reaction: bool = False, service: Optional[str] = None) -> None:
        if not message.bot:
            raise BotError(code=ErrorCode.INTERNAL_ERROR, message="Bot instance not available", is_logged=True)

        try:
            media_items, audio_items, gif_items, caption = self._parse_media(content)
            logger.info(f"Sending media: {len(media_items)} media, {len(audio_items)} audio, {len(gif_items)} gif")

            if user_id is None:
                user_id = message.from_user.id if hasattr(message, 'from_user') and message.from_user else message.chat.id
            settings = await self.get_settings(message.chat.id, user_id)

            if media_items:
                await self._send_media_group(message, media_items, caption, settings, service)

            for audio in audio_items:
                await message.bot.send_chat_action(message.chat.id, "upload_voice")
                await self._send_audio(message, audio, settings, service)

            for gif in gif_items:
                if not gif.path: continue
                await message.bot.send_chat_action(message.chat.id, "upload_video")
                await message.answer_animation(
                    animation=types.FSInputFile(gif.path),
                    disable_notification=not self._get_setting(settings, "notifications")
                )
                self._files_to_cleanup.append(gif.path)

            logger.info(f"Successfully sent all media to chat {message.chat.id}")

            if self._get_setting(settings, "reactions") and not skip_reaction:
                try:
                    from aiogram.types import ReactionTypeEmoji
                    emoji = random.choice(REACTION_EMOJIS)
                    await message.react([ReactionTypeEmoji(emoji=emoji)])
                except Exception as e:
                    logger.warning(f"Failed to react to message: {e}")

        finally:
            if self._files_to_cleanup:
                logger.debug(f"Cleaning up {len(self._files_to_cleanup)} files")
                await delete_files(self._files_to_cleanup)
                self._files_to_cleanup.clear()

    async def _send_media_group(self, message: types.Message, content: List[MediaContent],
                                caption: Optional[str], settings: Union[UserSettingsJson, ChatSettingsJson], service: Optional[str] = None) -> None:
        if not content:
            return

        MEDIA_GROUP_LIMIT = 10
        total_groups = (len(content) + MEDIA_GROUP_LIMIT - 1) // MEDIA_GROUP_LIMIT
        logger.debug(f"Sending {len(content)} items in {total_groups} group(s)")

        for i in range(0, len(content), MEDIA_GROUP_LIMIT):
            group_items = content[i:i + MEDIA_GROUP_LIMIT]
            media_group = MediaGroupBuilder()

            if caption and i == 0 and self._get_setting(settings, "auto_caption", service):
                if self._get_setting(settings, "auto_translate_titles", service):
                    title_lang = str(self._get_setting(settings, "title_language"))
                    caption = await translate_text(caption, title_lang)
                media_group.caption = truncate_string(caption, 1024)

            for item in group_items:
                # Check file size before sending
                file_size_mb = 0
                if item.path:
                    file_size_mb = item.path.stat().st_size / (1024 * 1024)
                elif item.content:
                    file_size_mb = len(item.content) / (1024 * 1024)

                max_size_mb = 2000 if os.getenv("TELEGRAM_LOCAL") else 50

                if file_size_mb > max_size_mb:
                    raise BotError(
                        code=ErrorCode.LARGE_FILE,
                        message=f"File {item.path.name if item.path else (item.filename or 'unknown')} is {file_size_mb:.1f}MB (limit: {max_size_mb}MB)",
                        is_logged=True
                    )

                if not item.path and not (item.content and item.filename):
                    raise BotError(code=ErrorCode.SEND_ERROR, message="Missing file source", is_logged=True)

                if self._get_setting(settings, "send_raw", service) and item.original_size and item.path:
                    media_group.add_document(media=types.FSInputFile(item.path))
                elif item.type == MediaType.PHOTO:
                    if item.content and item.filename:
                        media_group.add_photo(media=types.BufferedInputFile(item.content, item.filename), has_spoiler=item.is_blured)
                    elif item.path:
                        media_group.add_photo(media=types.FSInputFile(item.path), has_spoiler=item.is_blured)
                elif item.type == MediaType.VIDEO and item.path:
                    media_group.add_video(
                        media=types.FSInputFile(item.path),
                        supports_streaming=True,
                        width=item.width,
                        height=item.height,
                        duration=item.duration,
                        has_spoiler=item.is_blured,
                        thumbnail=types.FSInputFile(item.cover) if item.cover else None
                    )
                if item.path:
                    self._files_to_cleanup.append(item.path)

            if message.bot:
                should_send_as_doc = self._get_setting(settings, "send_raw", service) and any(item.original_size for item in group_items)
                await message.bot.send_chat_action(message.chat.id, "upload_document" if should_send_as_doc else "upload_video")

            try:
                await message.answer_media_group(
                    media=media_group.build(),
                    disable_notification=not self._get_setting(settings, "notifications")
                )
            except TelegramEntityTooLarge:
                raise BotError(
                    code=ErrorCode.LARGE_FILE,
                    message="File is too large for Telegram",
                    is_logged=True
                )

            logger.debug(f"Sent media group {i // MEDIA_GROUP_LIMIT + 1}/{total_groups}")


    async def _send_audio(self, message: types.Message, audio: MediaContent,
                         settings: Union[UserSettingsJson, ChatSettingsJson], service: Optional[str] = None) -> None:
        logger.debug(f"Sending audio: {audio.title or 'Unknown'}")

        if not audio.path:
            raise BotError(code=ErrorCode.SEND_ERROR, message="Missing audio file source", is_logged=True)

        # Check file size before sending
        file_size_mb = audio.path.stat().st_size / (1024 * 1024)
        max_size_mb = 4000 if os.getenv("TELEGRAM_BOT_API_URL") else 2000

        if file_size_mb > max_size_mb:
            raise BotError(
                code=ErrorCode.LARGE_FILE,
                message=f"Audio file is {file_size_mb:.1f}MB (limit: {max_size_mb}MB)",
                is_logged=True
            )

        if message.bot:
            await message.bot.send_chat_action(message.chat.id, "upload_voice")

        try:
            await message.answer_audio(
                audio=types.FSInputFile(audio.path),
                disable_notification=not self._get_setting(settings, "notifications"),
                thumbnail=types.FSInputFile(audio.cover) if audio.cover else None,
                title=audio.title,
                duration=audio.duration,
                performer=audio.performer
            )
        except TelegramEntityTooLarge:
            raise BotError(
                code=ErrorCode.LARGE_FILE,
                message="Audio file is too large for Telegram",
                is_logged=True
            )

        if audio.cover and self._get_setting(settings, "send_music_covers", service):
            # Send full size cover if available, otherwise regular cover
            cover_to_send = audio.full_cover if audio.full_cover else audio.cover
            logger.debug(f"Sending audio cover as document: {cover_to_send}")
            await message.answer_document(
                document=types.FSInputFile(cover_to_send),
                disable_notification=not self._get_setting(settings, "notifications")
            )

        # Cleanup files
        cleanup_files = []
        if audio.path: cleanup_files.append(audio.path)
        if audio.cover: cleanup_files.append(audio.cover)
        if audio.full_cover: cleanup_files.append(audio.full_cover)
        self._files_to_cleanup.extend(cleanup_files)


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
