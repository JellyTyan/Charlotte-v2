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
    ext = audio_file.lower().split('.')[-1]
    if ext not in ["mp3", "m4a", "mp4"]:
        logger.error(f"Unsupported audio format: {audio_file}")
        return

    try:
        if ext == "mp3":
            # Open the file to read and write metadata
            audio = MP3(audio_file, ID3=ID3)

            # Add or update title and artist
            audio["TIT2"] = TIT2(encoding=3, text=title)
            audio["TPE1"] = TPE1(encoding=3, text=artist)

            # If there's a cover, add it
            if cover_file:
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

        elif ext in ["m4a", "mp4"]:
            from mutagen.mp4 import MP4, MP4Cover

            audio = MP4(audio_file)
            audio["\xa9nam"] = title
            audio["\xa9ART"] = artist

            if cover_file:
                import os
                if not os.path.isfile(cover_file):
                    logger.error(f"Covr file not found: {cover_file}")
                else:
                     with open(cover_file, "rb") as img:
                        audio["covr"] = [
                            MP4Cover(img.read(), imageformat=MP4Cover.FORMAT_JPEG)
                        ]
            audio.save()

        logger.info(
            f"Metadata and file cover of {audio_file} have been successfully updated."
        )

    except Exception as e:
        logger.error(f"Error when updating metadata: {str(e)}")
