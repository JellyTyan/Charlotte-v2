import logging

import httpx
from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.ext.asyncio import AsyncSession

from models.service_list import Services
from modules.services._shared import build_post_media, cache_check, make_cache_key
from senders.media_sender import MediaSender
from storage.db.crud import check_if_user_premium
from tasks.task_manager import resolve_url, task_manager
from utils import format_author_link, extract_url

douyin_router = Router(name="douyin")

logger = logging.getLogger(__name__)

DOUYIN_REGEX = (
    r"https?://(?:v\.douyin\.com/[\w-]+/?"
    r"|(?:www\.)?(?:douyin\.com|iesdouyin\.com/share)/(?:video|note)/\d+/?)"
)


@douyin_router.message(F.text.regexp(DOUYIN_REGEX))
async def douyin_handler(message: Message, db_session: AsyncSession, http_client: httpx.AsyncClient):
    raw_text = message.text or message.caption
    if not raw_text or not message.from_user:
        return

    url = extract_url(DOUYIN_REGEX, raw_text)
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
        if "v.douyin.com/" in url:
            url = (await resolve_url(http_client, url)).split("#")[0]
        cache_key = get_cache_key(url, sponsor)

        cached = await cache_check(db_session, cache_key)
        if cached:
            await send_manager.send(message, cached, service="douyin", db_session=db_session)
            return

    async with ChatActionSender.record_video_note(bot=message.bot, chat_id=message.chat.id):
        payload = {
            "user_id": user_id,
            "url": url,
            "sponsor": sponsor,
            "nsfw": False,
        }
        metadata = await task_manager.run_media_download(
            user_id=user_id,
            url=url,
            service=Services.DOUYIN,
            payload=payload,
            http_client=http_client,
        )

        # Douyin profiles can't be linked by nickname (author.url is always empty) - plain name
        author_data = metadata.get('author') if isinstance(metadata.get('author'), dict) else {}
        author_link = format_author_link(author_data.get('name') or author_data.get('username'), icon="👤")
        media_content = build_post_media(metadata, author_link)

    if media_content:
        await send_manager.send(message, media_content, service="douyin", cache_key=cache_key, db_session=db_session)


def get_cache_key(url: str, sponsor: bool) -> str:
    return make_cache_key("dy", url, r"/(?:video|note)/(\d+)", ":sponsor" if sponsor else "")
