import logging
from pathlib import Path
from typing import Tuple, Optional
import re
import unicodedata

import aiofiles.os as aios

logger = logging.getLogger(__name__)


async def delete_files(files=None):
    """
    Asynchronously deletes multiple files.

    :param files: List of filenames to delete. Defaults to None.
    :return: List of successfully deleted files.
    """
    if files is None:
        files = []

    deleted_files = []

    for filename in files:
        try:
            if await aios.path.exists(filename):
                await aios.remove(filename)
                deleted_files.append(filename)
                logger.info(f"Deleted file: {filename}")
            else:
                logger.warning(f"File not found: {filename}")
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")

    return deleted_files


async def process_video_for_telegram(arq, video_path: str) -> Tuple[str, Optional[str], int, int, float]:
    """
    Process video for Telegram: fix encoding, create thumbnail, get metadata.

    Args:
        arq: ARQ pool object
        video_path: Path to input video file

    Returns:
        Tuple of (fixed_video_path, thumbnail_path, width, height, duration)
    """

    video_path = str(video_path)
    path_obj = Path(video_path)
    fixed_path = str(path_obj.with_stem(f"{path_obj.stem}_fixed"))
    thumb_path = str(path_obj.with_suffix('.jpg'))

    # Fix video and create thumbnail in one call
    fix_job = await arq.enqueue_job(
        'universal_ffmpeg_process',
        input_file=video_path,
        output_file=fixed_path,
        operation='fix_video',
        options={'create_thumbnail': True, 'thumbnail_path': thumb_path},
        _queue_name='heavy'
    )
    try:
        result = await fix_job.result()
    except Exception as e:
        logger.error(f"Failed to process video with ffmpeg: {e}")
        # Return original video if processing fails, so at least something is sent.
        # We return 0/None for metadata as we couldn't extract it.
        return video_path, None, 0, 0, 0.0

    width = result.get('width', 0)
    height = result.get('height', 0)
    duration = result.get('duration', 0.0)

    # Delete original video
    if await aios.path.exists(video_path):
        await aios.remove(video_path)

    # Only return thumbnail path if the file was actually created
    actual_thumb = thumb_path if await aios.path.exists(thumb_path) else None

    return fixed_path, actual_thumb, width, height, duration


def sanitize_filename(s: str, restricted: bool = False, is_id: bool = False) -> str:
    if not s:
        return ""

    s = unicodedata.normalize('NFKC', str(s))

    if restricted:
        s = re.sub(r'[^\w\s\-\.]', '_', s)
    else:
        s = re.sub(r'[\<\>\:\"\/\\\|\?\*\0-\x1f]', '_', s)

    s = re.sub(r'[\r\n\t]+', ' ', s)

    if not is_id:
        s = re.sub(r'[_ ]+', ' ', s)
        s = s.strip(' _.-')

    return s if s else "_"


def compress_image_sync(file_path: str, max_size_bytes: int = 10 * 1024 * 1024) -> Optional[str]:
    """Compresses/resizes an image to fit Telegram limits (size < 10MB, sum of dimensions < 10000, aspect ratio < 20:1)."""
    import os
    from PIL import Image
    
    try:
        size_ok = os.path.getsize(file_path) <= max_size_bytes
        
        with Image.open(file_path) as img:
            w, h = img.size
            dims_ok = (w + h <= 9500) and (w / h <= 19.0) and (h / w <= 19.0)
            
            if size_ok and dims_ok:
                return file_path
                
            if img.mode != "RGB":
                img = img.convert("RGB")
                
            if w + h > 9500:
                factor = 9500 / (w + h)
                img = img.resize((int(w * factor), int(h * factor)), Image.Resampling.LANCZOS)
                
            w, h = img.size
            if w / h > 19.0:
                img = img.resize((int(19.0 * h), h), Image.Resampling.LANCZOS)
            elif h / w > 19.0:
                img = img.resize((w, int(19.0 * w)), Image.Resampling.LANCZOS)
                
            path_obj = Path(file_path)
            compressed_path = str(path_obj.with_stem(f"{path_obj.stem}_compressed").with_suffix(".jpg"))
            
            quality = 95
            while quality > 10:
                img.save(compressed_path, format="JPEG", quality=quality, optimize=True)
                if os.path.getsize(compressed_path) <= max_size_bytes:
                    return compressed_path
                quality -= 15
                
            if os.path.getsize(compressed_path) > max_size_bytes:
                w, h = img.size
                img = img.resize((int(w * 0.7), int(h * 0.7)), Image.Resampling.LANCZOS)
                img.save(compressed_path, format="JPEG", quality=60, optimize=True)
                return compressed_path
                
    except Exception as e:
        logger.error(f"Failed to compress image {file_path}: {e}")
        return None


def compress_image_bytes_sync(content: bytes, max_size_bytes: int = 10 * 1024 * 1024) -> Optional[bytes]:
    """Compresses/resizes image bytes to fit Telegram limits."""
    import io
    from PIL import Image
    
    try:
        size_ok = len(content) <= max_size_bytes
        
        with Image.open(io.BytesIO(content)) as img:
            w, h = img.size
            dims_ok = (w + h <= 9500) and (w / h <= 19.0) and (h / w <= 19.0)
            
            if size_ok and dims_ok:
                return content
                
            if img.mode != "RGB":
                img = img.convert("RGB")
                
            if w + h > 9500:
                factor = 9500 / (w + h)
                img = img.resize((int(w * factor), int(h * factor)), Image.Resampling.LANCZOS)
                
            w, h = img.size
            if w / h > 19.0:
                img = img.resize((int(19.0 * h), h), Image.Resampling.LANCZOS)
            elif h / w > 19.0:
                img = img.resize((w, int(19.0 * w)), Image.Resampling.LANCZOS)
                
            quality = 95
            while quality > 10:
                out = io.BytesIO()
                img.save(out, format="JPEG", quality=quality, optimize=True)
                if len(out.getvalue()) <= max_size_bytes:
                    return out.getvalue()
                quality -= 15
                
            out = io.BytesIO()
            w, h = img.size
            img = img.resize((int(w * 0.7), int(h * 0.7)), Image.Resampling.LANCZOS)
            img.save(out, format="JPEG", quality=60, optimize=True)
            return out.getvalue()
            
    except Exception as e:
        logger.error(f"Failed to compress image bytes: {e}")
        return None