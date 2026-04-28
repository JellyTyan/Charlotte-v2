from typing import Optional

from aiogram.filters.callback_data import CallbackData


class NicoVideoCallback(CallbackData, prefix="nv"):
    type: str  # "video" or "audio"
    video_id: Optional[str] = None
    audio_id: Optional[str] = None
    url_hash: Optional[str] = None
    resolution: Optional[str] = None
