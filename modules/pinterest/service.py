import asyncio
import logging
import os
import re
from pathlib import Path
from typing import List, Union

from aiofiles import os as aios

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from models.service_list import Services

from .utils import get_pin_info
from utils import escape_html, process_video_for_telegram, delete_files, sanitize_filename

logger = logging.getLogger(__name__)


class PinterestService:
    name = "Pinterest"

    def __init__(self, output_path: str = "storage/temp/", arq=None) -> None:
        self.output_path = output_path
        self.arq = arq


    async def get_info(self, url: str) -> MediaMetadata:
        return await get_pin_info(url)

    async def download(self, data: Union[str, MediaMetadata]) -> List[MediaContent]:
        if isinstance(data, str):
            metadata = await self.get_info(data)
            if not metadata:
                raise BotError(
                    code=ErrorCode.METADATA_ERROR,
                    message="Failed to fetch metadata",
                    url=data,
                    service=Services.PINTEREST,
                    is_logged=True,
                    critical=True
                )
            data = metadata

        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )

        media_type = data.media_type

        if media_type == "video":
            return await self._download_video(data)
        elif media_type == "gallery":
            return await self._download_carousel(data)
        elif media_type == "gif":
            return await self._download_gif(data)
        elif media_type == "photo":
            return await self._download_photo(data)
        else:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Unsupported file type: {media_type}",
                url=data.url,
                service=Services.PINTEREST,
                is_logged=True
            )

    async def _download_video(self, data: MediaMetadata) -> List[MediaContent]:
        result = []

        video = data.attachments[0]
        video_url = video.url
        image_signature = sanitize_filename(data.extra.get("image_signature", "pinterest"))
        filename = f"{image_signature}.mp4"
        filepath = os.path.join(self.output_path, filename)

        if video_url.endswith(".m3u8"):
            # Use yt-dlp for m3u8 streams
            job = await self.arq.enqueue_job(
                "universal_ytdlp_extract",
                video_url,
                extract_only=False,
                format_selector=None,
                output_template=filepath,
                _queue_name='heavy'
            )
            try:
                result_data = await job.result()
            except Exception as e:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    service=Services.PINTEREST,
                    message=f"Failed to download Pinterest video stream: {e}",
                    url=data.url,
                    critical=True,
                    is_logged=True
                )
            downloaded_path = result_data.get("filepath")
        else:
            # Direct download for regular mp4
            job = await self.arq.enqueue_job(
                "universal_download",
                video_url,
                filepath,
                _queue_name='light'
            )
            try:
                downloaded_path = await job.result()
            except Exception as e:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    service=Services.PINTEREST,
                    message=f"Failed to download Pinterest video: {e}",
                    url=data.url,
                    critical=True,
                    is_logged=True
                )

        if downloaded_path and await aios.path.exists(downloaded_path):
            fixed_video, thumbnail, width, height, duration = await process_video_for_telegram(self.arq,
                                                                                                downloaded_path)
            result.append(MediaContent(
                type=MediaType.VIDEO,
                path=Path(fixed_video),
                title=escape_html(data.title),
                cover=Path(thumbnail) if thumbnail else None,
                width=width,
                height=height,
                duration=int(duration)
            ))
        else:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message="Video file not found after download",
                url=data.url,
                service=Services.PINTEREST,
                is_logged=True
            )

        return result


    async def _download_carousel(self, data: MediaMetadata) -> List[MediaContent]:
        title = data.title
        image_signature = sanitize_filename(data.extra.get("image_signature", "pinterest"))

        async def download_single_image(i: int, image) -> MediaContent | None:
            original_url = re.sub(r"/\d+x", "/originals", image.url)
            file_ext = Path(original_url.split('?')[0]).suffix or '.jpg'
            filename = f"{image_signature}_{i}{file_ext}"
            filepath = os.path.join(self.output_path, filename)

            # Try original quality
            try:
                job = await self.arq.enqueue_job(
                    "universal_download",
                    original_url,
                    filepath,
                    _queue_name='light'
                )
                downloaded_path = await job.result()

                if downloaded_path and await aios.path.exists(downloaded_path):
                    # Convert only if not JPG/JPEG
                    if not downloaded_path.lower().endswith(('.jpg', '.jpeg')):
                        job = await self.arq.enqueue_job(
                            "convert_to_jpg",
                            downloaded_path,
                            _queue_name='light'
                        )
                        converted_img = await job.result()

                        if await aios.path.exists(converted_img):
                            await delete_files([downloaded_path])
                            downloaded_path = converted_img

                    return MediaContent(
                        type=MediaType.PHOTO,
                        path=Path(downloaded_path),
                        title=escape_html(title),
                    )
            except Exception as e:
                logger.warning(f"Original quality failed for carousel item {i}: {e}")

            # Fallback to standard quality
            try:
                job = await self.arq.enqueue_job(
                    "universal_download",
                    image.url,
                    filepath,
                    _queue_name='light'
                )
                downloaded_path = await job.result()

                if downloaded_path and await aios.path.exists(downloaded_path):
                    # Convert only if not JPG/JPEG
                    if not downloaded_path.lower().endswith(('.jpg', '.jpeg')):
                        job = await self.arq.enqueue_job(
                            "convert_to_jpg",
                            downloaded_path,
                            _queue_name='light'
                        )
                        converted_img = await job.result()

                        if await aios.path.exists(converted_img):
                            await delete_files([downloaded_path])
                            downloaded_path = converted_img

                    return MediaContent(
                        type=MediaType.PHOTO,
                        path=Path(downloaded_path),
                        title=escape_html(title),
                    )
            except Exception as e:
                logger.error(f"Failed to download carousel item {i}: {e}")
                return None

        tasks = [download_single_image(i, img) for i, img in enumerate(data.attachments)]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    async def _download_gif(self, data: MediaMetadata) -> List[MediaContent]:
        image_url = data.attachments[0].url
        image_signature = sanitize_filename(data.extra.get("image_signature", "pinterest"))
        filename = f"{image_signature}.gif"
        filepath = os.path.join(self.output_path, filename)

        job = await self.arq.enqueue_job(
            "universal_download",
            image_url,
            filepath,
            _queue_name='light'
        )
        try:
            downloaded_path = await job.result()
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                service=Services.PINTEREST,
                message=f"Failed to download Pinterest GIF: {e}",
                url=data.url,
                critical=True,
                is_logged=True
            )

        if not downloaded_path or not await aios.path.exists(downloaded_path):
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message="GIF file not found after download",
                url=data.url,
                service=Services.PINTEREST,
                is_logged=True
            )

        return [MediaContent(
            type=MediaType.GIF,
            path=Path(downloaded_path),
        )]

    async def _download_photo(self, data: MediaMetadata) -> List[MediaContent]:
        image_url = data.attachments[0].url
        title = data.title
        image_signature = sanitize_filename(data.extra.get("image_signature", "pinterest"))
        original_url = re.sub(r"/\d+x", "/originals", image_url)
        file_ext = Path(original_url.split('?')[0]).suffix or '.jpg'
        filename = f"{image_signature}{file_ext}"
        filepath = os.path.join(self.output_path, filename)

        # Try original quality
        try:
            job = await self.arq.enqueue_job(
                "universal_download",
                original_url,
                filepath,
                _queue_name='light'
            )
            downloaded_path = await job.result()

            if downloaded_path and await aios.path.exists(downloaded_path):
                # Convert only if not JPG/JPEG
                if not downloaded_path.lower().endswith(('.jpg', '.jpeg')):
                    job = await self.arq.enqueue_job(
                        "convert_to_jpg",
                        downloaded_path,
                        _queue_name='light'
                    )
                    converted_img = await job.result()

                    if await aios.path.exists(converted_img):
                        await delete_files([downloaded_path])
                        downloaded_path = converted_img

                return [MediaContent(
                    type=MediaType.PHOTO,
                    path=Path(downloaded_path),
                    title=escape_html(title),
                )]
        except Exception as e:
            logger.warning(f"Original quality failed: {e}")

        # Fallback to standard quality
        job = await self.arq.enqueue_job(
            "universal_download",
            image_url,
            filepath,
            _queue_name='light'
        )
        try:
            downloaded_path = await job.result()
        except Exception as e:
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                service=Services.PINTEREST,
                message=f"Failed to download Pinterest photo: {e}",
                url=data.url,
                critical=True,
                is_logged=True
            )

        if not downloaded_path or not await aios.path.exists(downloaded_path):
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message="Photo file not found after download",
                url=data.url,
                service=Services.PINTEREST,
                is_logged=True
            )

        # Convert only if not JPG/JPEG
        if not downloaded_path.lower().endswith(('.jpg', '.jpeg')):
            job = await self.arq.enqueue_job(
                "convert_to_jpg",
                downloaded_path,
                _queue_name='light'
            )
            converted_img = await job.result()

            if await aios.path.exists(converted_img):
                await delete_files([downloaded_path])
                downloaded_path = converted_img

        return [MediaContent(
            type=MediaType.PHOTO,
            path=Path(downloaded_path),
            title=escape_html(title),
        )]
