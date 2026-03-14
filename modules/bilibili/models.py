from typing import Optional

from aiogram.filters.callback_data import CallbackData


class BilibiliCallback(CallbackData, prefix="bli"):
    type: str  # "video" or "audio"
    video_id: Optional[str] = None
    audio_id: Optional[str] = None
    url_hash: Optional[str] = None
