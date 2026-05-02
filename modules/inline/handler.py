import hashlib
import logging
import asyncio
import re
from aiogram import F, Router
from aiogram.types import (
    InlineQuery,
    InlineQueryResultCachedVideo,
    InlineQueryResultCachedPhoto,
    InlineQueryResultCachedAudio,
    InputTextMessageContent,
    InlineQueryResultArticle,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from core.config import Config
from storage.cache.redis_client import cache_set
from storage.db.crud import get_media_cache
from utils.arq_pool import get_arq_pool
from senders.media_sender import MediaSender
from models.media import MediaType, MediaContent
from sqlalchemy.ext.asyncio import AsyncSession
from fluentogram import TranslatorRunner

# Service Regexes & Utils
from modules.services.twitter.handler import TWITTER_REGEX
from modules.services.twitter.service import TwitterService
from modules.services.twitter.utils import get_cache_key as twitter_cache_key

from modules.services.instagram.handler import INSTAGRAM_REGEX
from modules.services.instagram.utils import get_cache_key as instagram_cache_key

from modules.services.pinterest.handler import PINTEREST_REGEX
from modules.services.pinterest.service import PinterestService
from modules.services.pinterest.utils import get_cache_key as pinterest_cache_key

from modules.services.reddit.handler import REDDIT_REGEX
from modules.services.reddit.service import RedditService
from modules.services.reddit.utils import get_cache_key as reddit_cache_key

from modules.services.tiktok.handler import TIKTOK_REGEX
from modules.services.tiktok.utils import get_cache_key as tiktok_cache_key

from modules.services.youtube.handler import YOUTUBE_REGEX
from modules.services.youtube.utils import get_cache_key as youtube_cache_key

from modules.services.ytmusic.handler import YTMUSIC_REGEX
from modules.services.ytmusic.service import cache_check as ytmusic_cache_key

from modules.services.soundcloud.handler import SOUNDCLOUD_REGEX
from modules.services.soundcloud.utils import get_cache_key as soundcloud_cache_key

from modules.services.spotify.handler import SPOTIFY_REGEX
from modules.services.spotify.utils import get_cache_key as spotify_cache_key

from modules.services.deezer.handler import DEEZER_REGEX
from modules.services.deezer.utils import get_cache_key as deezer_cache_key

from modules.services.nicovideo.handler import NICOVIDEO_REGEX
from modules.services.nicovideo.utils import get_cache_key as nicovideo_cache_key

from modules.services.apple_music.handler import APPLE_REGEX as APPLE_MUSIC_REGEX
from modules.services.apple_music.utils import get_cache_key as apple_music_cache_key

from modules.services.bluesky.handler import BLUESKY_REGEX
from modules.services.bluesky.utils import get_cache_key as bluesky_cache_key

from modules.services.twitch.handler import TWITCH_REGEX
from modules.services.twitch.utils import get_cache_key as twitch_cache_key

inline_router = Router(name="inline_handler")

logger = logging.getLogger(__name__)

# Списки сервисов для разной логики
FAST_TRACK_SERVICES = ["twitter", "reddit", "pinterest"]

@inline_router.inline_query(F.query.regexp(r"^https?://"))
async def inline_media_handler(inline_query: InlineQuery, config: Config, db_session: AsyncSession, i18n: TranslatorRunner):
    url = inline_query.query.strip()
    url_hash = hashlib.md5(url.encode()).hexdigest()
    
    service_name = None
    cache_key = None
    
    # Определение сервиса и ключа кэша
    if re.match(TWITTER_REGEX, url):
        service_name = "twitter"
        cache_key = twitter_cache_key(url)
    elif re.match(REDDIT_REGEX, url):
        service_name = "reddit"
        cache_key = reddit_cache_key(url)
    elif re.match(PINTEREST_REGEX, url):
        service_name = "pinterest"
        cache_key = pinterest_cache_key(url)
    elif re.match(INSTAGRAM_REGEX, url):
        service_name = "instagram"
        cache_key = instagram_cache_key(url)
    elif re.match(TIKTOK_REGEX, url):
        service_name = "tiktok"
        cache_key = tiktok_cache_key(url)
    elif re.match(YOUTUBE_REGEX, url):
        service_name = "youtube"
        cache_key = youtube_cache_key(url, "default")
    elif re.match(YTMUSIC_REGEX, url):
        service_name = "ytmusic"
        cache_key = ytmusic_cache_key(url, "default")
    elif re.match(SOUNDCLOUD_REGEX, url):
        service_name = "soundcloud"
        cache_key = soundcloud_cache_key(url)
    elif re.match(SPOTIFY_REGEX, url):
        service_name = "spotify"
        cache_key = spotify_cache_key(url)
    elif re.match(DEEZER_REGEX, url):
        service_name = "deezer"
        cache_key = deezer_cache_key(url)
    elif re.match(NICOVIDEO_REGEX, url):
        service_name = "nicovideo"
        cache_key = nicovideo_cache_key(url, "default")
    elif re.match(APPLE_MUSIC_REGEX, url):
        service_name = "apple_music"
        cache_key = apple_music_cache_key(url)
    elif re.match(BLUESKY_REGEX, url):
        service_name = "bluesky"
        cache_key = bluesky_cache_key(url)
    elif re.match(TWITCH_REGEX, url):
        service_name = "twitch"
        cache_key = twitch_cache_key(url)
        
    if not service_name or not cache_key:
        return await inline_query.answer([], cache_time=10)

    try:
        # 1. ПРОВЕРЯЕМ КЭШ (Для ВСЕХ сервисов - это бесплатно)
        cached_dto = await get_media_cache(db_session, cache_key)
        media_items = []

        if cached_dto:
            if cached_dto.media_type == "gallery":
                for item in cached_dto.data.items:
                    media_items.append(MediaContent(
                        type=MediaType(item.media_type),
                        telegram_file_id=item.file_id,
                        title=cached_dto.data.title
                    ))
            else:
                media_items.append(MediaContent(
                    type=MediaType(cached_dto.media_type),
                    telegram_file_id=cached_dto.telegram_file_id,
                    title=cached_dto.data.title
                ))
        
        # 2. КЭША НЕТ. Решаем, качать или сразу отправить в ЛС
        if not media_items:
            if service_name in FAST_TRACK_SERVICES:
                # Пытаемся скачать (Twitter, Reddit, Pinterest)
                arq = await get_arq_pool('light')
                service_obj = None
                coro = None
                
                if service_name == "twitter":
                    service_obj = TwitterService(arq=arq)
                    coro = service_obj.download(url, premium=False, config=config, allow_nsfw=True)
                elif service_name == "reddit":
                    service_obj = RedditService(arq=arq)
                    coro = service_obj.download(url)
                elif service_name == "pinterest":
                    service_obj = PinterestService(arq=arq)
                    coro = service_obj.download(url)

                if coro:
                    try:
                        # ⏳ 7 секунд на всё про всё
                        downloaded_content = await asyncio.wait_for(coro, timeout=7.0)
                        if downloaded_content:
                            sender = MediaSender()
                            dump_success = await sender._dump_media_to_cache_channel(inline_query.bot, downloaded_content)
                            if dump_success:
                                await sender._save_to_cache(downloaded_content, cache_key, service_name, downloaded_content[0].title, db_session)
                                media_items = downloaded_content
                    except asyncio.TimeoutError:
                        logger.warning(f"Inline timeout for {url}")
                    except Exception as e:
                        logger.error(f"Inline download error: {e}")
            else:
                # Для остальных сервисов (Instagram, TikTok, YouTube и т.д.) - сразу фолбэк
                pass

        # 3. ОТДАЕМ РЕЗУЛЬТАТ (Медиа или Фолбэк)
        if not media_items:
            await cache_set(f"inline_url:{url_hash}", {'url': url}, 600)

            fallback = InlineQueryResultArticle(
                id=url_hash,
                title=i18n.inline.download.title(),
                description=i18n.inline.download.desc(),
                thumbnail_url="https://img.icons8.com/color/48/000000/download--v1.png",
                input_message_content=InputTextMessageContent(
                    message_text=i18n.inline.download.msg(service=service_name.capitalize()),
                    parse_mode="Markdown"
                ),
                # ВОТ ОНА - КНОПКА ПРЯМОГО ПЕРЕХОДА
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=i18n.inline.download.btn(), url=f"https://t.me/YloaderZefirkaBot?start={url_hash}")]
                ])
            )
            return await inline_query.answer([fallback], cache_time=5, is_personal=True)

        from storage.db.crud import get_user, get_user_settings
        from utils.text_utils import truncate_string, escape_html

        user = await get_user(db_session, inline_query.from_user.id)
        is_premium = user.is_premium if user else False
        user_settings = await get_user_settings(db_session, inline_query.from_user.id)
        
        show_ad = True
        if user_settings and is_premium:
            show_ad = user_settings.profile.bot_sign

        results = []
        for i, media in enumerate(media_items):
            if not media.telegram_file_id:
                continue
            res_id = f"{url_hash}_{i}"

            final_caption = escape_html(media.title) if media.title else ""
            if show_ad:
                ad_text = "\n\n<a href='https://t.me/CharlotteFox_Bot'>Charlotte 🧡</a>"
                final_caption = truncate_string(final_caption, 1000)
                final_caption += ad_text
            elif not final_caption:
                final_caption = None
            
            if media.type in [MediaType.VIDEO, MediaType.GIF]:
                results.append(InlineQueryResultCachedVideo(id=res_id, title=media.title or "Video", video_file_id=media.telegram_file_id, caption=final_caption, parse_mode="HTML"))
            elif media.type == MediaType.PHOTO:
                results.append(InlineQueryResultCachedPhoto(id=res_id, photo_file_id=media.telegram_file_id, title=media.title or "Photo", caption=final_caption, parse_mode="HTML"))
            elif media.type == MediaType.AUDIO:
                results.append(InlineQueryResultCachedAudio(id=res_id, audio_file_id=media.telegram_file_id, caption=final_caption, parse_mode="HTML"))

        if not results:
             return await inline_query.answer([], cache_time=5)

        return await inline_query.answer(results, cache_time=300)
        
    except Exception as e:
        logger.error(f"Critical inline error: {e}")
        return await inline_query.answer([], cache_time=10)