import asyncio
import logging
import os
import re
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from modules.base_service import BaseService
from utils import truncate_string, process_video_for_telegram, escape_html
from models.service_list import Services
from .utils import get_post_data
from .account_manager import get_available_account, record_request, mark_account_banned

logger = logging.getLogger(__name__)


class InstagramService(BaseService):
    name = "Instagram"

    def __init__(self, output_path: str = "storage/temp", arq = None) -> None:
        super().__init__()
        self.output_path = output_path
        self.arq = arq

    async def download(self, url: str) -> List[MediaContent]:
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )
        try:
            if re.match(r"https?://(?:www\.)?instagram\.com/p/[\w-]+/?", url):
                return await self._download_post(url)
            elif re.match(r"https?://(?:www\.)?instagram\.com/reel(?:s)?/[\w-]+/?", url):
                return await self._download_video(url)
            else:
                raise BotError(
                    code=ErrorCode.INVALID_URL,
                    service=Services.INSTAGRAM,
                    message="Invalid Instagram URL",
                    url=url,
                    is_logged=False
                )

        except BotError as e:
            raise e
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Instagram error: {e}",
                url=url,
                is_logged=True,
            )

    async def _download_post(self, url: str) -> List[MediaContent]:
        post_data = await get_post_data(url)

        caption = post_data.get("caption", None)
        author_username = post_data.get("username", None)
        author_name = post_data.get("full_name", None)
        images = post_data.get("media", [])
        filenames = [
            f"{post_data.get('shortcode', i)}_{i}.{urlparse(img).path.split('.')[-1]}"
            for i, img in enumerate(images, start=1)
        ]

        download_tasks = []
        for link, name in zip(images, filenames):
            filepath = os.path.join(self.output_path, name)
            download_tasks.append(
                await self.arq.enqueue_job('universal_download', url=link, destination=filepath, _queue_name='light'))

        try:
            results = await asyncio.gather(*[job.result() for job in download_tasks], return_exceptions=True)
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                service=Services.INSTAGRAM,
                message=f"Failed to gather download results: {e}",
                url=url,
                is_logged=True
            )

        description = escape_html((caption or "").strip())

        display_name = author_name or author_username
        author_link = f"<a href='https://www.instagram.com/{author_username}/'>{display_name}</a>" if author_username else ""

        parts = [p for p in [author_link, description] if p]
        caption = " - ".join(parts)

        media_contents = []
        for i, res in enumerate(results):
            if isinstance(res, BaseException):
                logger.error(f"Error downloading instagram item {i}: {res}")
                continue

            if res and os.path.exists(str(res)):
                thumbnail = None
                path_obj = Path(res)
                ext = path_obj.suffix.lower()
                if ext == '.mp4':
                    fixed_video, thumbnail, width, height, duration = await process_video_for_telegram(self.arq, res)
                    path_obj = Path(fixed_video)
                    media_contents.append(MediaContent(
                        type=MediaType.VIDEO,
                        path=path_obj,
                        title=truncate_string(caption, 1024),
                        cover=Path(thumbnail),
                        width=width,
                        height=height,
                        duration=int(duration)
                    ))
                else:
                    media_contents.append(MediaContent(
                        type=MediaType.PHOTO,
                        path=path_obj,
                        title=truncate_string(caption, 1024)
                    ))

        if not media_contents:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                service=Services.INSTAGRAM,
                message="Failed to download any media files",
                url=url
            )

        return media_contents

    _YTDLP_BAN_SIGNALS = (
        "login required",
        "checkpoint required",
        "not logged in",
        "rate-limited",
        "please wait",
        "challenge required",
        "account suspended",
        "403",
        "401",
    )

    async def _download_video(self, url: str) -> List[MediaContent]:
        from .account_manager import MAX_REQUESTS_PER_MINUTE  # local import to avoid circular
        MAX_RETRIES = 3

        logger.info("yt-dlp reels download started: %s", url)
        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True,
            )

        last_error: Exception | None = None
        tried: list[str] = []

        for attempt in range(MAX_RETRIES):
            cookie_file = await get_available_account()
            account_name = os.path.basename(cookie_file) if cookie_file else "<no account>"

            if cookie_file:
                tried.append(account_name)
                await record_request(cookie_file)
                logger.info(
                    "[yt-dlp] [attempt %d/%d] Using account: %s",
                    attempt + 1, MAX_RETRIES, account_name,
                )
            else:
                logger.error(
                    "[yt-dlp] No available Instagram accounts after %d attempt(s). Tried: %s",
                    attempt, ", ".join(tried) if tried else "<none>",
                )
                break

            try:
                job = await self.arq.enqueue_job(
                    "universal_ytdlp_extract",
                    url,
                    extract_only=False,
                    format_selector=None,
                    output_template=f"{self.output_path}/%(id)s_%(title)s.%(ext)s",
                    cookies_file=cookie_file,
                    extra_opts={
                        "http_headers": {
                            "User-Agent": (
                                "Mozilla/5.0 (Linux; Android 13; SM-S901B) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/131.0.0.0 Mobile Safari/537.36"
                            ),
                            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                            "Sec-Ch-Ua-Mobile": "?1",
                            "Sec-Ch-Ua-Platform": '"Android"',
                        },
                        "merge_output_format": "mp4",
                    },
                    _queue_name="heavy",
                )
                result = await job.result()

            except Exception as e:
                err_lower = str(e).lower()
                if any(sig in err_lower for sig in self._YTDLP_BAN_SIGNALS):
                    logger.error(
                        "[yt-dlp] [%s] Ban/auth signal detected in error: %s. "
                        "Marking account as banned and rotating (attempt %d/%d).",
                        account_name, e, attempt + 1, MAX_RETRIES,
                    )
                    await mark_account_banned(cookie_file)
                    last_error = e
                    continue

                # Non-ban error — fail immediately
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    service=Services.INSTAGRAM,
                    message=f"yt-dlp download failed: {e}",
                    url=url,
                    critical=True,
                    is_logged=True,
                )

            # ── Successful download ───────────────────────────────────────────
            path = Path(result["filepath"])
            info = result["info"]

            title = info.get("title") or ""
            uploader = info.get("uploader")
            description = escape_html((info.get("description") or "").strip())
            username = title.split()[-1].strip(" @.") if title else None
            display_name = uploader or username
            author_link = (
                f"<a href='https://www.instagram.com/{username}/'>{display_name}</a>"
                if username else ""
            )
            parts = [p for p in [author_link, description] if p]
            caption = " - ".join(parts)

            if info.get("ext") == "mp4":
                fixed_video, thumbnail, width, height, duration = await process_video_for_telegram(
                    self.arq, str(path)
                )
                return [
                    MediaContent(
                        type=MediaType.VIDEO,
                        path=Path(fixed_video),
                        title=caption,
                        performer=username,
                        cover=Path(thumbnail) if thumbnail and os.path.exists(thumbnail) else None,
                        width=width,
                        height=height,
                        duration=int(duration),
                    )
                ]
            else:
                return [
                    MediaContent(
                        type=MediaType.PHOTO,
                        path=path,
                        title=caption,
                        performer=username,
                    )
                ]

        # All retries exhausted
        logger.error(
            "[yt-dlp] All %d account(s) failed for URL: %s. Tried: %s",
            MAX_RETRIES, url, ", ".join(tried),
        )
        raise BotError(
            code=ErrorCode.DOWNLOAD_FAILED,
            service=Services.INSTAGRAM,
            message=f"All Instagram accounts failed for yt-dlp download: {last_error}",
            url=url,
            critical=True,
            is_logged=True,
        )

    async def get_info(self, url: str) -> Optional[MediaMetadata]:
        return None
