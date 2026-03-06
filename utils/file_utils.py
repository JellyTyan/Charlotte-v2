import logging
from pathlib import Path
from typing import Tuple

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


async def process_video_for_telegram(arq, video_path: str) -> Tuple[str, str, int, int, float]:
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
    result = await fix_job.result()

    width = result.get('width', 0)
    height = result.get('height', 0)
    duration = result.get('duration', 0.0)

    # Delete original video
    if await aios.path.exists(video_path):
        await aios.remove(video_path)

    return fixed_path, thumb_path, width, height, duration
