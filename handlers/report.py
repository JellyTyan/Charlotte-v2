import re
import logging
from typing import Optional
from aiogram import Router, types, Bot
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from fluentogram import TranslatorRunner
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import Config
from storage.db.crud import get_media_cache_entry_by_file_id, get_media_cache
from utils import escape_html
from utils.message_context import get_message_context, store_purge_key

logger = logging.getLogger(__name__)

router = Router(name="report")


@router.message(Command("report"))
async def report_command_handler(
    message: types.Message,
    bot: Bot,
    config: Config,
    db_session: AsyncSession,
    i18n: TranslatorRunner = None,
):
    # 1. Проверяем, что это Reply
    if not message.reply_to_message:
        reply_text = (
            i18n.get("report-reply-required")
            if i18n
            else "Пожалуйста, отправь команду <code>/report</code> в ответ (Reply) на сообщение бота с проблемным контентом или ошибкой."
        )
        await message.reply(reply_text, parse_mode=ParseMode.HTML)
        return

    reply = message.reply_to_message
    bot_info = await bot.get_me()

    # 2. Проверяем, что ответили именно на сообщение бота
    if not reply.from_user or reply.from_user.id != bot_info.id:
        reply_text = (
            i18n.get("report-not-bot-message")
            if i18n
            else "Эта команда работает только в ответ на сообщение от меня 🐾"
        )
        await message.reply(reply_text, parse_mode=ParseMode.HTML)
        return

    # 3. Извлекаем комментарий пользователя
    args = message.text.split(maxsplit=1) if message.text else []
    user_comment = args[1].strip() if len(args) > 1 else None

    # 4. Проверяем контекст в Redis
    ctx = await get_message_context(reply.chat.id, reply.message_id) or {}

    # 5. Извлекаем данные медиафайла (если есть)
    file_id: Optional[str] = None
    media_type: Optional[str] = None
    file_title: Optional[str] = None
    file_performer: Optional[str] = None
    file_duration: Optional[int] = None

    if reply.audio:
        file_id = reply.audio.file_id
        media_type = "Audio"
        file_title = reply.audio.title
        file_performer = reply.audio.performer
        file_duration = reply.audio.duration
    elif reply.video:
        file_id = reply.video.file_id
        media_type = "Video"
        file_duration = reply.video.duration
    elif reply.document:
        file_id = reply.document.file_id
        media_type = "Document"
        file_title = reply.document.file_name
    elif reply.photo:
        file_id = reply.photo[-1].file_id
        media_type = "Photo"
    elif reply.animation:
        file_id = reply.animation.file_id
        media_type = "Animation"
        file_duration = reply.animation.duration

    # 6. Поиск в БД mediacache
    cache_key = ctx.get("cache_key")
    service = ctx.get("service")
    db_media_id = None

    if file_id:
        db_res = await get_media_cache_entry_by_file_id(db_session, file_id)
        if db_res:
            db_media_id, cache_dto = db_res
            if not cache_key:
                cache_key = cache_dto.cache_key
            if not service:
                service = cache_dto.platform
            if not file_title and cache_dto.data.title:
                file_title = cache_dto.data.title
            if not file_performer and cache_dto.data.author:
                file_performer = cache_dto.data.author
    elif cache_key:
        cached_dto = await get_media_cache(db_session, cache_key)
        if cached_dto:
            if not service:
                service = cached_dto.platform

    # 7. Извлекаем URL
    url = ctx.get("url") or ctx.get("original_url")
    if not url and reply.reply_to_message:
        orig_text = reply.reply_to_message.text or reply.reply_to_message.caption or ""
        url_match = re.search(r"https?://[^\s]+", orig_text)
        if url_match:
            url = url_match.group(0)

    if not url and user_comment:
        url_match = re.search(r"https?://[^\s]+", user_comment)
        if url_match:
            url = url_match.group(0)

    # 8. Данные об ошибке (если есть)
    error_code = ctx.get("error_code")
    error_message = ctx.get("error_message")
    reply_snippet = reply.text or reply.caption

    # 9. Формируем карточку для админа
    reporter = message.from_user
    user_mention = f"@{reporter.username}" if reporter.username else reporter.full_name

    lines = [
        "🚨 <b>Репорт по контенту</b>\n",
        f"👤 <b>Пользователь:</b> {escape_html(user_mention)} (<code>{reporter.id}</code>)",
        f"💬 <b>Комментарий:</b> <i>{escape_html(user_comment) if user_comment else 'Не указан'}</i>\n",
        "📦 <b>Информация о медиа:</b>",
    ]

    if service:
        lines.append(f"• <b>Сервис:</b> <code>{escape_html(str(service))}</code>")
    if url:
        lines.append(f"• <b>URL:</b> <code>{escape_html(url)}</code>")
    if cache_key:
        lines.append(f"• <b>Cache Key:</b> <code>{escape_html(cache_key)}</code>")
    if db_media_id:
        lines.append(f"• <b>MediaCache ID:</b> <code>#{db_media_id}</code>")
    if file_title or file_performer:
        full_name = (
            f"{file_performer} — {file_title}"
            if file_performer and file_title
            else (file_title or file_performer)
        )
        lines.append(f"• <b>Название:</b> {escape_html(full_name)}")
    if media_type:
        lines.append(f"• <b>Тип:</b> {media_type}")
    if file_duration:
        lines.append(f"• <b>Длительность:</b> {file_duration} сек")
    if error_code or error_message:
        lines.append(
            f"• <b>Ошибка:</b> <code>{escape_html(str(error_code or ''))}</code> {escape_html(str(error_message or ''))}"
        )
    elif reply_snippet and isinstance(reply_snippet, str) and not file_id:
        lines.append(f"• <b>Текст сообщения:</b> <i>{escape_html(reply_snippet[:300])}</i>")
    if file_id and isinstance(file_id, str):
        lines.append(f"• <b>File ID:</b> <code>{file_id[:32]}...</code>")

    if message.chat.type != "private":
        chat_title = message.chat.title or str(message.chat.id)
        lines.append(f"\n📍 <b>Чат:</b> {escape_html(chat_title)} (<code>{message.chat.id}</code>)")

    admin_text = "\n".join(lines)

    # 10. Кнопки для админа
    buttons = []
    if cache_key:
        purge_token = await store_purge_key(cache_key)
        buttons.append([
            InlineKeyboardButton(
                text="🗑 Очистить кэш",
                callback_data=f"purge_cache:{purge_token}",
            )
        ])

    user_action_row = []
    if reporter.username:
        user_action_row.append(
            InlineKeyboardButton(
                text="✉️ Написать пользователю",
                url=f"https://t.me/{reporter.username}",
            )
        )
    if user_action_row:
        buttons.append(user_action_row)

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons) if buttons else None

    # 11. Отправляем админу
    if config.ADMIN_ID:
        try:
            await bot.send_message(
                config.ADMIN_ID,
                admin_text,
                reply_markup=keyboard,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception as e:
            logger.error(f"Failed to forward report to admin {config.ADMIN_ID}: {e}")

    # 12. Отвечаем пользователю
    success_text = (
        i18n.get("report-success")
        if i18n
        else "Спасибо за репорт! 🧡 Я передала информацию разработчику, скоро разберёмся."
    )
    await message.reply(success_text, parse_mode=ParseMode.HTML)
