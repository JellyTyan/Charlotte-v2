import logging
import hashlib
import re
from typing import Any, Dict, Optional

from curl_cffi.requests import AsyncSession
from sqlalchemy.ext.asyncio import AsyncSession as DbAsyncSession
from storage.db.crud import get_media_cache
from models.media import MediaContent, MediaType

from models.errors import BotError, ErrorCode
from models.metadata import MediaMetadata, MetadataType, MediaAttachment

logger = logging.getLogger(__name__)


async def get_pin_info(url: str) -> MediaMetadata:
    """Fetch pin information from Pinterest API."""
    async with AsyncSession(impersonate="chrome136") as session:
        response = await session.get(url, allow_redirects=True)
        final_url = str(response.url)

        match = re.search(r"/pin/(\d+)", final_url)
        if not match:
            raise BotError(
                code=ErrorCode.INVALID_URL,
                message="Failed to extract pin ID from URL",
                url=url,
                is_logged=False
            )

        pin_id = match.group(1)
        api_url = "https://www.pinterest.com/resource/PinResource/get/"
        headers = {
            "accept": "application/json, text/javascript, */*, q=0.01",
            "x-pinterest-pws-handler": "www/pin/[id]/feedback.js",
        }
        params = {
            "source_url": f"/pin/{pin_id}",
            "data": f'{{"options":{{"id":"{pin_id}","field_set_key":"auth_web_main_pin","noCache":true,"fetch_visual_search_objects":true}},"context":{{}}}}',
        }

        response = await session.get(api_url, params=params, headers=headers)
        if response.status_code != 200:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message=f"Failed to retrieve pin info. Status code: {response.status_code}",
                url=url,
                is_logged=True
            )

        data = response.json().get("resource_response", {}).get("data", {})
        if not data:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Invalid API response structure",
                url=url,
                is_logged=True
            )

        title = data.get("title") or "Pinterest Media"
        attachments = []
        media_type = "unknown"

        # Carousel
        carousel_data = data.get("carousel_data") or {}
        carousel = carousel_data.get("carousel_slots")
        if carousel:
            for slot in carousel:
                img_url = slot.get("images", {}).get("736x", {}).get("url")
                if img_url:
                    attachments.append(MediaAttachment(url=img_url, mime_type="image/jpeg"))
            media_type = "gallery" if attachments else "unknown"

        # Story pin video
        elif not attachments:
            story_pin = data.get("story_pin_data") or {}
            pages = story_pin.get("pages")
            if pages and pages[0].get("blocks"):
                video_block = (pages[0]["blocks"][0].get("video") or {}).get("video_list")
                if video_block:
                    video_url = get_best_video(video_block)
                    if video_url:
                        attachments.append(MediaAttachment(url=video_url, mime_type="video/mp4"))
                        media_type = "video"

        # Regular video
        if not attachments:
            videos = data.get("videos") or {}
            video_list = videos.get("video_list")
            if video_list:
                video_url = get_best_video(video_list)
                if video_url:
                    attachments.append(MediaAttachment(url=video_url, mime_type="video/mp4"))
                    media_type = "video"

        # Image or GIF
        if not attachments:
            images = data.get("images") or {}
            orig = images.get("orig") or {}
            img_url = orig.get("url")
            if img_url:
                is_gif = img_url.lower().endswith(".gif")
                mime_type = "image/gif" if is_gif else "image/jpeg"
                media_type = "gif" if is_gif else "photo"
                attachments.append(MediaAttachment(url=img_url, mime_type=mime_type))

        if not attachments:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message=f"Unknown Pinterest media type. Pin id: {pin_id}",
                url=url,
                is_logged=True
            )

        return MediaMetadata(
            type=MetadataType.METADATA,
            url=url,
            title=title,
            media_type=media_type,
            attachments=attachments,
            extra={"image_signature": data.get("image_signature", pin_id)}
        )


def get_best_video(video_list: Dict[str, Any]) -> Optional[str]:
    """Select the best quality video from available options."""
    video_qualities = ["V_EXP7", "V_720P", "V_480P", "V_360P", "V_HLSV3_MOBILE"]
    for quality in video_qualities:
        if quality in video_list:
            return video_list[quality]["url"]
    return None

def get_cache_key(url: str) -> str:
    # Try to extract Pin ID
    match = re.search(r"/pin/(\d+)", url)
    if match:
        return f"pin:{match.group(1)}"
        
    # Fallback and parameter stripping
    clean_url = url.split('?')[0].rstrip('/')
    hashed = hashlib.md5(clean_url.encode('utf-8')).hexdigest()
    return f"pin:{hashed}"

async def cache_check(db_session: DbAsyncSession, key: str) -> list[MediaContent] | None:
    cached = await get_media_cache(db_session, key)
    if not cached:
        return None

    if cached.media_type == "gallery":
        results = []
        for c_item in cached.data.items:
            t_type = MediaType(c_item.media_type) if c_item.media_type else MediaType.PHOTO
            results.append(MediaContent(
                type=t_type,
                telegram_file_id=c_item.file_id,
                telegram_document_file_id=c_item.raw_file_id,
                cover_file_id=c_item.cover,
                full_cover_file_id=cached.data.full_cover,
                title=cached.data.title,
                performer=cached.data.author,
                duration=c_item.duration or cached.data.duration,
                width=c_item.width or cached.data.width,
                height=c_item.height or cached.data.height,
                is_blurred=c_item.is_blurred if c_item.is_blurred is not None else cached.data.is_blurred
            ))
        return results

    try:
        media_type = MediaType(cached.media_type)
    except ValueError:
        media_type = MediaType.VIDEO if cached.data.width else MediaType.PHOTO
        
    return [MediaContent(
        type=media_type,
        telegram_file_id=cached.telegram_file_id,
        telegram_document_file_id=cached.telegram_document_file_id,
        cover_file_id=cached.data.cover,
        full_cover_file_id=cached.data.full_cover,
        title=cached.data.title,
        performer=cached.data.author,
        duration=cached.data.duration,
        width=cached.data.width,
        height=cached.data.height,
        is_blurred=cached.data.is_blurred
    )]
