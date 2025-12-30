import asyncio
import logging
import os
import re
from pathlib import Path
from typing import List, Optional

import httpx

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from modules.base_service import BaseService
from utils import download_file, truncate_string
from .utils import get_guest_token, get_tweet_info, sanitize_filename

logger = logging.getLogger(__name__)


class TwitterService(BaseService):
    name = "Twitter"

    def __init__(self, output_path: str = "storage/temp/twitter") -> None:
        super().__init__()
        self.output_path = output_path
        os.makedirs(self.output_path, exist_ok=True)
        self.auth = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
        self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.guest_token = None
        self.headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'user-agent': self.user_agent,
        }
        self.request_counter = 0
        self.token_update_interval = 3

    async def download(self, url: str) -> List[MediaContent]:
        match = re.search(r"status/(\d+)", url)
        if not match:
            raise BotError(
                code=ErrorCode.INVALID_URL,
                message="Invalid Twitter URL",
                url=url
            )

        tweet_id = int(match.group(1))

        async with httpx.AsyncClient(follow_redirects=True, headers=self.headers) as client:
            try:
                await client.get(url)

                if self.guest_token is None:
                    self.guest_token = await get_guest_token(self.auth, client)

                tweet_dict = await get_tweet_info(
                    tweet_id,
                    self.auth,
                    self.user_agent,
                    self.guest_token,
                    client
                )

                status = tweet_dict.get("data", {}).get("tweetResult")

                if not status:
                    raise BotError(
                        code=ErrorCode.INVALID_URL,
                        url=url,
                        message="Tweet not found"
                    )

                status = status.get("result")

                if not status or status.get("__typename") == "TweetUnavailable":
                    raise BotError(
                        code=ErrorCode.INVALID_URL,
                        url=url,
                        message="Tweet is unavailable"
                    )

                medias = tweet_dict["data"]["tweetResult"]["result"]["legacy"].get("extended_entities", {}).get("media", [])

                if not medias:
                    raise BotError(
                        code=ErrorCode.DOWNLOAD_FAILED,
                        url=url,
                        message="No media found in tweet"
                    )

                result_data = tweet_dict.get("data", {}).get("tweetResult", {}).get("result", {})

                user_results = result_data.get("core", {}).get("user_results", {}).get("result", {})
                author = (
                    user_results.get("core", {}).get("name") or
                    user_results.get("core", {}).get("screen_name") or
                    user_results.get("legacy", {}).get("name") or
                    user_results.get("legacy", {}).get("screen_name") or
                    "Unknown"
                )

                title = result_data.get("legacy", {}).get("full_text") or \
                        result_data.get("legacy", {}).get("text") or \
                        "Twitter Media"

                result = []
                tasks = []

                for media in medias:
                    if media["type"] == "photo":
                        photo_url = media["media_url_https"]
                        match_photo = re.search(r"([^/]+\.(?:jpg|jpeg|png))", photo_url, re.IGNORECASE)
                        if not match_photo:
                            continue
                        filename = os.path.join(self.output_path, sanitize_filename(os.path.basename(photo_url)))
                        tasks.append(download_file(photo_url, filename, client=client))
                        result.append(MediaContent(
                            type=MediaType.PHOTO,
                            path=Path(filename),
                            title=truncate_string(f"{author} - {title}", 1024),
                            performer=author
                        ))

                    elif media["type"] == "video":
                        variants = media["video_info"]["variants"]

                        video_with_highest_bitrate = max(
                            (variant for variant in variants if "bitrate" in variant),
                            key=lambda x: x["bitrate"],
                        )

                        video_url = video_with_highest_bitrate["url"]

                        match_video = re.search(r"([^/]+\.mp4)", video_url)
                        if not match_video:
                            continue
                        filename = os.path.join(self.output_path, match_video.group(1))

                        tasks.append(download_file(video_url, filename, client=client))
                        result.append(MediaContent(
                            type=MediaType.VIDEO,
                            path=Path(filename),
                            title=truncate_string(f"{author} - {title}", 1024),
                            performer=author
                        ))

                    elif media["type"] == "animated_gif":
                        variant = media["video_info"]["variants"][0]
                        video_url = variant["url"]

                        match_gif = re.search(r"([^/]+\.mp4)", video_url)
                        if not match_gif:
                            continue
                        filename = os.path.join(self.output_path, match_gif.group(1))

                        tasks.append(download_file(video_url, filename, client=client))
                        result.append(MediaContent(
                            type=MediaType.GIF,
                            path=Path(filename),
                            title=truncate_string(f"{author} - {title}", 1024),
                            performer=author
                        ))

                await asyncio.gather(*tasks)

                return result

            except BotError:
                raise
            except Exception as e:
                logger.error(f"Error downloading Twitter media: {str(e)}")
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message=str(e),
                    url=url,
                    is_logged=True
                )



    async def get_info(self, url: str) -> Optional[MediaMetadata]:
        return None
