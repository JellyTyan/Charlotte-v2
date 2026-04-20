import hashlib
import logging
from aiogram import F
from aiogram.types import (
    InlineQuery, 
    InlineQueryResultCachedVideo, 
    InlineQueryResultCachedPhoto, 
    FSInputFile, 
    InputTextMessageContent, 
    InlineQueryResultArticle
)
from core.config import Config
from storage.cache.redis_client import cache_get, cache_set
from utils.arq_pool import get_arq_pool

from modules.router import service_router as router
from modules.twitter.handler import TWITTER_REGEX
from modules.twitter.service import TwitterService
from modules.instagram.handler import INSTAGRAM_REGEX
from modules.instagram.service import InstagramService
from models.media import MediaType
import re

logger = logging.getLogger(__name__)

@router.inline_query(F.query.regexp(TWITTER_REGEX) | F.query.regexp(INSTAGRAM_REGEX))
async def inline_media_handler(inline_query: InlineQuery, config: Config):
    url = inline_query.query.strip()
    
    # Check cache
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_key = f"inline_cache:{url_hash}"
    cached_data = await cache_get(cache_key)
    
    if cached_data:
        file_id = cached_data.get('file_id')
        media_type = cached_data.get('type')
        
        if media_type == 'video':
            result = InlineQueryResultCachedVideo(
                id=url_hash,
                title="Video",
                video_file_id=file_id
            )
        elif media_type == 'gif':
            result = InlineQueryResultCachedVideo(
                id=url_hash,
                title="GIF",
                video_file_id=file_id
            )
        else:
            result = InlineQueryResultCachedPhoto(
                id=url_hash,
                title="Photo",
                photo_file_id=file_id
            )
        await inline_query.answer([result], cache_time=300)
        return

    # Not cached, download and upload
    try:
        arq = await get_arq_pool('light')
        
        if re.match(TWITTER_REGEX, url):
            service = TwitterService(arq=arq)
            media_items = await service.download(url, premium=False, config=config, allow_nsfw=True)
        elif re.match(INSTAGRAM_REGEX, url):
            service = InstagramService(arq=arq)
            media_items = await service.download(url)
        else:
            await inline_query.answer([], cache_time=10)
            return
        
        if not media_items:
            await inline_query.answer([], cache_time=10)
            return
            
        item = media_items[0]
        bot = inline_query.bot
        admin_id = config.ADMIN_ID
        
        if item.type in (MediaType.VIDEO, MediaType.GIF):
            msg = await bot.send_video(
                chat_id=admin_id,
                video=FSInputFile(item.path),
                caption=f"Inline Cache Dump: {url}",
                disable_notification=True
            )
            file_id = msg.video.file_id
            media_type = 'video' if item.type == MediaType.VIDEO else 'gif'
        elif item.type == MediaType.PHOTO:
            msg = await bot.send_photo(
                chat_id=admin_id,
                photo=FSInputFile(item.path),
                caption=f"Inline Cache Dump: {url}",
                disable_notification=True
            )
            file_id = msg.photo[-1].file_id
            media_type = 'photo'
        else:
            await inline_query.answer([], cache_time=10)
            return
            
        # Clean up file
        if item.path and item.path.exists():
            item.path.unlink()
            
        # Save to cache
        await cache_set(cache_key, {"file_id": file_id, "type": media_type}, ttl=86400 * 7) # cache for 7 days
        
        # Send result
        if media_type in ('video', 'gif'):
            result = InlineQueryResultCachedVideo(
                id=url_hash,
                title="Video / GIF" if media_type == 'gif' else "Video",
                video_file_id=file_id
            )
        else:
            result = InlineQueryResultCachedPhoto(
                id=url_hash,
                title="Photo",
                photo_file_id=file_id
            )
        await inline_query.answer([result], cache_time=300)
        
    except Exception as e:
        logger.error(f"Inline download failed: {e}")
        # fallback result
        result = InlineQueryResultArticle(
            id=url_hash,
            title="Error",
            description="Failed to download media or timeout.",
            input_message_content=InputTextMessageContent(message_text="Failed to download media")
        )
        await inline_query.answer([result], cache_time=10)
