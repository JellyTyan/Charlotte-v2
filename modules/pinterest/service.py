import logging
import os
import re
from pathlib import Path
from typing import List, Optional

try:
    from PIL import Image
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIC_SUPPORT = True
except ImportError:
    HEIC_SUPPORT = False

from aiofiles import os as aios

from models.errors import BotError, ErrorCode
from models.media import MediaContent, MediaType
from models.metadata import MediaMetadata
from modules.base_service import BaseService

from .utils import get_pin_info
from utils import escape_html

logger = logging.getLogger(__name__)


async def _convert_heic_to_jpg(heic_path: Path) -> Path:
    """Convert HEIC image to JPG format."""
    if not HEIC_SUPPORT:
        logger.warning("pillow_heif not available, cannot convert HEIC")
        return heic_path

    try:
        jpg_path = heic_path.with_suffix('.jpg')
        logger.debug(f"Converting HEIC to JPG: {heic_path} -> {jpg_path}")

        # Open and convert HEIC to JPG
        image = Image.open(heic_path)
        # Convert to RGB if necessary (HEIC can have alpha channel)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background
        elif image.mode != 'RGB':
            image = image.convert('RGB')

        # Save as JPG
        image.save(jpg_path, 'JPEG', quality=95, optimize=True)
        logger.info(f"HEIC converted successfully: {jpg_path}")

        # Delete original HEIC file
        if await aios.path.exists(heic_path):
            await aios.remove(heic_path)
            logger.debug(f"Removed original HEIC file: {heic_path}")

        return jpg_path
    except Exception as e:
        logger.error(f"Failed to convert HEIC to JPG: {e}")
        return heic_path


class PinterestService(BaseService):
    name = "Pinterest"

    def __init__(self, output_path: str = "storage/temp/", arq=None) -> None:
        super().__init__()
        self.output_path = output_path
        self.arq = arq

    async def download(self, url: str) -> List[MediaContent]:
        logger.debug(f"Starting Pinterest download for URL: {url}")

        if not self.arq:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="ARQ pool is required",
                critical=True,
                is_logged=True
            )

        try:
            # Get pin metadata
            logger.debug(f"Extracting pin info from URL: {url}")
            post_dict = await get_pin_info(url)

            image_signature = post_dict["image_signature"]
            title = post_dict["title"]
            ext = post_dict["ext"]

            logger.debug(f"Pin info extracted: signature={image_signature}, type={ext}")

            result = []

            # Handle video
            if ext == "mp4":
                video_url = post_dict["video"]
                filename = f"{image_signature}.mp4"
                filepath = os.path.join(self.output_path, filename)

                logger.debug(f"Downloading video from: {video_url}")

                if video_url.endswith(".m3u8"):
                    # Use yt-dlp for m3u8 streams
                    logger.debug("Using yt-dlp for m3u8 stream")
                    job = await self.arq.enqueue_job(
                        "universal_ytdlp_extract",
                        video_url,
                        extract_only=False,
                        format_selector=None,
                        output_template=filepath,
                        _queue_name='heavy'
                    )
                    result_data = await job.result()
                    downloaded_path = result_data.get("filepath")
                else:
                    # Direct download for regular mp4
                    logger.debug("Using direct download for mp4")
                    job = await self.arq.enqueue_job(
                        "universal_download",
                        video_url,
                        filepath,
                        _queue_name='light'
                    )
                    downloaded_path = await job.result()

                if downloaded_path and await aios.path.exists(downloaded_path):
                    logger.debug(f"Video downloaded successfully: {downloaded_path}")
                    result.append(MediaContent(
                        type=MediaType.VIDEO,
                        path=Path(downloaded_path),
                        title=escape_html(title),
                        original_size=True
                    ))
                else:
                    raise BotError(
                        code=ErrorCode.DOWNLOAD_FAILED,
                        message="Video file not found after download",
                        url=url,
                        is_logged=True
                    )

            # Handle carousel
            elif ext == "carousel":
                carousel_data = post_dict["carousel_data"]
                logger.debug(f"Downloading carousel with {len(carousel_data)} items")

                for i, image_url in enumerate(carousel_data):
                    # Try original quality first
                    original_url = re.sub(r"/\d+x", "/originals", image_url)

                    # Detect file extension from URL
                    file_ext = Path(original_url.split('?')[0]).suffix or '.jpg'
                    filename = f"{image_signature}_{i}{file_ext}"
                    filepath = os.path.join(self.output_path, filename)

                    downloaded = False
                    try:
                        # Try original quality
                        job = await self.arq.enqueue_job(
                            "universal_download",
                            original_url,
                            filepath,
                            _queue_name='light'
                        )
                        downloaded_path = await job.result()

                        if downloaded_path and await aios.path.exists(downloaded_path):
                            logger.debug(f"Carousel item {i} downloaded (original): {downloaded_path}")

                            # Convert HEIC to JPG if needed
                            final_path = Path(downloaded_path)
                            if final_path.suffix.lower() in ('.heic', '.heif'):
                                final_path = await _convert_heic_to_jpg(final_path)

                            result.append(MediaContent(
                                type=MediaType.PHOTO,
                                path=final_path,
                                title=escape_html(title),
                                original_size=True
                            ))
                            downloaded = True
                    except Exception as e:
                        logger.warning(f"Original quality failed for carousel item {i}: {e}")

                    # Fallback to standard quality if original failed
                    if not downloaded:
                        try:
                            job = await self.arq.enqueue_job(
                                "universal_download",
                                image_url,
                                filepath,
                                _queue_name='light'
                            )
                            downloaded_path = await job.result()

                            if downloaded_path and await aios.path.exists(downloaded_path):
                                logger.debug(f"Carousel item {i} downloaded (standard): {downloaded_path}")

                                # Convert HEIC to JPG if needed
                                final_path = Path(downloaded_path)
                                if final_path.suffix.lower() in ('.heic', '.heif'):
                                    final_path = await _convert_heic_to_jpg(final_path)

                                result.append(MediaContent(
                                    type=MediaType.PHOTO,
                                    path=final_path,
                                    title=escape_html(title),
                                    original_size=False
                                ))
                        except Exception as fallback_error:
                            logger.error(f"Failed to download carousel item {i}: {fallback_error}")
                            continue

            # Handle photo/GIF
            elif ext == "jpg":
                image_url = post_dict["image"]

                if image_url.endswith(".gif"):
                    logger.debug(f"Downloading GIF from: {image_url}")
                    filename = f"{image_signature}.gif"
                    filepath = os.path.join(self.output_path, filename)

                    job = await self.arq.enqueue_job(
                        "universal_download",
                        image_url,
                        filepath,
                        _queue_name='light'
                    )
                    downloaded_path = await job.result()

                    if downloaded_path and await aios.path.exists(downloaded_path):
                        logger.debug(f"GIF downloaded successfully: {downloaded_path}")
                        result.append(MediaContent(
                            type=MediaType.GIF,
                            path=Path(downloaded_path),
                            original_size=True
                        ))
                else:
                    # Try original quality first
                    original_url = re.sub(r"/\d+x", "/originals", image_url)
                    logger.debug(f"Downloading photo from: {original_url}")

                    # Detect file extension from URL
                    file_ext = Path(original_url.split('?')[0]).suffix or '.jpg'
                    filename = f"{image_signature}{file_ext}"
                    filepath = os.path.join(self.output_path, filename)

                    downloaded = False
                    try:
                        job = await self.arq.enqueue_job(
                            "universal_download",
                            original_url,
                            filepath,
                            _queue_name='light'
                        )
                        downloaded_path = await job.result()

                        if downloaded_path and await aios.path.exists(downloaded_path):
                            logger.debug(f"Photo downloaded successfully (original): {downloaded_path}")

                            # Convert HEIC to JPG if needed
                            final_path = Path(downloaded_path)
                            if final_path.suffix.lower() in ('.heic', '.heif'):
                                final_path = await _convert_heic_to_jpg(final_path)

                            result.append(MediaContent(
                                type=MediaType.PHOTO,
                                path=final_path,
                                title=escape_html(title),
                                original_size=True
                            ))
                            downloaded = True
                    except Exception as e:
                        logger.warning(f"Original quality failed: {e}")

                    # Fallback to standard quality if original failed
                    if not downloaded:
                        job = await self.arq.enqueue_job(
                            "universal_download",
                            image_url,
                            filepath,
                            _queue_name='light'
                        )
                        downloaded_path = await job.result()

                        if downloaded_path and await aios.path.exists(downloaded_path):
                            logger.debug(f"Photo downloaded successfully (standard): {downloaded_path}")

                            # Convert HEIC to JPG if needed
                            final_path = Path(downloaded_path)
                            if final_path.suffix.lower() in ('.heic', '.heif'):
                                final_path = await _convert_heic_to_jpg(final_path)

                            result.append(MediaContent(
                                type=MediaType.PHOTO,
                                path=final_path,
                                title=escape_html(title),
                                original_size=False
                            ))

            else:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message=f"Unsupported file type: {ext}",
                    url=url,
                    is_logged=True
                )

            if not result:
                raise BotError(
                    code=ErrorCode.DOWNLOAD_FAILED,
                    message="Failed to download any media files",
                    url=url,
                    is_logged=True
                )

            logger.debug(f"Pinterest download completed: {len(result)} items")
            return result

        except BotError:
            raise
        except Exception as e:
            logger.error(f"Error downloading Pinterest media: {str(e)}")
            raise BotError(
                code=ErrorCode.DOWNLOAD_FAILED,
                message=f"Pinterest download error: {str(e)}",
                url=url,
                is_logged=True
            )

    async def get_info(self, url: str) -> Optional[MediaMetadata]:
        return None
