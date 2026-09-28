import hashlib
import logging
from aiogram import Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultCachedVideo,
    InlineQueryResultCachedPhoto,
    InlineQueryResultCachedAudio,
    InlineQueryResultCachedGif,
    ChosenInlineResult,
)
from aiogram.exceptions import TelegramBadRequest
from storage.db.crud import (
    search_user_saves,
    search_public_saves,
    increment_save_uses,
    search_cached_music,
)
from storage.cache.redis_client import cache_get
from utils.recent_downloads import get_recent_downloads
from sqlalchemy.ext.asyncio import AsyncSession
from fluentogram import TranslatorRunner

inline_router = Router(name="inline_handler")
logger = logging.getLogger(__name__)

INLINE_SEARCH_LIMIT = 25
VISUAL_MEDIA_TYPES = ("photo", "video", "gif")

RECENT_TAGS = ("#recent", "#recents", "#недавнее", "#история", "#last")
MUSIC_TAGS = ("#music", "#музыка", "🎵", "#audio")
SAVED_TAGS = ("#saved", "#saves", "#сейв", "#сейвы")
PASTE_TRIGGERS = ("paste", "#paste", "вставить", "буфер")


def _match_hashtag(query: str, tags: tuple[str, ...]) -> tuple[bool, str]:
    """Проверяет, начинается ли запрос с одного из хэштегов."""
    q_lower = query.lower()
    for tag in tags:
        if q_lower == tag:
            return True, ""
        if q_lower.startswith(tag + " "):
            sub = query[len(tag):].strip()
            return True, sub
    return False, ""


def _build_save_inline_result(save, is_own: bool = True):
    """Преобразует запись из БД в нативный результат инлайна без лишних подписей."""
    icon = "💾" if is_own else "🌐"
    res_id = f"save_{save.id}"
    title = f"{icon} {save.label}"
    if save.media_type == "video":
        return InlineQueryResultCachedVideo(id=res_id, title=title, video_file_id=save.telegram_file_id, caption=None)
    elif save.media_type == "photo":
        return InlineQueryResultCachedPhoto(id=res_id, photo_file_id=save.telegram_file_id, title=title, caption=None)
    elif save.media_type == "audio":
        return InlineQueryResultCachedAudio(id=res_id, audio_file_id=save.telegram_file_id, caption=None)
    elif save.media_type == "gif":
        return InlineQueryResultCachedGif(id=res_id, title=title, gif_file_id=save.telegram_file_id, caption=None)
    return None


def _build_recent_inline_result(item: dict, idx: int):
    """Преобразует недавнее скачанное медиа из Redis в результат инлайна."""
    file_id = item.get("file_id")
    m_type = item.get("media_type")
    if not file_id or m_type not in VISUAL_MEDIA_TYPES:
        return None

    raw_title = item.get("title") or "Недавнее"
    title = f"🕒 {raw_title}"
    res_id = f"recent_{idx}_{hashlib.md5(file_id.encode()).hexdigest()[:8]}"

    if m_type == "video":
        return InlineQueryResultCachedVideo(id=res_id, title=title, video_file_id=file_id, caption=None)
    elif m_type == "photo":
        return InlineQueryResultCachedPhoto(id=res_id, photo_file_id=file_id, title=title, caption=None)
    elif m_type == "gif":
        return InlineQueryResultCachedGif(id=res_id, title=title, gif_file_id=file_id, caption=None)
    return None


async def _safe_answer_inline(
    inline_query: InlineQuery,
    results: list,
    cache_time: int = 3,
    is_personal: bool = True,
):
    """Безопасная отправка ответа инлайна с перехватом TelegramBadRequest (DOCUMENT_INVALID и др.)"""
    try:
        return await inline_query.answer(results, cache_time=cache_time, is_personal=is_personal)
    except TelegramBadRequest as e:
        logger.warning(f"Failed to answer inline query with {len(results)} items ({e}). Attempting resilient fallback.")
        if len(results) > 1:
            for chunk_size in (15, 10, 5, 2, 1):
                for i in range(0, len(results), chunk_size):
                    candidate = results[i : i + chunk_size]
                    try:
                        return await inline_query.answer(
                            candidate, cache_time=cache_time, is_personal=is_personal
                        )
                    except TelegramBadRequest:
                        continue
        try:
            return await inline_query.answer([], cache_time=1, is_personal=True)
        except Exception:
            pass


@inline_router.inline_query()
async def inline_main_handler(
    inline_query: InlineQuery,
    db_session: AsyncSession,
    i18n: TranslatorRunner,
):
    """
    Инлайн-поиск медиа:
    1. Хэштег #recent (#recents, #недавнее) -> до 15 недавних загрузок пользователя (без музыки)
    2. Запрос paste -> вставка последнего скопированного через /copy медиа из Redis (1 час)
    3. Хэштег #music (#музыка, 🎵) -> поиск музыки в кэше бота
    4. Хэштег #saved (#saves, #сейв, #сейвы) -> поиск только по личным сохранёнкам
    5. По умолчанию пустой запрос (@bot) -> скопированное (1) + недавние (до 5) + личные (до 5) + публичные мемы
    6. Поиск по тексту (@bot <текст>) -> поиск картинок/мемов по названию/описанию
    """
    raw_query = inline_query.query.strip()
    user_id = inline_query.from_user.id
    q_lower = raw_query.lower()

    # 1. ХЭШТЕГ #recent — до 15 недавних загрузок за 12 часов
    is_recent, recent_query = _match_hashtag(raw_query, RECENT_TAGS)
    if is_recent:
        results = []
        recents = await get_recent_downloads(user_id, limit=15)
        seen_file_ids = set()
        for idx, item in enumerate(recents):
            fid = item.get("file_id")
            if fid and fid not in seen_file_ids:
                res = _build_recent_inline_result(item, idx)
                if res:
                    seen_file_ids.add(fid)
                    results.append(res)
        return await _safe_answer_inline(inline_query, results, cache_time=1, is_personal=True)

    # 2. ВСТАВКА ИЗ БУФЕРА ОБМЕНА: paste (или #paste, вставить, буфер)
    if q_lower in PASTE_TRIGGERS:
        copied = await cache_get(f"clipboard:{user_id}")
        results = []
        if copied and isinstance(copied, dict):
            file_id = copied.get("file_id")
            m_type = copied.get("media_type")
            title = f"📋 {copied.get('title') or 'Вставить из буфера'}"

            res_id = f"paste_{user_id}"
            if m_type == "video":
                results.append(InlineQueryResultCachedVideo(id=res_id, title=title, video_file_id=file_id, caption=None))
            elif m_type == "photo":
                results.append(InlineQueryResultCachedPhoto(id=res_id, photo_file_id=file_id, title=title, caption=None))
            elif m_type == "audio":
                results.append(InlineQueryResultCachedAudio(id=res_id, audio_file_id=file_id, caption=None))
            elif m_type == "gif":
                results.append(InlineQueryResultCachedGif(id=res_id, title=title, gif_file_id=file_id, caption=None))

        return await _safe_answer_inline(inline_query, results, cache_time=1, is_personal=True)

    # 3. ХЭШТЕГ #music (или #музыка, 🎵) — поиск музыки
    is_music, music_query = _match_hashtag(raw_query, MUSIC_TAGS)
    if is_music:
        results = []
        tracks = await search_cached_music(db_session, music_query, limit=INLINE_SEARCH_LIMIT)
        for idx, track in enumerate(tracks):
            key_hash = hashlib.md5(track.cache_key.encode()).hexdigest()[:8]
            results.append(
                InlineQueryResultCachedAudio(
                    id=f"music_{idx}_{key_hash}",
                    audio_file_id=track.telegram_file_id,
                    caption=None,
                )
            )
        return await _safe_answer_inline(inline_query, results, cache_time=5, is_personal=True)

    # 4. ХЭШТЕГ #saved (или #saves) — поиск только по личным сохранёнкам
    is_saved, saved_query = _match_hashtag(raw_query, SAVED_TAGS)
    if is_saved:
        results = []
        user_saves = await search_user_saves(
            db_session, user_id, query=saved_query, limit=INLINE_SEARCH_LIMIT
        )
        for save in user_saves:
            item = _build_save_inline_result(save, is_own=True)
            if item:
                results.append(item)
        return await _safe_answer_inline(inline_query, results, cache_time=3, is_personal=True)

    # 5. ПУСТОЙ ЗАПРОС (@bot): структурированная выдача без перегруза
    if not raw_query:
        results = []
        seen_file_ids = set()

        # А. Буфер обмена (первым, если есть скопированное визуальное медиа)
        copied = await cache_get(f"clipboard:{user_id}")
        if copied and isinstance(copied, dict):
            file_id = copied.get("file_id")
            m_type = copied.get("media_type")
            if file_id and m_type in VISUAL_MEDIA_TYPES:
                seen_file_ids.add(file_id)
                title = f"📋 {copied.get('title') or 'Вставить из буфера'}"
                res_id = f"paste_{user_id}"
                if m_type == "video":
                    results.append(InlineQueryResultCachedVideo(id=res_id, title=title, video_file_id=file_id, caption=None))
                elif m_type == "photo":
                    results.append(InlineQueryResultCachedPhoto(id=res_id, photo_file_id=file_id, title=title, caption=None))
                elif m_type == "gif":
                    results.append(InlineQueryResultCachedGif(id=res_id, title=title, gif_file_id=file_id, caption=None))

        # Б. Недавно скачанное (до 5 шт., видео/фото/гиф за 12 часов)
        recents = await get_recent_downloads(user_id, limit=5)
        for idx, item in enumerate(recents):
            fid = item.get("file_id")
            if fid and fid not in seen_file_ids:
                res = _build_recent_inline_result(item, idx)
                if res:
                    seen_file_ids.add(fid)
                    results.append(res)

        # В. Личные сохранёнки пользователя (до 5 шт.)
        user_saves = await search_user_saves(
            db_session, user_id, query="", limit=5, media_types=VISUAL_MEDIA_TYPES
        )
        for save in user_saves:
            if save.telegram_file_id not in seen_file_ids:
                res = _build_save_inline_result(save, is_own=True)
                if res:
                    seen_file_ids.add(save.telegram_file_id)
                    results.append(res)

        # Г. Популярные публичные мемы библиотеки (добирают до 25)
        remaining = INLINE_SEARCH_LIMIT - len(results)
        if remaining > 0:
            pub_saves = await search_public_saves(
                db_session, query="", exclude_user_id=user_id,
                limit=remaining, media_types=VISUAL_MEDIA_TYPES
            )
            for save in pub_saves:
                if save.telegram_file_id not in seen_file_ids:
                    res = _build_save_inline_result(save, is_own=False)
                    if res:
                        seen_file_ids.add(save.telegram_file_id)
                        results.append(res)

        return await _safe_answer_inline(inline_query, results, cache_time=1, is_personal=True)

    # 6. ПОИСК ПО ТЕКСТУ (@bot <текст>)
    results = []
    user_saves = await search_user_saves(
        db_session, user_id, query=raw_query, limit=INLINE_SEARCH_LIMIT, media_types=VISUAL_MEDIA_TYPES
    )
    for save in user_saves:
        item = _build_save_inline_result(save, is_own=True)
        if item:
            results.append(item)

    if len(results) < INLINE_SEARCH_LIMIT:
        pub_saves = await search_public_saves(
            db_session, query=raw_query, exclude_user_id=user_id,
            limit=INLINE_SEARCH_LIMIT - len(results), media_types=VISUAL_MEDIA_TYPES
        )
        for save in pub_saves:
            item = _build_save_inline_result(save, is_own=False)
            if item:
                results.append(item)

    return await _safe_answer_inline(inline_query, results, cache_time=3, is_personal=True)


@inline_router.chosen_inline_result()
async def handle_chosen_inline_result(
    chosen: ChosenInlineResult,
    db_session: AsyncSession,
):
    """Счётчик популярности: увеличивает uses_count при отправке сохранёнки/мема (чужими пользователями)"""
    if chosen.result_id.startswith("save_"):
        try:
            save_id = int(chosen.result_id.split("_")[1])
            user_id = chosen.from_user.id
            await increment_save_uses(db_session, save_id, user_id=user_id)
        except Exception as e:
            logger.debug(f"Failed to increment save uses: {e}")
