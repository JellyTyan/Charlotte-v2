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