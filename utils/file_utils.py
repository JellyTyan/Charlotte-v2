import logging
import aiofiles.os
from typing import Optional

from mutagen.id3 import ID3
from mutagen.id3._frames import APIC, TIT2, TPE1
from mutagen.mp3 import MP3

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
            if await aiofiles.os.path.exists(filename):
                await aiofiles.os.remove(filename)
                deleted_files.append(filename)
                logger.info(f"Deleted file: {filename}")
            else:
                logger.warning(f"File not found: {filename}")
        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")

    return deleted_files


def update_metadata(
    audio_file: str, title: str, artist: str, cover_file: Optional[str]
) -> None:
    """
    Updates the MP3 file metadata and adds a cover art.

    :param audio_file: The path to the MP3 file.
    :param title: New title of the track.
    :param artist: New artist of the track.
    :param cover_file: Path to cover image (optional).
    :return: None
    """
    # Checking file extension
    if not audio_file.lower().endswith(".mp3"):
        logger.error(f"Файл {audio_file} не является MP3.")
        return

    try:
        # Open the file to read and write metadata
        audio = MP3(audio_file, ID3=ID3)

        # Add or update title and artist
        audio["TIT2"] = TIT2(encoding=3, text=title)
        audio["TPE1"] = TPE1(encoding=3, text=artist)

        # If there's a cover, add it
        if cover_file:
            # Validate cover file path to prevent path traversal
            import os
            if not os.path.isfile(cover_file) or ".." in cover_file:
                logger.error(f"Invalid cover file path: {cover_file}")
                return
            with open(cover_file, "rb") as img:
                audio.tags.add(
                    APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=img.read(),
                    )
                )

        audio.save()
        logger.info(
            f"Metadata and file cover of {audio_file} have been successfully updated."
        )

    except Exception as e:
        logger.error(f"Error when updating metadata: {str(e)}")
