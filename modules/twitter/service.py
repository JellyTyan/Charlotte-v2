import asyncio
import logging
import os
import re
from pathlib import Path
from typing import List, Optional

from curl_cffi.requests import AsyncSession

from core.config import Config
from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from modules.base_service import BaseService
from utils import truncate_string
from .utils import get_guest_token, get_tweet_info, sanitize_filename
from models.service_list import Services

logger = logging.getLogger(__name__)


class TwitterService(BaseService):
    name = "Twitter"

    def __init__(self, output_path: str = "storage/temp", arq = None) -> None:
        super().__init__()
        self.output_path = output_path
        self.auth = "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
        self.arq = arq

    async def download(self, url: str, premium: bool = False, config: Optional[Config] = None) -> List[MediaContent]:
        match = re.search(r"status/(\d+)", url)
        if not match:
            raise BotError(
                code=ErrorCode.INVALID_URL,
                message="Invalid Twitter URL",
                url=url,
                service=Services.TWITTER,
                is_logged=False,
                critical=False
            )

        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )

        tweet_id = int(match.group(1))

        headers = {
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        }

        async with AsyncSession(headers=headers, impersonate="chrome136") as client:
            csrf_token: Optional[str] = None
            auth_token: Optional[str] = None

            if premium:
                if not isinstance(config, Config):
                    logger.warning("Config object not provided for premium mode")
                elif config.TWITTER_CSRF_TOKEN and config.TWITTER_AUTH_TOKEN:
                    csrf_token = config.TWITTER_CSRF_TOKEN
                    auth_token = config.TWITTER_AUTH_TOKEN
                else:
                    raise BotError(
                        code=ErrorCode.SPONSORSHIP_ACTIVATE,
                        message="Premium mode requires Twitter CSRF and Auth tokens",
                        is_logged=False,
                        critical=False
                    )

            try:
                await client.get(url)

                guest_token = await get_guest_token(self.auth, client)

                tweet_dict = await get_tweet_info(
                    tweet_id,
                    self.auth,
                    guest_token,
                    client,
                    csrf_token=csrf_token,
                    auth_token=auth_token
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
                        message="Tweet is unavailable",
                        is_logged=False,
                        critical=False
                    )

                result_data = tweet_dict.get("data", {}).get("tweetResult", {}).get("result", {})

                # Check if media is blurred
                is_blurred = bool(result_data.get("mediaVisibilityResults"))

                # Handle different response structures (Tweet vs TweetWithVisibilityResults)
                if result_data.get("__typename") == "TweetWithVisibilityResults":
                    result_data = result_data.get("tweet", {})

                legacy = result_data.get("legacy", {})
                medias = legacy.get("extended_entities", {}).get("media", [])

                if not medias:
                    raise BotError(
                        code=ErrorCode.NOT_FOUND,
                        url=url,
                        message="No media found in tweet",
                        critical=False,
                        is_logged=False
                    )

                sensitive = legacy.get("possibly_sensitive", False) or is_blurred

                user_results = result_data.get("core", {}).get("user_results", {}).get("result", {})
                author = (
                    user_results.get("core", {}).get("name") or
                    user_results.get("legacy", {}).get("name") or
                    user_results.get("core", {}).get("screen_name") or
                    user_results.get("legacy", {}).get("screen_name") or
                    "Unknown"
                )

                title = legacy.get("full_text") or legacy.get("text") or "Twitter Media"

                result = []
                tasks = []

                for media in medias:
                    if media["type"] == "photo":
                        photo_url = media["media_url_https"]
                        match_photo = re.search(r"([^/]+\.(?:jpg|jpeg|png))", photo_url, re.IGNORECASE)
                        if not match_photo:
                            continue
                        filename = os.path.join(self.output_path, sanitize_filename(os.path.basename(photo_url)))
                        tasks.append(await self.arq.enqueue_job('universal_download', url=photo_url, destination=filename, _queue_name='light'))
                        result.append(MediaContent(
                            type=MediaType.PHOTO,
                            path=Path(filename),
                            title=truncate_string(f"{author} - {title}", 1024),
                            performer=author,
                            is_blured=sensitive
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
                        tasks.append(await self.arq.enqueue_job('universal_download', url=video_url, destination=filename, _queue_name='light'))
                        result.append(MediaContent(
                            type=MediaType.VIDEO,
                            path=Path(filename),
                            title=truncate_string(f"{author} - {title}", 1024),
                            performer=author,
                            is_blured=sensitive
                        ))

                    elif media["type"] == "animated_gif":
                        variant = media["video_info"]["variants"][0]
                        video_url = variant["url"]

                        match_gif = re.search(r"([^/]+\.mp4)", video_url)
                        if not match_gif:
                            continue
                        filename = os.path.join(self.output_path, match_gif.group(1))
                        tasks.append(await self.arq.enqueue_job('universal_download', url=video_url, destination=filename, _queue_name='light'))
                        result.append(MediaContent(
                            type=MediaType.GIF,
                            path=Path(filename),
                            title=truncate_string(f"{author} - {title}", 1024),
                            performer=author,
                            is_blured=sensitive
                        ))

                await asyncio.gather(*[job.result() for job in tasks], return_exceptions=True)

                return result

            except BotError as ebot:
                ebot.service = Services.TWITTER
                raise ebot
            except Exception as e:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message=str(e),
                    service=Services.TWITTER,
                    url=url,
                    is_logged=True,
                    critical=True
                )


    async def get_info(self, url: str) -> Optional[MediaMetadata]:
        return None
