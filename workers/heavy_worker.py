import asyncio
import json
import logging
import os
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List
import mimetypes

import yt_dlp
from arq.connections import RedisSettings
from mutagen.id3 import ID3
from mutagen.id3._frames import TIT2, TPE1, TALB, TPE2, TRCK, TCON, APIC
from mutagen.flac import FLAC, Picture
from mutagen.mp4 import MP4, MP4Cover, MP4Tags
from mutagen.mp3 import HeaderNotFoundError

logger = logging.getLogger(__name__)


# ============================================================================
# MEDIA EXTRACTION FUNCTIONS
# ============================================================================

async def universal_ytdlp_extract(
    ctx,
    url: str,
    extract_only: bool = True,
    format_selector: Optional[str] = None,
    output_template: Optional[str] = None,
    output_dir: Optional[str] = None,
    extract_audio: bool = False,
    audio_format: str = "mp3",
    audio_quality: str = "192",
    cookies_file: Optional[str] = None,
    extra_opts: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Extract info or download media using yt-dlp.

    Args:
        ctx: ARQ context
        url: Media URL
        extract_only: Only extract info without downloading
        format_selector: Format selector (e.g., 'bestvideo+bestaudio')
        output_template: Output filename template
        output_dir: Output directory
        extract_audio: Extract audio only
        audio_format: Audio format (mp3, m4a, etc.)
        audio_quality: Audio quality (0-9 or bitrate like '192k')
        cookies_file: Path to cookies file
        extra_opts: Additional yt-dlp options

    Returns:
        dict: {
            'info': info_dict,
            'filepath': str (if downloaded),
            'title': str,
            'duration': int,
            'thumbnail': str
        }
    """
    logger.info(f"yt-dlp processing: {url}")

    loop = asyncio.get_running_loop()

    def process():
        ydl_opts = {
            "quiet": False,
            "no_warnings": False,
            "extract_flat": False,
        }

        if cookies_file and os.path.exists(cookies_file):
            ydl_opts["cookiefile"] = cookies_file

        if not extract_only:
            if output_dir:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
                ydl_opts["paths"] = {"home": output_dir}

            if output_template:
                ydl_opts["outtmpl"] = output_template

            if format_selector:
                ydl_opts["format"] = format_selector

            if extract_audio:
                ydl_opts["format"] = "bestaudio/best"
                ydl_opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": audio_format,
                    "preferredquality": audio_quality,
                }]

        # Merge extra options
        if extra_opts:
            ydl_opts.update(extra_opts)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=not extract_only)

            result = {
                "info": info,
                "title": info.get("title"),
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
            }

            if not extract_only:
                filepath = ydl.prepare_filename(info)
                # Handle audio extraction filename change
                if extract_audio:
                    filepath = os.path.splitext(filepath)[0] + f".{audio_format}"
                result["filepath"] = filepath

            return result

    return await loop.run_in_executor(None, process)


async def universal_gallery_dl(
    ctx,
    url: str,
    output_dir: Optional[str] = None,
    options: Optional[Dict[str, str]] = None,
    extract_only: bool = False,
) -> Dict[str, Any]:
    """
    Extract info or download using gallery-dl.

    Args:
        ctx: ARQ context
        url: Media URL
        output_dir: Output directory
        options: Gallery-dl options as dict
        extract_only: Only extract info (--dump-json)

    Returns:
        dict: {
            'items': List[dict],  # Extracted items
            'files': List[str]  # Downloaded files (if not extract_only)
        }
    """
    logger.info(f"gallery-dl processing: {url}")

    loop = asyncio.get_running_loop()

    def process():
        cmd = ["gallery-dl"]

        if extract_only:
            cmd.append("--dump-json")

        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            cmd.extend(["--dest", output_dir])

        if options:
            for key, value in options.items():
                cmd.extend([f"--{key}", str(value)])

        cmd.append(url)

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"gallery-dl failed: {result.stderr}")

        items = []
        files = []

        if extract_only:
            # Parse JSON output (one JSON per line)
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        else:
            # Parse downloaded files from stdout
            for line in result.stdout.strip().split('\n'):
                if line and os.path.exists(line):
                    files.append(line)

        return {
            "items": items,
            "files": files,
        }

    return await loop.run_in_executor(None, process)


# ============================================================================
# MEDIA PROCESSING FUNCTIONS (FFmpeg)
# ============================================================================

async def universal_ffmpeg_process(
    ctx,
    input_file: str,
    output_file: str,
    operation: str,
    options: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Universal FFmpeg processing function.

    Args:
        ctx: ARQ context
        input_file: Input file path
        output_file: Output file path
        operation: Operation type (convert, extract_audio, thumbnail, concat, etc.)
        options: Operation-specific options

    Returns:
        str: Output file path
    """
    logger.info(f"FFmpeg {operation}: {input_file} -> {output_file}")

    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")

    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    loop = asyncio.get_running_loop()
    options = options or {}

    def process():
        if operation == "convert_audio":
            codec = options.get("codec", "libmp3lame")
            bitrate = options.get("bitrate", "192k")
            cmd = [
                "ffmpeg", "-i", input_file,
                "-vn", "-acodec", codec, "-b:a", bitrate,
                "-y", output_file
            ]

        elif operation == "convert_video":
            vcodec = options.get("vcodec", "libx264")
            acodec = options.get("acodec", "aac")
            preset = options.get("preset", "fast")
            crf = options.get("crf", "23")
            cmd = [
                "ffmpeg", "-i", input_file,
                "-c:v", vcodec, "-preset", preset, "-crf", str(crf),
                "-c:a", acodec,
                "-y", output_file
            ]

        elif operation == "extract_audio":
            acodec = options.get("codec", "copy")
            cmd = [
                "ffmpeg", "-i", input_file,
                "-vn", "-acodec", acodec,
                "-y", output_file
            ]

        elif operation == "create_thumbnail":
            timestamp = options.get("timestamp", "00:00:01")
            size = options.get("size", "320x180")
            cmd = [
                "ffmpeg", "-i", input_file,
                "-ss", timestamp, "-vframes", "1",
                "-s", size,
                "-y", output_file
            ]

        elif operation == "concat":
            # Expects options['files'] as list of files
            files = options.get("files", [])
            if not files:
                raise ValueError("concat operation requires 'files' list in options")

            # Create concat file
            concat_file = output_file + ".concat.txt"
            with open(concat_file, "w") as f:
                for file in files:
                    f.write(f"file '{file}'\n")

            cmd = [
                "ffmpeg", "-f", "concat", "-safe", "0",
                "-i", concat_file,
                "-c", "copy",
                "-y", output_file
            ]

        elif operation == "remux":
            # Remux without re-encoding
            cmd = [
                "ffmpeg", "-i", input_file,
                "-c", "copy",
                "-y", output_file
            ]

        elif operation == "add_thumbnail":
            # Add thumbnail to audio file
            thumbnail = options.get("thumbnail")
            if not thumbnail:
                raise ValueError("add_thumbnail requires 'thumbnail' option")

            cmd = [
                "ffmpeg", "-i", input_file, "-i", thumbnail,
                "-map", "0:0", "-map", "1:0",
                "-c", "copy", "-id3v2_version", "3",
                "-metadata:s:v", "title=Album cover",
                "-metadata:s:v", "comment=Cover (front)",
                "-y", output_file
            ]

        else:
            raise ValueError(f"Unknown operation: {operation}")

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise Exception(f"FFmpeg failed: {result.stderr}")

        # Clean up concat file if created
        if operation == "concat":
            concat_file = output_file + ".concat.txt"
            if os.path.exists(concat_file):
                os.remove(concat_file)

        return output_file

    return await loop.run_in_executor(None, process)


# async def universal_thumbnail_generate(
#     ctx,
#     input_file: str,
#     output_file: str,
#     size: tuple = (320, 180),
#     timestamp: Optional[str] = None,
#     quality: int = 85,
# ) -> str:
#     """
#     Generate thumbnail from video or resize image.

#     Args:
#         ctx: ARQ context
#         input_file: Input file (video or image)
#         output_file: Output thumbnail path
#         size: Thumbnail size (width, height)
#         timestamp: Timestamp for video (e.g., '00:00:01')
#         quality: JPEG quality (1-100)

#     Returns:
#         str: Thumbnail file path
#     """
#     logger.info(f"Generating thumbnail: {input_file}")

#     loop = asyncio.get_running_loop()
#     Path(output_file).parent.mkdir(parents=True, exist_ok=True)

#     def process():
#         # Check if input is video or image
#         input_ext = os.path.splitext(input_file)[1].lower()
#         video_exts = {'.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv'}

#         if input_ext in video_exts:
#             # Use FFmpeg for video
#             ts = timestamp or "00:00:01"
#             size_str = f"{size[0]}x{size[1]}"

#             cmd = [
#                 "ffmpeg", "-i", input_file,
#                 "-ss", ts, "-vframes", "1",
#                 "-s", size_str,
#                 "-y", output_file
#             ]

#             result = subprocess.run(cmd, capture_output=True, text=True)
#             if result.returncode != 0:
#                 raise Exception(f"FFmpeg thumbnail generation failed: {result.stderr}")
#         else:
#             # Use PIL for images
#             with Image.open(input_file) as img:
#                 img.thumbnail(size, Image.Resampling.LANCZOS)
#                 img.save(output_file, quality=quality, optimize=True)

#         return output_file

#     return await loop.run_in_executor(None, process)


# ============================================================================
# METADATA FUNCTIONS
# ============================================================================

async def universal_metadata_update(
    ctx,
    audio_file: str,
    title: Optional[str] = None,
    artist: Optional[str] = None,
    cover_file: Optional[str] = None,
    album_name: Optional[str] = None,
    orchestra_name: Optional[str] = None,
    track_number: Optional[str] = None,
    genre_name: Optional[str] = None
) -> bool:
    """
    Update metadata for audio files (MP3, FLAC, M4A, etc.).

    Args:
        ctx: ARQ context
        file_path: Audio file path
        metadata: Metadata dict (title, artist, album, date, etc.)
        cover_file: Optional cover art file path
        ...

    Returns:
        bool: Success status
    """
    logger.info(f"Updating metadata: {audio_file}")

    loop = asyncio.get_running_loop()

    def process():
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

    return await loop.run_in_executor(None, process)


# async def universal_metadata_extract(
#     ctx,
#     file_path: str,
# ) -> Dict[str, Any]:
#     """
#     Extract metadata from media files.

#     Args:
#         ctx: ARQ context
#         file_path: Media file path

#     Returns:
#         dict: Extracted metadata
#     """
#     logger.info(f"Extracting metadata: {file_path}")

#     loop = asyncio.get_running_loop()

#     def process():
#         try:
#             file_ext = os.path.splitext(file_path)[1].lower()
#             metadata = {}

#             if file_ext == ".mp3":
#                 audio = MP3(file_path, ID3=ID3)
#                 easy = EasyID3(file_path)

#                 for key in ["title", "artist", "album", "date", "genre"]:
#                     metadata[key] = easy.get(key, [""])[0]

#                 metadata["duration"] = audio.info.length
#                 metadata["bitrate"] = audio.info.bitrate
#                 metadata["sample_rate"] = audio.info.sample_rate

#             elif file_ext == ".flac":
#                 audio = FLAC(file_path)

#                 for key in ["title", "artist", "album", "date", "genre"]:
#                     metadata[key] = audio.get(key, [""])[0]

#                 metadata["duration"] = audio.info.length
#                 metadata["sample_rate"] = audio.info.sample_rate

#             else:
#                 logger.warning(f"Unsupported file type: {file_ext}")

#             return metadata

#         except Exception as e:
#             logger.error(f"Metadata extraction failed: {e}")
#             return {}

#     return await loop.run_in_executor(None, process)


# ============================================================================
# IMAGE PROCESSING FUNCTIONS
# ============================================================================

# async def universal_image_process(
#     ctx,
#     input_file: str,
#     output_file: str,
#     operation: str,
#     options: Optional[Dict[str, Any]] = None,
# ) -> str:
#     """
#     Universal image processing function.

#     Args:
#         ctx: ARQ context
#         input_file: Input image path
#         output_file: Output image path
#         operation: Operation (resize, convert, crop, rotate)
#         options: Operation-specific options

#     Returns:
#         str: Output file path
#     """
#     logger.info(f"Image processing {operation}: {input_file}")

#     loop = asyncio.get_running_loop()
#     options = options or {}
#     Path(output_file).parent.mkdir(parents=True, exist_ok=True)

#     def process():
#         with Image.open(input_file) as img:
#             if operation == "resize":
#                 size = options.get("size", (800, 600))
#                 method = options.get("method", "thumbnail")  # thumbnail or resize

#                 if method == "thumbnail":
#                     img.thumbnail(size, Image.Resampling.LANCZOS)
#                 else:
#                     img = img.resize(size, Image.Resampling.LANCZOS)

#             elif operation == "convert":
#                 # Format conversion handled by save
#                 pass

#             elif operation == "crop":
#                 box = options.get("box")  # (left, top, right, bottom)
#                 if box:
#                     img = img.crop(box)

#             elif operation == "rotate":
#                 angle = options.get("angle", 0)
#                 expand = options.get("expand", True)
#                 img = img.rotate(angle, expand=expand)

#             quality = options.get("quality", 85)
#             img.save(output_file, quality=quality, optimize=True)

#         return output_file

#     return await loop.run_in_executor(None, process)


# ============================================================================
# WORKER SETTINGS
# ============================================================================

class WorkerSettings:
    """ARQ heavy worker settings for blocking/CPU-intensive operations"""
    functions = [
        # Media extraction
        universal_ytdlp_extract,
        universal_gallery_dl,
        # Media processing
        universal_ffmpeg_process,
        # universal_thumbnail_generate,
        # Metadata
        universal_metadata_update,
        # universal_metadata_extract,
        # Image processing
        # universal_image_process,
    ]
    redis_settings = RedisSettings(host='redis', port=6379)
    queue_name = 'heavy'
