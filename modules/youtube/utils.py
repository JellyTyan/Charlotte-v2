from utils import random_cookie_file
import logging

logger = logging.getLogger(__name__)
def get_ytdlp_options():
    return {
        # "outtmpl": f"temp/%(id)s_{sanitize_filename('%(title)s')}.%(ext)s",
        "noplaylist": True,
        "cookiefile": random_cookie_file("youtube"),
        "geo_bypass": True,
        "age_limit": 99,
        "retries": 10,
        "restrictfilenames": True,
        "no_exec": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["tv", "web_safari", "web_embedded", "web"]
            },
            "youtubepot-bgutilhttp": {
                "base_url": ["http://bgutil:4416"]
            }
        }
    }


async def get_video_info(info_dict: dict, max_size_mb: int = 50) -> dict:
    title = info_dict.get("title", "Unknown Title")
    uploader = info_dict.get("uploader", "Unknown Uploader")
    thumbnail = info_dict.get("thumbnail", None)
    formats = info_dict.get("formats", [])

    video_formats = []
    audio_formats = []

    for f in formats:
        ext = f.get("ext", "")
        vcodec = f.get("vcodec", "") or "none"
        acodec = f.get("acodec", "") or "none"
        format_id = f.get("format_id", "")
        height = f.get("height", 0)

        if vcodec.startswith("avc1") and ext == "mp4" and acodec == "none" and height:
            video_formats.append(f)

        if vcodec == "none" and ext == "m4a" and acodec != "none":
            if "-drc" not in format_id.lower():
                audio_formats.append(f)

    def is_original_audio(fmt: dict) -> bool:
        search_string = f"{fmt.get('format_note', '')} {fmt.get('format', '')} {fmt.get('language', '')}".lower()
        return "original" in search_string

    explicit_original = [f for f in audio_formats if is_original_audio(f)]
    if explicit_original:
        audio_formats = explicit_original
        logger.info(f"Found {len(audio_formats)} explicit 'original' audio tracks.")

    video_formats.sort(key=lambda x: x.get("height", 0), reverse=True)
    audio_formats.sort(key=lambda x: x.get("abr", 0), reverse=True)

    max_bytes = max_size_mb * 1024 * 1024
    all_pairs = []
    added_resolutions = set()

    for v in video_formats:
        height = v.get("height")
        resolution = f"{height}p"

        if resolution in added_resolutions:
            continue

        v_size = v.get('filesize') or v.get('filesize_approx')

        for a in audio_formats:
            a_size = a.get('filesize') or a.get('filesize_approx')

            if v_size is None or a_size is None:
                logger.warning(f"Skipping pair v:{v.get('format_id')} a:{a.get('format_id')} due to unknown filesize.")
                continue

            total_bytes = v_size + a_size

            if total_bytes <= max_bytes:
                all_pairs.append({
                    "video_format_id": v["format_id"],
                    "audio_format_id": a["format_id"],
                    "resolution": resolution,
                    "total_size_mb": round(total_bytes / (1024 * 1024), 2)
                })
                added_resolutions.add(resolution)
                break

    best_audio = None
    if audio_formats:
        for a in audio_formats:
            a_size = a.get('filesize') or a.get('filesize_approx')
            if a_size and (a_size <= max_bytes):
                best_audio = a
                break

    all_pairs.sort(
        key=lambda x: (
            int(x["resolution"].replace("p", "")),
            -x["total_size_mb"]
        ),
        reverse=False
    )

    result = {
        "title": title,
        "uploader": uploader,
        "thumbnail": thumbnail,
        "formats": all_pairs,
        "best_audio": None
    }

    if best_audio:
        a_size = best_audio.get('filesize') or best_audio.get('filesize_approx') or 0
        result["best_audio"] = {
            "format_id": best_audio["format_id"],
            "filesize": round(a_size / (1024 * 1024), 2)
        }

    return result