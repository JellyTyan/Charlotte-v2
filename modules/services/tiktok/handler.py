import logging
import re
from pathlib import Path

from curl_cffi.requests import AsyncSession as CurlAsyncSession
import httpx
from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.ext.asyncio import AsyncSession

from models.media import MediaContent, MediaType
from models.service_list import Services
from modules.services._shared import build_media_items, cache_check, make_cache_key
from senders.media_sender import MediaSender
from storage.db.crud import check_if_user_premium
from tasks.task_manager import task_manager
from utils import build_caption, escape_html, format_author_link, extract_url

tiktok_router = Router(name="tiktok")

logger = logging.getLogger(__name__)

TIKTOK_REGEX = r"https?://(?:(?:www\.|m\.)?tiktok\.com/\S+|(?:vm|vt)\.tiktok\.com/\S+|(?:www\.)?tt\.site/\S+)"


async def resolve_tiktok_url(url: str) -> str:
    """
    Resolves short or redirecting TikTok URLs (e.g. tt.site/t/..., vm.tiktok.com/..., vt.tiktok.com/...)
    to canonical tiktok.com/@user/video/... or tiktok.com/@user/photo/... URL
    using curl_cffi with Chrome browser impersonation.
    """
    if re.search(r"tiktok\.com/.+/(?:video|photo)/\d+", url):
        return url

    try:
        async with CurlAsyncSession(impersonate="chrome") as session:
            res = await session.get(url, allow_redirects=True, timeout=10.0)
            final_url = str(res.url)
            return final_url.split("#")[0]
    except Exception as e:
        logger.warning(f"Failed to resolve TikTok URL {url} with curl_cffi: {e}")
        return url


@tiktok_router.message(F.text.regexp(TIKTOK_REGEX))
async def tiktok_handler(message: Message, db_session: AsyncSession, http_client: httpx.AsyncClient):
    raw_text = message.text or message.caption
    if not raw_text or not message.from_user:
        return

    url = extract_url(TIKTOK_REGEX, raw_text)
    if not url:
        return
    url = url.split("#")[0]
    user_id = message.from_user.id

    if task_manager.is_user_busy(user_id):
        from utils.ephemeral import notify_already_downloading_if_ephemeral
        await notify_already_downloading_if_ephemeral(message, user_id)

    from utils.effects import react_safe
    await react_safe(message, "👀")

    sponsor = await check_if_user_premium(db_session, user_id)

    async with ChatActionSender.choose_sticker(bot=message.bot, chat_id=message.chat.id):
        send_manager = MediaSender()
        resolved_url = await resolve_tiktok_url(url)
        cache_key = get_cache_key(resolved_url, sponsor)

        cached = await cache_check(db_session, cache_key)
        if not cached and resolved_url != url:
            fallback_cache_key = get_cache_key(url, sponsor)
            cached = await cache_check(db_session, fallback_cache_key)

        if cached:
            await send_manager.send(message, cached, service="tiktok", db_session=db_session)
            return

    async with ChatActionSender.record_video_note(bot=message.bot, chat_id=message.chat.id):
        payload = {
            "user_id": user_id,
            "url": resolved_url,
            "sponsor": sponsor,
            "nsfw": False,
        }
        metadata = await task_manager.run_media_download(
            user_id=user_id,
            url=resolved_url,
            service=Services.TIKTOK,
            payload=payload,
            http_client=http_client,
        )

        author_data = metadata.get('author') if isinstance(metadata.get('author'), dict) else {}
        author_username = author_data.get('username') or metadata.get('author_username')
        author_name = author_data.get('name')
        author_url = author_data.get('url') or (f"https://www.tiktok.com/@{author_username}/" if author_username else "")
        author_display = author_username or author_name
        author_link = format_author_link(author_display, author_url, icon="👤")

        description = escape_html((metadata.get('caption') or metadata.get('title') or "").strip())
        caption = build_caption(header=author_link, description=description)

        is_nsfw = bool(metadata.get('is_nsfw') or metadata.get('is_sensitive'))
        is_blurred = bool(metadata.get('is_blurred') or is_nsfw)

        media_content = build_media_items(metadata.get('items', []), caption, is_blurred, is_nsfw)

        music_info = metadata.get('audio') or metadata.get('music_info') or {}
        if music_info and music_info.get('path'):
            audio_cover_str = music_info.get('cover') or music_info.get('cover_path')
            audio_cover = Path(audio_cover_str) if audio_cover_str and Path(audio_cover_str).exists() else None
            media_content.append(
                MediaContent(
                    type=MediaType.AUDIO,
                    path=Path(music_info.get('path')),
                    title=music_info.get('title'),
                    performer=music_info.get('author'),
                    cover=audio_cover,
                    duration=music_info.get('duration'),
                )
            )

    if media_content:
        await send_manager.send(message, media_content, service="tiktok", cache_key=cache_key, db_session=db_session)


def get_cache_key(url: str, sponsor: bool) -> str:
    return make_cache_key("tt", url, r"/(?:video|photo)/(\d+)", ":sponsor" if sponsor else "")
