from typing import Optional

from aiogram.filters.callback_data import CallbackData


class YoutubeCallback(CallbackData, prefix="yt"):
    type: str
    format_id: str
    audio_id: Optional[str] = None
    url_hash: Optional[str] = None
    sponsored: Optional[bool] = False
