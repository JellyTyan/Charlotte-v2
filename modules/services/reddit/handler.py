import logging


import httpx
from aiogram import F, Router
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender
from sqlalchemy.ext.asyncio import AsyncSession

from models.service_list import Services
from modules.services._shared import build_media_items, cache_check, ensure_nsfw_allowed, make_cache_key
from senders.media_sender import MediaSender
from storage.db.crud import check_if_user_premium, get_chat_settings
from tasks.task_manager import task_manager
from utils import escape_html, build_caption, format_author_link, extract_url

reddit_router = Router(name="reddit")

logger = logging.getLogger(__name__)

REDDIT_REGEX = r"https?:\/\/(?:www\.|old\.|new\.)?reddit\.com\/(?:r\/[A-Za-z0-9_]+\/)?(?:comments\/[A-Za-z0-9]+(?:\/[^\/\s?]+)?|s\/[A-Za-z0-9]+|gallery\/[A-Za-z0-9]+)(?:\/)?"


@reddit_router.message(F.text.regexp(REDDIT_REGEX))
async def reddit_handler(
    message: Message,
    db_session: AsyncSession,
    http_client: httpx.AsyncClient,
):
    if not message.text or not message.from_user:
        return

    url = extract_url(REDDIT_REGEX, message.text)
    if not url:
        return
    chat_id = message.chat.id
    user_id = message.from_user.id

    from utils.effects import react_safe
    await react_safe(message, "👀")

    if "/s/" in url:
        try:
            res = await http_client.head(url, follow_redirects=True, timeout=5.0)
            url = str(res.url)
        except Exception:
            pass

    sponsor = await check_if_user_premium(db_session, user_id)

    async with ChatActionSender.choose_sticker(bot=message.bot, chat_id=chat_id):
        send_manager = MediaSender()
        cache_key = get_cache_key(url)

        allow_nsfw = True
        if chat_id < 0:
            settings = await get_chat_settings(db_session, chat_id)
            allow_nsfw = settings.profile.allow_nsfw

        cached = await cache_check(db_session, cache_key)
        if cached:
            is_nsfw = any(item.is_nsfw for item in cached)
            ensure_nsfw_allowed(is_nsfw, sponsor, allow_nsfw, url, Services.REDDIT)
            await send_manager.send(message, cached, service="reddit", db_session=db_session)
            return

    async with ChatActionSender.record_video_note(bot=message.bot, chat_id=chat_id):
        payload = {
            "user_id": user_id,
            "url": url,
            "sponsor": sponsor,
            "nsfw": allow_nsfw,
        }
        metadata = await task_manager.run_media_download(
            user_id=user_id,
            url=url,
            service=Services.REDDIT,
            payload=payload,
            http_client=http_client,
        )

        # Check NSFW status from response
        is_nsfw = bool(metadata.get('is_nsfw') or metadata.get('is_sensitive'))
        is_blurred = bool(metadata.get('is_blurred') or is_nsfw)

        ensure_nsfw_allowed(is_nsfw, sponsor, allow_nsfw, url, Services.REDDIT)

        author_data = metadata.get('author') if isinstance(metadata.get('author'), dict) else {}
        author_username = author_data.get('username') or metadata.get('author_username')
        author_name = author_data.get('name')
        author_url = author_data.get('url') or (f"https://www.reddit.com/user/{author_username}" if author_username else "")
        author_display = author_username or author_name
        author_link = format_author_link(author_display, author_url, icon="")

        extra_data = metadata.get('extra') if isinstance(metadata.get('extra'), dict) else {}
        subreddit = extra_data.get('subreddit') or metadata.get('subreddit')
        if subreddit:
            sub_str = str(subreddit).strip('/')
            sub_url = subreddit if sub_str.startswith("http") else f"https://www.reddit.com/r/{sub_str.removeprefix('r/')}"
            sub_name = sub_str if sub_str.startswith("r/") else f"r/{sub_str}"
            subreddit_link = f"<a href='{escape_html(sub_url)}'>{escape_html(sub_name)}</a>"
        else:
            subreddit_link = ""

        description = escape_html((metadata.get('caption') or metadata.get('title') or "").strip())
        
        header = ""
        if author_link and subreddit_link:
            header = f"👤 {author_link} on {subreddit_link}"
        elif author_link:
            header = f"👤 {author_link}"
        elif subreddit_link:
            header = f"📌 {subreddit_link}"

        caption = build_caption(header=header, description=description)

        media_content = build_media_items(metadata.get('items', []), caption, is_blurred, is_nsfw)

    if media_content:
        await send_manager.send(message, media_content, service="reddit", cache_key=cache_key, db_session=db_session)


def get_cache_key(url: str) -> str:
    return make_cache_key("rd", url, r"(?:comments|gallery)/([A-Za-z0-9_]+)")
