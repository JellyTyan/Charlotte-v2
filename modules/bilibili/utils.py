import logging

from typing import Union

logger = logging.getLogger(__name__)


def get_video_formats(formats_dict: list, max_size_mb: int = 50, duration: Union[int, float, None] = None):
    video_formats = []
    audio_formats = []

    max_bytes = max_size_mb * 1024 * 1024

    for f in formats_dict:
        vcodec = f.get("vcodec") or ""
        acodec = f.get("acodec") or ""
        # Bilibili has separate video and audio streams
        if vcodec != "none" and acodec == "none" and f.get("height"):
            video_formats.append(f)
        elif vcodec == "none" and acodec != "none":
            audio_formats.append(f)

    # Best audio for video+audio pairs
    best_audio_for_video = max(audio_formats, key=lambda f: f.get("abr") or 0, default=None)
    
    logger.info(
        f"Bilibili formats: {len(video_formats)} video, {len(audio_formats)} audio. "
        f"Best audio for video: {best_audio_for_video.get('format_id') if best_audio_for_video else 'none'}"
    )

    # Deduplicate video formats by resolution (pick the one with smallest size or hevc)
    # Sort video formats by height ascending, then filesize ascending
    def get_size(fmt):
        return fmt.get("filesize") or fmt.get("filesize_approx") or 0

    video_formats.sort(key=lambda x: (x.get("height", 0), get_size(x)))

    unique_video_formats = {}
    for v in video_formats:
        height = v.get("height")
        if height not in unique_video_formats:
            unique_video_formats[height] = v

    video_formats = list(unique_video_formats.values())

    # Build video+audio pairs
    all_pairs = []
    for v in reversed(video_formats): # Highest to lowest resolution
        height = v.get("height") or 0
        resolution = f"{height}p"

        v_size = get_size(v)
        a_size = get_size(best_audio_for_video) if best_audio_for_video else 0
        
        if v_size == 0 and duration:
            vbr = v.get("vbr") or v.get("tbr") or 0
            if vbr:
                v_size = int(duration * vbr * 1024 / 8)
        
        if a_size == 0 and best_audio_for_video and duration:
            abr = best_audio_for_video.get("abr") or 0
            if abr:
                a_size = int(duration * abr * 1024 / 8)
        
        total = v_size + a_size

        if total == 0 or total <= max_bytes:
            all_pairs.append({
                "video_format_id": v["format_id"],
                "audio_format_id": best_audio_for_video["format_id"] if best_audio_for_video else None,
                "resolution": resolution,
                "total_size_mb": round(total / (1024*1024), 2) if total > 0 else 0
            })

    # Find best standalone audio
    best_audio = None
    best_audio_score = -1

    for a in audio_formats:
        a_size = get_size(a)
        
        # Calculate size if not available
        if a_size == 0 and duration:
            abr = a.get("abr") or 0
            if abr:
                a_size = int(duration * abr * 1024 / 8)
        
        size_mb = a_size / (1024 * 1024) if a_size > 0 else 0
        if size_mb > max_size_mb:
            continue

        abr = a.get("abr", 0)
        score = abr

        if score > best_audio_score:
            best_audio_score = score
            best_audio = a

    result = {
        "formats": all_pairs,
        "best_audio": None
    }

    if best_audio:
        result["best_audio"] = {
            "format_id": best_audio["format_id"],
            "filesize": get_size(best_audio)
        }
        logger.info(f"Best standalone audio: {best_audio['format_id']}, {best_audio.get('abr', 0)}kbps")

    return result
