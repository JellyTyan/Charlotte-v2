import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple, Union

from aiogram import types
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.exceptions import TelegramEntityTooLarge
from sqlalchemy.ext.asyncio import AsyncSession

from utils import delete_files, truncate_string
from models.media import MediaContent, MediaType
from models.errors import BotError, ErrorCode
from storage.db.crud import get_user_settings, get_chat_settings
from models.settings import UserSettingsJson, ChatSettingsJson
from utils import translate_text
import random

REACTION_EMOJIS = [
    "👍", "❤", "🔥", "🥰", "👏", "😁", "🤔", "🤯", "😱", "🎉", "🤩", "🙏", "👌", "🕊", "😍", "🐳", "❤‍🔥", "🌭", "💯", "🤣", "⚡", "🍌", "🏆", "🍾", "💋", "👻", "👨‍💻", "👀", "🎃", "😇", "😨", "🤝", "✍", "🤗", "🫡", "🎅", "🎄", "☃", "💅", "🤪", "🆒", "💘", "🦄", "😘",  "😎", "👾"
]
NEGATIVITY_EMOJIS =[
    "🤬", "😢", "🤮", "💩", "🤡", "🥱", "🥴", "🌚", "💔", "🤨", "😐", "🍓", "🖕", "😈", "😴", "😭", "🤓", "🙈", "🗿", "🙉", "💊", "🙊", "🤷‍♂", "🤷", "🤷‍♀", "😡"
]

logger = logging.getLogger(__name__)


class MediaSender:
    def __init__(self):
        self._files_to_cleanup: List[Path] = []

    async def send(self, message: types.Message, content: List[MediaContent], skip_reaction: bool = False, service: Optional[str] = None, db_session: Optional[AsyncSession] = None, cache_key: Optional[str] = None) -> None:
        if not message.bot:
            raise BotError(code=ErrorCode.INTERNAL_ERROR, message="Bot instance not available", is_logged=True)

        try:
            media_items, audio_items, gif_items, caption = self._parse_media(content)
            logger.info(f"Sending media: {len(media_items)} media, {len(audio_items)} audio, {len(gif_items)} gif")

            chat_id = message.chat.id
            if db_session:
                if chat_id < 0:
                    settings = await get_chat_settings(db_session, chat_id)
                else:
                    settings = await get_user_settings(db_session, chat_id)
            else:
                # Fallback to default settings if no session provided
                from models.settings import UserSettingsJson
                settings = UserSettingsJson()

            if media_items:
                await self._send_media_group(message, media_items, caption, settings, service)

            for audio in audio_items:
                await message.bot.send_chat_action(message.chat.id, "upload_voice")
                await self._send_audio(message, audio, settings, service)

            for gif in gif_items:
                if not gif.path and not gif.telegram_file_id and not gif.telegram_document_file_id:
                    continue

                service_settings = getattr(settings.services, service, None) if service is not None else None
                should_send_as_doc = getattr(service_settings, 'raw', False)

                if should_send_as_doc:
                    if gif.telegram_document_file_id:
                        media = gif.telegram_document_file_id
                    elif gif.path:
                        media = types.FSInputFile(gif.path)
                    else:
                        raise BotError(code=ErrorCode.SEND_ERROR, message="Missing raw file cache", is_logged=True)
                        
                    await message.bot.send_chat_action(message.chat.id, "upload_document")
                    sent_msg = await message.answer_document(
                        document=media,
                        disable_notification=not settings.profile.notifications
                    )
                    if sent_msg.document:
                        gif.telegram_document_file_id = sent_msg.document.file_id
                        if sent_msg.document.thumbnail:
                            gif.cover_file_id = sent_msg.document.thumbnail.file_id
                else:
                    if gif.telegram_file_id:
                        media = gif.telegram_file_id
                    elif gif.path:
                        media = types.FSInputFile(gif.path)
                    else:
                        raise BotError(code=ErrorCode.SEND_ERROR, message="Missing cache", is_logged=True)
                    
                    await message.bot.send_chat_action(message.chat.id, "upload_video")
                    sent_msg = await message.answer_animation(
                        animation=media,
                        disable_notification=not settings.profile.notifications
                    )
                    if sent_msg.animation:
                        gif.telegram_file_id = sent_msg.animation.file_id
                        if sent_msg.animation.thumbnail:
                            gif.cover_file_id = sent_msg.animation.thumbnail.file_id

                if gif.path: self._files_to_cleanup.append(gif.path)
                if gif.cover: self._files_to_cleanup.append(gif.cover)
                if gif.full_cover: self._files_to_cleanup.append(gif.full_cover)

            logger.info(f"Successfully sent all media to chat {message.chat.id}")

            if cache_key and db_session and service:
                await self._save_to_cache(content, cache_key, service, caption, db_session)

            if settings.profile.reactions and not skip_reaction:
                try:
                    if settings.profile.negativity:
                        emoji = random.choice(REACTION_EMOJIS + NEGATIVITY_EMOJIS)
                    else:
                        emoji = random.choice(REACTION_EMOJIS)
                    from aiogram.types import ReactionTypeEmoji
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

        total_groups = (len(content) + 10 - 1) // 10
        logger.debug(f"Sending {len(content)} items in {total_groups} group(s)")
        service_settings = getattr(settings.services, service, None) if service is not None else None
        for i in range(0, len(content), 10):
            group_items = content[i:i + 10]
            media_group = MediaGroupBuilder()

            if caption and i == 0 and getattr(service_settings, 'caption', False):
                if getattr(service_settings, 'translate_caption', False):
                    title_lang = str(settings.profile.title_language)
                    caption = await translate_text(caption, title_lang)
                media_group.caption = truncate_string(caption, 1024)

            for item in group_items:
                should_send_as_doc = getattr(service_settings, 'raw', False) and item.type in (MediaType.PHOTO, MediaType.VIDEO)
                has_valid_cache = item.telegram_document_file_id if should_send_as_doc else item.telegram_file_id

                if not has_valid_cache:
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

                if should_send_as_doc:
                    if item.telegram_document_file_id:
                        media_group.add_document(media=item.telegram_document_file_id)
                    elif item.path:
                        media_group.add_document(media=types.FSInputFile(item.path))
                    else:
                        raise BotError(code=ErrorCode.SEND_ERROR, message="Missing raw file cache", is_logged=True)
                elif item.type == MediaType.PHOTO:
                    if item.content and item.filename:
                        media_group.add_photo(media=types.BufferedInputFile(item.content, item.filename), has_spoiler=item.is_blurred)
                    elif item.telegram_file_id:
                        media_group.add_photo(media=item.telegram_file_id, has_spoiler=item.is_blurred)
                    elif item.path:
                        media_group.add_photo(media=types.FSInputFile(item.path), has_spoiler=item.is_blurred)
                elif item.type == MediaType.VIDEO:
                    if item.telegram_file_id:
                        media_group.add_video(
                            media=item.telegram_file_id,
                            supports_streaming=True,
                            width=item.width,
                            height=item.height,
                            duration=item.duration,
                            has_spoiler=item.is_blurred
                        )
                    elif item.path:
                        media_group.add_video(
                            media=types.FSInputFile(item.path),
                            supports_streaming=True,
                            width=item.width,
                            height=item.height,
                            duration=item.duration,
                            has_spoiler=item.is_blurred,
                            thumbnail=types.FSInputFile(item.cover) if item.cover else None
                        )
                if item.path:
                    self._files_to_cleanup.append(item.path)
                if item.cover:
                    self._files_to_cleanup.append(item.cover)
                if item.full_cover:
                    self._files_to_cleanup.append(item.full_cover)

            if message.bot:
                should_send_as_doc = getattr(service_settings, 'raw', False) and any(item.type in (MediaType.PHOTO, MediaType.VIDEO) for item in group_items)
                await message.bot.send_chat_action(message.chat.id, "upload_document" if should_send_as_doc else "upload_video")

            try:
                sent_messages = await message.answer_media_group(
                    media=media_group.build(),
                    disable_notification=not settings.profile.notifications
                )
                if isinstance(sent_messages, list):
                    for item, sent_msg in zip(group_items, sent_messages):
                        if sent_msg.photo:
                            item.telegram_file_id = sent_msg.photo[-1].file_id
                        elif sent_msg.video:
                            item.telegram_file_id = sent_msg.video.file_id
                            if sent_msg.video.thumbnail:
                                item.cover_file_id = sent_msg.video.thumbnail.file_id
                        elif sent_msg.document:
                            item.telegram_document_file_id = sent_msg.document.file_id
                            if sent_msg.document.thumbnail:
                                item.cover_file_id = sent_msg.document.thumbnail.file_id
            except TelegramEntityTooLarge:
                raise BotError(
                    code=ErrorCode.LARGE_FILE,
                    message="File is too large for Telegram",
                    is_logged=True
                )
            except Exception as e:
                raise BotError(code=ErrorCode.SEND_ERROR, message=f"Failed to send media group: {e}", is_logged=True, critical=True)
            finally:
                logger.debug(f"Sent media group {i // 10 + 1}/{total_groups}")


    async def _send_audio(self, message: types.Message, audio: MediaContent,
                         settings: Union[UserSettingsJson, ChatSettingsJson], service: Optional[str] = None) -> None:
        logger.debug(f"Sending audio: {audio.title or 'Unknown'}")

        if not audio.path and not audio.telegram_file_id:
            raise BotError(code=ErrorCode.SEND_ERROR, message="Missing audio file source", is_logged=True)

        # Check file size before sending if path exists
        if audio.path:
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
            if audio.telegram_file_id:
                sent_msg = await message.answer_audio(
                    audio=audio.telegram_file_id,
                    disable_notification=not settings.profile.reactions,
                    title=audio.title,
                    duration=audio.duration,
                    performer=audio.performer
                )
            else:
                sent_msg = await message.answer_audio(
                    audio=types.FSInputFile(audio.path),
                    disable_notification=not settings.profile.reactions,
                    thumbnail=types.FSInputFile(audio.cover) if audio.cover else None,
                    title=audio.title,
                    duration=audio.duration,
                    performer=audio.performer
                )
            if sent_msg.audio:
                audio.telegram_file_id = sent_msg.audio.file_id
                if sent_msg.audio.thumbnail:
                    audio.cover_file_id = sent_msg.audio.thumbnail.file_id
        except TelegramEntityTooLarge:
            raise BotError(
                code=ErrorCode.LARGE_FILE,
                message="Audio file is too large for Telegram",
                is_logged=True
            )
        service_settings = getattr(settings.services, service, None) if service is not None else None
        if getattr(service_settings, 'send_covers', False):
            if audio.full_cover_file_id:
                logger.debug(f"Sending cached full cover: {audio.full_cover_file_id}")
                await message.answer_document(
                    document=audio.full_cover_file_id,
                    disable_notification=not settings.profile.notifications
                )
            elif audio.cover:
                # Send full size cover if available, otherwise regular cover
                cover_to_send = audio.full_cover if audio.full_cover else audio.cover
                logger.debug(f"Sending audio cover as document: {cover_to_send}")
                sent_cover = await message.answer_document(
                    document=types.FSInputFile(cover_to_send),
                    disable_notification=not settings.profile.notifications
                )
                if sent_cover.document:
                    audio.full_cover_file_id = sent_cover.document.file_id

        # Cleanup files
        cleanup_files = []
        if audio.path: cleanup_files.append(audio.path)
        if audio.cover: cleanup_files.append(audio.cover)
        if audio.full_cover: cleanup_files.append(audio.full_cover)
        self._files_to_cleanup.extend(cleanup_files)


    async def _save_to_cache(self, content: List[MediaContent], cache_key: str, service: str, caption: Optional[str], db_session: AsyncSession) -> None:
        from storage.db.crud import upsert_media_cache, get_media_cache
        from models.media_cache import MediaCacheDTO, CacheMetadata, CacheItemMetadata

        if not content:
            return

        try:
            existing = await get_media_cache(db_session, cache_key)
            existing_data: CacheMetadata = existing.data if existing else CacheMetadata()
            
            if len(content) == 1:
                item = content[0]
                
                t_file_id = item.telegram_file_id
                t_doc_file_id = item.telegram_document_file_id
                t_cover_id = item.cover_file_id
                t_full_cover_id = item.full_cover_file_id
                if existing:
                    t_file_id = t_file_id or existing.telegram_file_id
                    t_doc_file_id = t_doc_file_id or existing.telegram_document_file_id
                    t_cover_id = t_cover_id or existing_data.cover
                    t_full_cover_id = t_full_cover_id or existing_data.full_cover

                dto = MediaCacheDTO(
                    cache_key=cache_key,
                    platform=service,
                    media_type=item.type.value,
                    telegram_file_id=t_file_id,
                    telegram_document_file_id=t_doc_file_id,
                    data=CacheMetadata(
                        title=item.title or caption,
                        description=caption,
                        author=item.performer,
                        duration=item.duration,
                        cover=t_cover_id,
                        full_cover=t_full_cover_id,
                        width=item.width,
                        height=item.height,
                        is_blurred=item.is_blurred
                    )
                )
            else:
                items = []
                existing_items = existing_data.items if existing and existing.media_type == "gallery" else []
                for i, item in enumerate(content):
                    t_file_id = item.telegram_file_id
                    t_doc_file_id = item.telegram_document_file_id
                    t_cover_id = item.cover_file_id
                    t_is_blurred = item.is_blurred
                    if i < len(existing_items):
                        t_file_id = t_file_id or existing_items[i].file_id
                        t_doc_file_id = t_doc_file_id or existing_items[i].raw_file_id
                        t_cover_id = t_cover_id or existing_items[i].cover
                        t_is_blurred = t_is_blurred if t_is_blurred is not None else existing_items[i].is_blurred
                    
                    items.append(CacheItemMetadata(
                        file_id=t_file_id,
                        raw_file_id=t_doc_file_id,
                        cover=t_cover_id,
                        media_type=item.type.value,
                        duration=item.duration,
                        width=item.width,
                        height=item.height,
                        is_blurred=t_is_blurred
                    ))
                
                dto = MediaCacheDTO(
                    cache_key=cache_key,
                    platform=service,
                    media_type="gallery",
                    data=CacheMetadata(
                        title=caption,
                        description=caption,
                        items=items
                    )
                )

            await upsert_media_cache(db_session, dto)
            logger.info(f"💾 Saved media to cache: {cache_key}")
        except Exception as e:
            logger.error(f"Failed to save media to cache: {e}")

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
