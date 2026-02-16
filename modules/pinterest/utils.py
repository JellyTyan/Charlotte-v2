import logging
import re
from typing import Any, Dict, Optional

from curl_cffi.requests import AsyncSession

from models.errors import BotError, ErrorCode
from utils import get_user_agent

logger = logging.getLogger(__name__)


async def get_pin_info(url: str) -> Dict[str, Any]:
    """Fetch pin information from Pinterest API."""
    async with AsyncSession(impersonate="chrome136") as session:
        # Follow redirects for short URLs
        response = await session.get(url, allow_redirects=True)
        final_url = str(response.url)

        # Extract pin ID from URL
        match = re.search(r"/pin/(\d+)", final_url)
        if not match:
            raise BotError(
                code=ErrorCode.INVALID_URL,
                message="Failed to extract pin ID from URL",
                url=url,
                is_logged=False
            )

        pin_id = match.group(1)
        logger.debug(f"Extracted pin ID: {pin_id}")

        # Fetch pin data from API
        api_url = "https://www.pinterest.com/resource/PinResource/get/"
        headers = {
            "accept": "application/json, text/javascript, */*, q=0.01",
            "user-agent": get_user_agent(),
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

        response_json = response.json()
        root = response_json["resource_response"]["data"]

        title = root.get("title", "Pinterest Media")
        image_signature = root["image_signature"]
        ext = ""
        carousel_data = None
        video = None
        image = None

        # Check for carousel
        if root.get("carousel_data"):
            carousel = root["carousel_data"]["carousel_slots"]
            carousel_data = []
            for carousel_element in carousel:
                image_url = carousel_element["images"]["736x"]["url"]
                carousel_data.append(image_url)
            ext = "carousel"

        # Check for story pin video
        elif (
            isinstance(root.get("story_pin_data"), dict)
            and isinstance(root["story_pin_data"].get("pages"), list)
            and len(root["story_pin_data"]["pages"]) > 0
            and isinstance(root["story_pin_data"]["pages"][0].get("blocks"), list)
            and len(root["story_pin_data"]["pages"][0]["blocks"]) > 0
            and isinstance(root["story_pin_data"]["pages"][0]["blocks"][0], dict)
            and isinstance(
                root["story_pin_data"]["pages"][0]["blocks"][0].get("video"), dict
            )
            and isinstance(
                root["story_pin_data"]["pages"][0]["blocks"][0]["video"].get(
                    "video_list"
                ),
                dict,
            )
        ):
            video_list = root["story_pin_data"]["pages"][0]["blocks"][0]["video"][
                "video_list"
            ]
            video = get_best_video(video_list)

            if video:
                ext = "mp4"

        # Check for regular video
        elif isinstance(root.get("videos"), dict) and isinstance(
            root["videos"].get("video_list"), dict
        ):
            video_list = root["videos"]["video_list"]
            video = get_best_video(video_list)

            if video:
                ext = "mp4"

        # Check for image
        elif (
            isinstance(root.get("images"), dict)
            and isinstance(root["images"].get("orig"), dict)
            and "url" in root["images"]["orig"]
        ):
            image = root["images"]["orig"]["url"]
            ext = "jpg"

        else:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message=f"Unknown Pinterest media type. Pin id: {pin_id}",
                url=url,
                is_logged=True
            )

        data = {
            "title": title,
            "image_signature": image_signature,
            "ext": ext,
            "carousel_data": carousel_data,
            "video": video,
            "image": image,
        }

        return data


def get_best_video(video_list: Dict[str, Any]) -> Optional[str]:
    """Select the best quality video from available options."""
    video_qualities = ["V_EXP7", "V_720P", "V_480P", "V_360P", "V_HLSV3_MOBILE"]
    for quality in video_qualities:
        if quality in video_list:
            return video_list[quality]["url"]
    return None
