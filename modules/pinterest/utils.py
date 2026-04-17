import logging
import re
from typing import Any, Dict, Optional

from curl_cffi.requests import AsyncSession

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
