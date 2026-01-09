import os
import random
from yt_dlp.utils import sanitize_filename


def random_cookie_file():
    try:
        cookie_dir = "storage/cookies/youtube"
        if not os.path.exists(cookie_dir):
            return None

        cookie_files = [f for f in os.listdir(cookie_dir) if f.endswith('.txt')]
        return f"{cookie_dir}/{random.choice(cookie_files)}" if cookie_files else None
    except (OSError, IndexError):
        return None


def get_ytdlp_options():
    return {
        "outtmpl": f"temp/%(id)s_{sanitize_filename('%(title)s')}.%(ext)s",
        "noplaylist": True,
        "cookiefile": random_cookie_file(),
        "geo_bypass": True,
        "age_limit": 99,
        "retries": 10,
        "restrictfilenames": True,
        "no_exec": True,
        "allowed_extractors": ["youtube", "youtubetab"],
        "extractor_args": {
            "youtube": {
                "player_client": ["tv", "web_safari", "web_embedded", "ios"]
            },
            "youtubepot-bgutilhttp": {
                "base_url": ["http://bgutil:4416"]
            }
        }
    }


async def  get_video_info(info_dict: dict, max_size_mb: int = 50) -> dict:
        import logging
        logger = logging.getLogger(__name__)

        title = info_dict.get("title", "Unknown Title")
        uploader = info_dict.get("uploader", "Unknown Uploader")
        thumbnail = info_dict.get("thumbnail", None)
        formats = info_dict.get("formats", [])

        allowed_resolutions = ["2160p", "2160p60", "1440p", "1440p60", "1080p", "1080p60", "720p", "720p60", "480p", "360p", "240p", "144p"]

        video_formats = []
        audio_formats = []
        for f in formats:
            ext = f.get("ext", "")
            vcodec = f.get("vcodec", "") or ""
            acodec = f.get("acodec", "") or ""
            format_note = f.get("format_note") or ""

            if not format_note and f.get("height"):
                format_note = f["height"] and f"{f['height']}p"

            if format_note in allowed_resolutions \
                    and vcodec.startswith("avc1") and ext == "mp4" and acodec == "none":
                video_formats.append(f)

            # Select all m4a audio formats
            if vcodec == "none" and acodec and ext == "m4a":
                audio_formats.append(f)

        logger.info(f"Available audio formats: {[a.get('format_id') for a in audio_formats]}")

        max_bytes = max_size_mb * 1024 * 1024
        all_pairs = []
        added_resolutions = set()

        for v in video_formats:
            resolution = v.get("format_note") or f"{v.get('height')}p"
            if resolution in added_resolutions:
                continue
            v_size = v.get('filesize') or v.get('filesize_approx') or 0

            for a in audio_formats:
                a_size = a.get('filesize') or a.get('filesize_approx') or 0
                total = v_size + a_size
                if total <= max_bytes:
                    all_pairs.append({
                        "video_format_id": v["format_id"],
                        "audio_format_id": a["format_id"],
                        "resolution": resolution,
                        "total_size_mb": round(total / (1024*1024), 2)
                    })
                    added_resolutions.add(resolution)
                    break

        best_audio = None
        best_audio_score = -1

        # First pass: try to find original audio
        for a in audio_formats:
            format_note = (a.get('format_note') or '').lower()
            if 'original' in format_note:
                a_size = a.get('filesize') or a.get('filesize_approx') or 0
                size_mb = a_size / (1024 * 1024)
                abr = a.get("abr", 0)

                if size_mb <= max_size_mb and abr > best_audio_score:
                    best_audio_score = abr
                    best_audio = a

        # Second pass: if no original found, take best available
        if not best_audio:
            for a in audio_formats:
                a_size = a.get('filesize') or a.get('filesize_approx') or 0
                size_mb = a_size / (1024 * 1024)
                abr = a.get("abr", 0)

                if size_mb <= max_size_mb and abr > best_audio_score:
                    best_audio_score = abr
                    best_audio = a

        result = {
            "title": title,
            "uploader": uploader,
            "thumbnail": thumbnail,
            "formats": all_pairs,
            "best_audio": None
        }

        if best_audio:
            result["best_audio"] = {
                "format_id": best_audio["format_id"],
                "filesize": best_audio.get("filesize") or best_audio.get("filesize_approx") or 0
            }

        return result
