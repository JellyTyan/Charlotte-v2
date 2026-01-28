import os
import aiofiles.os as aios

import asyncio
import logging
import mimetypes
from typing import Optional

from mutagen.mp3 import HeaderNotFoundError
from mutagen.id3 import ID3
from mutagen.id3._frames import TIT2, TPE1, TALB, TPE2, TRCK, TCON, APIC
from concurrent.futures import ThreadPoolExecutor
from mutagen.flac import FLAC, Picture

from mutagen.mp4 import MP4, MP4Cover, MP4Tags

logger = logging.getLogger(__name__)

update_executor = ThreadPoolExecutor(max_workers=10)


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

async def async_update_metadata(audio_file: str,
    title: Optional[str] = None,
    artist: Optional[str] = None,
    cover_file: Optional[str] = None,
    album_name: Optional[str] = None,
    orchestra_name: Optional[str] = None,
    track_number: Optional[str] = None,
    genre_name: Optional[str] = None
    ) -> None:
        """Updates the MP3 file metadata and adds a cover art."""
        loop = asyncio.get_event_loop()

        await loop.run_in_executor(
            update_executor,
            lambda: sync_update_metadata(
                audio_file=audio_file,
                title=title,
                artist=artist,
                cover_file=cover_file,
                album_name=album_name,
                orchestra_name=orchestra_name,
                track_number=track_number,
                genre_name=genre_name
                )
            )


def sync_update_metadata(
    audio_file: str,
    title: Optional[str],
    artist: Optional[str],
    cover_file: Optional[str],
    album_name: Optional[str],
    orchestra_name: Optional[str],
    track_number: Optional[str],
    genre_name: Optional[str]
) -> None:
    """
    Synchronous implementation of metadata update.
    WARNING: Do NOT use 'await' or 'aios' here. Use standard 'os'.
    """

    if not os.path.exists(audio_file):
        logger.error(f"Audio file not found: {audio_file}")
        return

    ext = audio_file.lower().split('.')[-1]

    # Читаем картинку один раз, если она есть
    cover_data = None
    mime_type = "image/jpeg"

    if cover_file:
        if os.path.exists(cover_file):
            mime_type, _ = mimetypes.guess_type(cover_file)
            if not mime_type: mime_type = "image/jpeg"

            try:
                with open(cover_file, "rb") as img:
                    cover_data = img.read()
            except Exception as e:
                logger.error(f"Failed to read cover: {e}")
        else:
            logger.error(f"Cover file not found: {cover_file}")

    try:
        # --- MP3 ---
        if ext == "mp3":
            try:
                tags = ID3(audio_file)
            except HeaderNotFoundError:
                tags = ID3()

            # ВАЖНО: Проверяем на None перед добавлением
            if title: tags.add(TIT2(encoding=3, text=title))
            if artist: tags.add(TPE1(encoding=3, text=artist))
            if album_name: tags.add(TALB(encoding=3, text=album_name))
            if orchestra_name: tags.add(TPE2(encoding=3, text=orchestra_name))
            if track_number: tags.add(TRCK(encoding=3, text=str(track_number)))
            if genre_name: tags.add(TCON(encoding=3, text=genre_name))

            if cover_data:
                tags.delall("APIC")
                tags.add(APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,
                    desc=u"Cover",
                    data=cover_data
                ))

            tags.save(audio_file, v2_version=3)

        # --- M4A / MP4 ---
        elif ext in ["m4a", "mp4"]:
            audio = MP4(audio_file)

            # MP4 использует атомы (©nam, ©ART и т.д.)
            if title: audio["\xa9nam"] = title
            if artist: audio["\xa9ART"] = artist
            if album_name: audio["\xa9alb"] = album_name
            if genre_name: audio["\xa9gen"] = genre_name
            # Номер трека в MP4 - это кортеж (номер, всего), требует int
            if track_number and track_number.isdigit():
                audio["trkn"] = [(int(track_number), 0)]

            if cover_data:
                # Нужно выбрать правильный формат для MP4 контейнера
                img_fmt = MP4Cover.FORMAT_PNG if "png" in mime_type else MP4Cover.FORMAT_JPEG
                audio["covr"] = [MP4Cover(cover_data, imageformat=img_fmt)]

            audio.save()

        # --- FLAC ---
        elif ext == "flac":
            audio = FLAC(audio_file)

            if title: audio["TITLE"] = title
            if artist: audio["ARTIST"] = artist
            if album_name: audio["ALBUM"] = album_name
            if genre_name: audio["GENRE"] = genre_name
            if track_number: audio["TRACKNUMBER"] = str(track_number)

            if cover_data:
                image = Picture()
                image.type = 3
                image.mime = mime_type
                image.desc = "Cover"
                image.data = cover_data

                # Удаляем старые картинки перед добавлением новой
                audio.clear_pictures()
                audio.add_picture(image)

            audio.save()

        logger.info(f"Metadata updated for {audio_file}")

    except Exception as e:
        logger.error(f"Error updating metadata for {audio_file}: {e}", exc_info=True)
