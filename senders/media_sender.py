import asyncio
import logging
import os
import random
import time
from functools import wraps
from pathlib import Path
from typing import List, Optional, Tuple, Union

from aiogram import types, Bot
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.exceptions import TelegramEntityTooLarge, TelegramRetryAfter
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.utils.chat_action import ChatActionSender

from utils import delete_files, truncate_string, translate_text
from models.media import MediaContent, MediaType
from models.errors import BotError, ErrorCode
from storage.db.crud import (
    get_user_settings,
    get_chat_settings,
    upsert_media_cache,
    get_media_cache,
)
from models.settings import UserSettingsJson, ChatSettingsJson
from models.media_cache import MediaCacheDTO, CacheMetadata, CacheItemMetadata
from models.service_list import Services
from utils.statistics_helper import log_download_event
from core.config import Config

logger = logging.getLogger(__name__)

REACTION_EMOJIS = [
    "👍",
    "❤",
    "🔥",
    "🥰",
    "👏",
    "😁",
    "🤔",
    "🤯",
    "😱",
    "🎉",
    "🤩",
    "🙏",
    "👌",
    "🕊",
    "😍",
    "🐳",
    "❤‍🔥",
    "🌭",
    "💯",
    "🤣",
    "⚡",
    "🍌",
    "🏆",
    "🍾",
    "💋",
    "👻",
    "👨‍💻",
    "👀",
    "🎃",
    "😇",
    "😨",
    "🤝",
    "✍",
    "🤗",
    "🫡",
    "🎅",
    "🎄",
    "☃",
    "💅",
    "🤪",
    "🆒",
    "💘",
    "🦄",
    "😘",
    "😎",
    "👾",
]
NEGATIVITY_EMOJIS = [
    "🤬",
    "😢",
    "🤮",
    "💩",
    "🤡",
    "🥱",
    "🥴",
    "🌚",
    "💔",
    "🤨",
    "😐",
    "🍓",
    "🖕",
    "😈",
    "😴",
    "😭",
    "🤓",
    "🙈",
    "🗿",
    "🙉",
    "💊",
    "🙊",
    "🤷‍♂",
    "🤷",
    "🤷‍♀",
    "😡",
]


def with_retry(max_retries: int = 5):
    """Декоратор: Глобальный Rate Limit (Redis) + Перехват FloodWait от Telegram"""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Локальный импорт Redis, чтобы избежать циклических зависимостей при старте
            from storage.cache.redis_client import redis_client

            for attempt in range(max_retries):
                try:
                    if redis_client:
                        current_time = int(time.time())
                        key = f"global_send_count:{current_time}"
                        count = await redis_client.incr(key)
                        if count == 1:
                            await redis_client.expire(key, 5)

                        if count >= 25:
                            await asyncio.sleep(1)
                            continue

                    return await func(*args, **kwargs)

                except TelegramRetryAfter as e:
                    logger.warning(
                        f"Rate limited by Telegram. Sleeping for {e.retry_after}s..."
                    )
                    await asyncio.sleep(e.retry_after)

            raise BotError(
                code=ErrorCode.SEND_ERROR,
                message="Max retries exceeded for API call",
                is_logged=True,
            )

        return wrapper

    return decorator


class MediaSender:
    _dump_lock = asyncio.Lock()

    def __init__(self):
        self._files_to_cleanup: List[Path] = []

    # ==========================================
    # ХЕЛПЕРЫ (DRY)
    # ==========================================

    def _get_input_media(
        self, item: MediaContent, as_document: bool = False
    ) -> Union[str, types.InputFile]:
        """Умный селектор источника файла: Кэш -> Диск -> Память"""
        cache_id = (
            item.telegram_document_file_id if as_document else item.telegram_file_id
        )
        if cache_id:
            return cache_id

        if item.path:
            return types.FSInputFile(item.path)

        if item.content and item.filename:
            return types.BufferedInputFile(item.content, item.filename)

        raise BotError(
            code=ErrorCode.SEND_ERROR, message="Missing file source", is_logged=True
        )

    def _get_thumb(self, cover_path: Optional[Path]) -> Optional[types.FSInputFile]:
        """Возвращает обложку, если она есть"""
        return types.FSInputFile(cover_path) if cover_path else None

    def _check_file_size(self, item: MediaContent, is_audio: bool = False) -> None:
        """Проверка размера файла на соответствие лимитам Telegram API"""
        if not item.path and not item.content:
            return

        size_mb = (item.path.stat().st_size if item.path else len(item.content)) / (
            1024 * 1024
        )

        # Лимиты зависят от того, запущен ли Local Bot API
        is_local = bool(
            os.getenv("TELEGRAM_LOCAL") or os.getenv("TELEGRAM_BOT_API_URL")
        )
        max_size_mb = (
            (4000 if is_local else 2000) if is_audio else (2000 if is_local else 50)
        )

        if size_mb > max_size_mb:
            filename = item.path.name if item.path else (item.filename or "unknown")
            raise BotError(
                code=ErrorCode.LARGE_FILE,
                message=f"File {filename} is {size_mb:.1f}MB (limit: {max_size_mb}MB)",
                is_logged=True,
            )

    @with_retry()
    async def _safe_send(self, target_obj, method_name: str, **kwargs):
        """Универсальный и безопасный вызов любого метода aiogram"""
        method = getattr(target_obj, method_name)
        return await method(**kwargs)

    # ==========================================
    # ДАМП В КАНАЛ (КЭШИРОВАНИЕ)
    # ==========================================

    async def _dump_media_to_cache_channel(
        self, bot: Bot, content: List[MediaContent]
    ) -> bool:
        dump_channel_id = Config.instance().DUMP_CHANNEL_ID
        if not dump_channel_id:
            return False

        async with self._dump_lock:
            for item in content:
                if not item.path and not item.content:
                    continue

                try:
                    media_standard = self._get_input_media(item, as_document=False)
                    media_document = self._get_input_media(item, as_document=True)
                    thumb = self._get_thumb(item.cover)

                    # 1. Дамп стандартного формата (Photo/Video/Audio/Animation)
                    if not item.telegram_file_id:
                        if item.type == MediaType.PHOTO:
                            msg = await self._safe_send(
                                bot,
                                "send_photo",
                                chat_id=dump_channel_id,
                                photo=media_standard,
                                disable_notification=True,
                            )
                            if msg.photo:
                                item.telegram_file_id = msg.photo[-1].file_id
                            elif msg.document:
                                item.telegram_file_id = msg.document.file_id

                        elif item.type == MediaType.VIDEO:
                            msg = await self._safe_send(
                                bot,
                                "send_video",
                                chat_id=dump_channel_id,
                                video=media_standard,
                                thumbnail=thumb,
                                width=item.width,
                                height=item.height,
                                duration=item.duration,
                                disable_notification=True,
                                supports_streaming=True,
                            )
                            if msg.video:
                                item.telegram_file_id = msg.video.file_id
                                if msg.video.thumbnail:
                                    item.cover_file_id = msg.video.thumbnail.file_id
                            elif msg.document:
                                item.telegram_file_id = msg.document.file_id

                        elif item.type == MediaType.AUDIO:
                            msg = await self._safe_send(
                                bot,
                                "send_audio",
                                chat_id=dump_channel_id,
                                audio=media_standard,
                                thumbnail=thumb,
                                title=item.title,
                                performer=item.performer,
                                duration=item.duration,
                                disable_notification=True,
                            )
                            if msg.audio:
                                item.telegram_file_id = msg.audio.file_id
                                if msg.audio.thumbnail:
                                    item.cover_file_id = msg.audio.thumbnail.file_id
                            elif msg.document:
                                item.telegram_file_id = msg.document.file_id

                        elif item.type == MediaType.GIF:
                            msg = await self._safe_send(
                                bot,
                                "send_animation",
                                chat_id=dump_channel_id,
                                animation=media_standard,
                                thumbnail=thumb,
                                width=item.width,
                                height=item.height,
                                duration=item.duration,
                                disable_notification=True,
                            )
                            if msg.animation:
                                item.telegram_file_id = msg.animation.file_id
                                if msg.animation.thumbnail:
                                    item.cover_file_id = msg.animation.thumbnail.file_id
                            elif msg.document:
                                item.telegram_file_id = msg.document.file_id

                        await asyncio.sleep(0.5)  # Пауза для стабильности дампа

                    # 2. Дамп в виде документа (Raw файл)
                    if (
                        not item.telegram_document_file_id
                        and item.type != MediaType.AUDIO
                    ):
                        msg = await self._safe_send(
                            bot,
                            "send_document",
                            chat_id=dump_channel_id,
                            document=media_document,
                            thumbnail=thumb,
                            disable_notification=True,
                        )
                        if msg.document:
                            item.telegram_document_file_id = msg.document.file_id
                            if msg.document.thumbnail and not getattr(
                                item, "cover_file_id", None
                            ):
                                item.cover_file_id = msg.document.thumbnail.file_id
                        elif msg.photo:
                            item.telegram_document_file_id = msg.photo[-1].file_id
                        await asyncio.sleep(0.5)

                    # 3. Дамп Full Cover для Аудио
                    if item.type == MediaType.AUDIO and not item.full_cover_file_id:
                        cover_to_dump = item.full_cover or item.cover
                        if cover_to_dump:
                            msg = await self._safe_send(
                                bot,
                                "send_document",
                                chat_id=dump_channel_id,
                                document=types.FSInputFile(cover_to_dump),
                                disable_notification=True,
                            )
                            item.full_cover_file_id = msg.document.file_id
                            await asyncio.sleep(0.5)

                except Exception as e:
                    logger.error(f"Failed to dump media to cache channel: {e}")
                    return False

        return True

    # ==========================================
    # ГЛАВНЫЙ МЕТОД ОТПРАВКИ
    # ==========================================

    async def send(
        self,
        message: types.Message,
        content: List[MediaContent],
        skip_reaction: bool = False,
        service: Optional[str] = None,
        db_session: Optional[AsyncSession] = None,
        cache_key: Optional[str] = None,
    ) -> None:

        if not message.bot:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Bot instance not available",
                is_logged=True,
            )

        try:
            # 1. Сразу собираем пути для гарантированной очистки (Броня от утечек памяти)
            for item in content:
                if item.path:
                    self._files_to_cleanup.append(item.path)
                if item.cover:
                    self._files_to_cleanup.append(item.cover)
                if item.full_cover:
                    self._files_to_cleanup.append(item.full_cover)

            # 2. Парсим медиа
            media_items, audio_items, gif_items, caption = self._parse_media(content)

            # 3. Дамп в кэш-канал
            dump_success = await self._dump_media_to_cache_channel(message.bot, content)

            # 4. Сохранение в БД (до отправки, если дамп успешен)
            if dump_success and cache_key and db_session and service:
                await self._save_to_cache(
                    content, cache_key, service, caption, db_session
                )

            # 5. Получаем настройки пользователя/чата
            settings = UserSettingsJson()  # Fallback
            if db_session:
                settings = (
                    await get_chat_settings(db_session, message.chat.id)
                    if message.chat.id < 0
                    else await get_user_settings(db_session, message.chat.id)
                )

            is_premium = False
            show_ad = True
            if db_session and message.from_user:
                from storage.db.crud import get_user
                user = await get_user(db_session, message.from_user.id)
                is_premium = user.is_premium if user else False
                
                user_settings = await get_user_settings(db_session, message.from_user.id)
                if user_settings:
                    if is_premium:
                        show_ad = user_settings.profile.bot_sign
                    else:
                        show_ad = True

            logger.info(
                f"Sending to {message.chat.id}: {len(media_items)} media, {len(audio_items)} audio, {len(gif_items)} gif"
            )

            # 6. Отправка пользователю
            if media_items:
                await self._send_media_group(
                    message, media_items, caption, settings, service, show_ad
                )

            for audio in audio_items:
                async with ChatActionSender.upload_voice(bot=message.bot, chat_id=message.chat.id):
                    await self._send_audio(message, audio, settings, service, caption, show_ad)

            for gif in gif_items:
                await self._send_gif(message, gif, settings, service, caption, show_ad)

            # 7. Реакции
            if settings.profile.reactions and not skip_reaction:
                emoji_pool = (
                    REACTION_EMOJIS + NEGATIVITY_EMOJIS
                    if settings.profile.negativity
                    else REACTION_EMOJIS
                )
                try:
                    from aiogram.types import ReactionTypeEmoji

                    await message.react(
                        [ReactionTypeEmoji(emoji=random.choice(emoji_pool))]
                    )
                except Exception as e:
                    logger.warning(f"Failed to react: {e}")

            # 8. Если дамп упал, но юзеру доставили (сгенерировался file_id), сохраняем кэш постфактум
            if not dump_success and cache_key and db_session and service:
                await self._save_to_cache(
                    content, cache_key, service, caption, db_session
                )

            # 9. Логируем успешную отправку в статистику
            if db_session and service:
                service_enum = self._get_service_enum(service)
                if service_enum:
                    user_id = message.from_user.id if message.from_user else message.chat.id
                    await log_download_event(db_session, user_id, service_enum, "success")

            logger.info(f"Successfully sent all media to chat {message.chat.id}")

        finally:
            # Срабатывает ВСЕГДА, даже если бот упал с ошибкой на этапе отправки
            if self._files_to_cleanup:
                logger.debug(f"Cleaning up {len(self._files_to_cleanup)} files")
                await delete_files(self._files_to_cleanup)
                self._files_to_cleanup.clear()

    # ==========================================
    # ЛОГИКА ОТПРАВКИ КОНКРЕТНЫХ ФОРМАТОВ
    # ==========================================

    async def _send_media_group(
        self,
        message: types.Message,
        content: List[MediaContent],
        caption: Optional[str],
        settings: Union[UserSettingsJson, ChatSettingsJson],
        service: Optional[str] = None,
        show_ad: bool = True,
    ) -> None:
        if not content:
            return

        service_settings = (
            getattr(settings.services, service, None) if service else None
        )
        send_as_raw = getattr(service_settings, "raw", False)

        for i in range(0, len(content), 10):
            group_items = content[i : i + 10]
            media_group = MediaGroupBuilder()

            # Обработка подписи и перевода (только для первого элемента)
            if i == 0:
                final_caption = ""
                if caption and getattr(service_settings, "caption", False):
                    if getattr(service_settings, "translate_caption", False):
                        caption = await translate_text(
                            caption, str(settings.profile.title_language)
                        )
                    final_caption = truncate_string(caption, 1000)
                
                if show_ad:
                    ad_text = "\n\n<a href='https://t.me/CharlotteFox_Bot'>Charlotte 🧡</a>"
                    if final_caption:
                        final_caption += ad_text
                    else:
                        final_caption = ad_text
                
                if final_caption:
                    media_group.caption = final_caption

            # Сборка альбома
            for item in group_items:
                self._check_file_size(item, is_audio=False)
                media_input = self._get_input_media(item, as_document=send_as_raw)

                if send_as_raw:
                    media_group.add_document(media=media_input)
                elif item.type == MediaType.PHOTO:
                    media_group.add_photo(
                        media=media_input, has_spoiler=item.is_blurred
                    )
                elif item.type == MediaType.VIDEO:
                    media_group.add_video(
                        media=media_input,
                        supports_streaming=True,
                        width=item.width,
                        height=item.height,
                        duration=item.duration,
                        has_spoiler=item.is_blurred,
                        thumbnail=self._get_thumb(item.cover),
                    )

            # Отправка альбома
            action = "upload_document" if send_as_raw else "upload_video"

            try:
                async with ChatActionSender(bot=message.bot, chat_id=message.chat.id, action=action):
                    sent_messages = await self._safe_send(
                        message,
                        "answer_media_group",
                        media=media_group.build(),
                        disable_notification=not settings.profile.notifications,
                    )
                # Кэшируем новые file_id, если их не было
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
                    is_logged=True,
                )
            except Exception as e:
                raise BotError(
                    code=ErrorCode.SEND_ERROR,
                    message=f"Failed to send media group: {e}",
                    is_logged=True,
                    critical=True,
                )

    async def _send_audio(
        self,
        message: types.Message,
        audio: MediaContent,
        settings: Union[UserSettingsJson, ChatSettingsJson],
        service: Optional[str] = None,
        caption: Optional[str] = None,
        show_ad: bool = True,
    ) -> None:
        self._check_file_size(audio, is_audio=True)
        media_input = self._get_input_media(audio, as_document=False)

        service_settings = getattr(settings.services, service, None) if service else None
        final_caption = ""
        if caption and getattr(service_settings, "caption", False):
            if getattr(service_settings, "translate_caption", False):
                caption = await translate_text(
                    caption, str(settings.profile.title_language)
                )
            final_caption = truncate_string(caption, 1000)

        if show_ad:
            ad_text = "\n\n<a href='https://t.me/CharlotteFox_Bot'>Charlotte 🧡</a>"
            if final_caption:
                final_caption += ad_text
            else:
                final_caption = ad_text
                
        if not final_caption:
            final_caption = None

        try:
            sent_msg = await self._safe_send(
                message,
                "answer_audio",
                audio=media_input,
                disable_notification=not settings.profile.reactions,
                thumbnail=self._get_thumb(audio.cover)
                if not audio.telegram_file_id
                else None,
                title=audio.title,
                duration=audio.duration,
                performer=audio.performer,
                caption=final_caption
            )
            if sent_msg.audio:
                audio.telegram_file_id = sent_msg.audio.file_id
                if sent_msg.audio.thumbnail:
                    audio.cover_file_id = sent_msg.audio.thumbnail.file_id
        except TelegramEntityTooLarge:
            raise BotError(
                code=ErrorCode.LARGE_FILE,
                message="Audio file is too large for Telegram",
                is_logged=True,
            )

        # Отправка обложки отдельным документом, если включено в настройках
        service_settings = (
            getattr(settings.services, service, None) if service else None
        )
        if getattr(service_settings, "send_covers", False):
            cover_input = audio.full_cover_file_id or self._get_thumb(
                audio.full_cover or audio.cover
            )
            if cover_input:
                sent_cover = await self._safe_send(
                    message,
                    "answer_document",
                    document=cover_input,
                    disable_notification=not settings.profile.notifications,
                )
                if sent_cover.document:
                    audio.full_cover_file_id = sent_cover.document.file_id

    async def _send_gif(
        self,
        message: types.Message,
        gif: MediaContent,
        settings: Union[UserSettingsJson, ChatSettingsJson],
        service: Optional[str] = None,
        caption: Optional[str] = None,
        show_ad: bool = True,
    ) -> None:
        service_settings = (
            getattr(settings.services, service, None) if service else None
        )
        send_as_raw = getattr(service_settings, "raw", False)

        self._check_file_size(gif, is_audio=False)
        media_input = self._get_input_media(gif, as_document=send_as_raw)

        action = "upload_document" if send_as_raw else "upload_video"
        method = "answer_document" if send_as_raw else "answer_animation"

        final_caption = ""
        if caption and getattr(service_settings, "caption", False):
            if getattr(service_settings, "translate_caption", False):
                caption = await translate_text(
                    caption, str(settings.profile.title_language)
                )
            final_caption = truncate_string(caption, 1000)

        if show_ad:
            ad_text = "\n\n<a href='https://t.me/CharlotteFox_Bot'>Charlotte 🧡</a>"
            if final_caption:
                final_caption += ad_text
            else:
                final_caption = ad_text
                
        if not final_caption:
            final_caption = None

        kwargs = {
            "disable_notification": not settings.profile.notifications,
            "caption": final_caption
        }
        if send_as_raw:
            kwargs["document"] = media_input
            kwargs["thumbnail"] = self._get_thumb(gif.cover) if not gif.telegram_document_file_id else None
        else:
            kwargs["animation"] = media_input
            kwargs["thumbnail"] = self._get_thumb(gif.cover) if not gif.telegram_file_id else None
            kwargs["width"] = gif.width
            kwargs["height"] = gif.height
            kwargs["duration"] = gif.duration

        async with ChatActionSender(bot=message.bot, chat_id=message.chat.id, action=action):
            sent_msg = await self._safe_send(
                message,
                method,
                **kwargs
            )

        # Обновляем кэш
        if send_as_raw and sent_msg.document:
            gif.telegram_document_file_id = sent_msg.document.file_id
            if sent_msg.document.thumbnail:
                gif.cover_file_id = sent_msg.document.thumbnail.file_id
        elif not send_as_raw and sent_msg.animation:
            gif.telegram_file_id = sent_msg.animation.file_id
            if sent_msg.animation.thumbnail:
                gif.cover_file_id = sent_msg.animation.thumbnail.file_id

    # ==========================================
    # РАБОТА С БД (СОХРАНЕНИЕ КЭША)
    # ==========================================

    async def _save_to_cache(
        self,
        content: List[MediaContent],
        cache_key: str,
        service: str,
        caption: Optional[str],
        db_session: AsyncSession,
    ) -> None:
        if not content:
            return

        try:
            existing = await get_media_cache(db_session, cache_key)
            existing_data: CacheMetadata = (
                existing.data if existing else CacheMetadata()
            )

            if len(content) == 1:
                item = content[0]
                dto = MediaCacheDTO(
                    cache_key=cache_key,
                    platform=service,
                    media_type=item.type.value,
                    telegram_file_id=item.telegram_file_id
                    or (existing.telegram_file_id if existing else None),
                    telegram_document_file_id=item.telegram_document_file_id
                    or (existing.telegram_document_file_id if existing else None),
                    data=CacheMetadata(
                        title=item.title or caption,
                        description=caption,
                        author=item.performer,
                        duration=item.duration,
                        cover=item.cover_file_id or existing_data.cover,
                        full_cover=item.full_cover_file_id or existing_data.full_cover,
                        width=item.width,
                        height=item.height,
                        is_blurred=item.is_blurred,
                    ),
                )
            else:
                items = []
                existing_items = (
                    existing_data.items
                    if existing and existing.media_type == "gallery"
                    else []
                )
                for i, item in enumerate(content):
                    e_item = existing_items[i] if i < len(existing_items) else None
                    items.append(
                        CacheItemMetadata(
                            file_id=item.telegram_file_id
                            or (e_item.file_id if e_item else None),
                            raw_file_id=item.telegram_document_file_id
                            or (e_item.raw_file_id if e_item else None),
                            cover=item.cover_file_id
                            or (e_item.cover if e_item else None),
                            media_type=item.type.value,
                            duration=item.duration,
                            width=item.width,
                            height=item.height,
                            is_blurred=item.is_blurred
                            if item.is_blurred is not None
                            else getattr(e_item, "is_blurred", None),
                        )
                    )
                dto = MediaCacheDTO(
                    cache_key=cache_key,
                    platform=service,
                    media_type="gallery",
                    data=CacheMetadata(title=caption, description=caption, items=items),
                )

            await upsert_media_cache(db_session, dto)
            logger.info(f"💾 Saved media to cache: {cache_key}")
        except Exception as e:
            logger.error(f"Failed to save media to cache: {e}")

    def _parse_media(
        self, content: List[MediaContent]
    ) -> Tuple[
        List[MediaContent], List[MediaContent], List[MediaContent], Optional[str]
    ]:
        """Разбивает массив медиа на категории"""
        media, audio, gif, caption = [], [], [], None
        for item in content:
            if item.title and not caption:
                caption = item.title

            if item.type in (MediaType.PHOTO, MediaType.VIDEO):
                media.append(item)
            elif item.type == MediaType.AUDIO:
                audio.append(item)
            elif item.type == MediaType.GIF:
                gif.append(item)

        return media, audio, gif, caption

    def _get_service_enum(self, service_name: str) -> Optional[Services]:
        """Маппинг строкового названия сервиса в Services Enum"""
        mapping = {
            "youtube": Services.YOUTUBE,
            "ytmusic": Services.YTMUSIC,
            "reddit": Services.REDDIT,
            "tiktok": Services.TIKTOK,
            "instagram": Services.INSTAGRAM,
            "pinterest": Services.PINTEREST,
            "twitter": Services.TWITTER,
            "spotify": Services.SPOTIFY,
            "soundcloud": Services.SOUNDCLOUD,
            "pixiv": Services.PIXIV,
            "deezer": Services.DEEZER,
            "apple_music": Services.APPLE_MUSIC,
            "applemusic": Services.APPLE_MUSIC,
            "bluesky": Services.BLUESKY,
            "twitch": Services.TWITCH,
            "nicovideo": Services.NICOVIDEO,
        }
        return mapping.get(service_name.lower())

