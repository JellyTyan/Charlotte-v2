import asyncio
import logging
import re
from typing import Any, Dict, Optional

import aiofiles
import httpx
import yt_dlp

from models.errors import BotError, ErrorCode

logger = logging.getLogger(__name__)


async def get_pin_info(pin_id: int, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Fetch pin information from Pinterest API."""
    url = "https://www.pinterest.com/resource/PinResource/get/"
    headers = {
        "accept": "application/json, text/javascript, */*, q=0.01",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "x-pinterest-pws-handler": "www/pin/[id]/feedback.js",
    }
    params = {
        "source_url": f"/pin/{pin_id}",
        "data": f'{{"options":{{"id":"{pin_id}","field_set_key":"auth_web_main_pin","noCache":true,"fetch_visual_search_objects":true}},"context":{{}}}}',
    }

    response = await client.get(url, params=params, headers=headers)
    if response.status_code != 200:
        raise BotError(
            code=ErrorCode.DOWNLOAD_FAILED,
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

    if root.get("carousel_data"):
        carousel = root["carousel_data"]["carousel_slots"]
        carousel_data = []
        for carousel_element in carousel:
            image_url = carousel_element["images"]["736x"]["url"]
            carousel_data.append(image_url)
        ext = "carousel"

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

    elif isinstance(root.get("videos"), dict) and isinstance(
        root["videos"].get("video_list"), dict
    ):
        video_list = root["videos"]["video_list"]
        video = get_best_video(video_list)

        if video:
            ext = "mp4"

    elif (
        isinstance(root.get("images"), dict)
        and isinstance(root["images"].get("orig"), dict)
        and "url" in root["images"]["orig"]
    ):
        image = root["images"]["orig"]["url"]
        ext = "jpg"

    else:
        raise BotError(
            code=ErrorCode.DOWNLOAD_FAILED,
            message=f"Unknown Pinterest type. Pin id: {pin_id}",
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


async def download_photo(
    url: str,
    filename: str,
    client: httpx.AsyncClient,
) -> None:
    """Download a photo from Pinterest, trying original quality first."""
    try:
        content_url = re.sub(r"/\d+x", "/originals", url)

        async with client.stream("GET", content_url) as response:
            if response.status_code == 200:
                async with aiofiles.open(filename, "wb") as f:
                    async for chunk in response.aiter_bytes(1024):
                        await f.write(chunk)
                return

        if response.status_code == 403:
            async with client.stream("GET", url) as response:
                if response.status_code == 200:
                    async with aiofiles.open(filename, "wb") as f:
                        async for chunk in response.aiter_bytes(1024):
                            await f.write(chunk)
                    return
                else:
                    raise BotError(
                        code=ErrorCode.DOWNLOAD_FAILED,
                        message=f"Failed to retrieve image. Status code: {response.status_code}",
                        url=url,
                        is_logged=True
                    )
        else:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Failed to retrieve image. Status code: {response.status_code}",
                url=content_url,
                is_logged=True
            )

    except BotError:
        raise
    except Exception as e:
        raise BotError(
            code=ErrorCode.DOWNLOAD_FAILED,
            message=f"Failed to retrieve image: {url}. {e}",
            url=url,
            is_logged=True
        )


async def download_m3u8_video(url: str, filename: str) -> None:
    """Download m3u8 video stream using yt-dlp."""
    try:
        ydl_opts = {
            'outtmpl': filename,
            'quiet': True,
            'no_warnings': True,
        }
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await loop.run_in_executor(None, lambda: ydl.download([url]))
    except Exception as e:
        logger.error(f"Error downloading m3u8 video: {e}")
        raise BotError(
            code=ErrorCode.DOWNLOAD_FAILED,
            message=f"Failed to download M3U8 video: {e}",
            url=url,
            is_logged=True
        )
