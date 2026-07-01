from aiogram.filters.callback_data import CallbackData


class YoutubeMenuCallback(CallbackData, prefix="yt_menu"):
    action: str  # "toggle_trim", "download_simple", "cancel"
    format: str  # "video" or "audio"
    trim: bool   # True if trim is toggled on


class YoutubeQualityCallback(CallbackData, prefix="yt_qual"):
    height: int
    size_mb: float
    label: str
