import logging
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