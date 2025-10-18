"""Утилиты общего назначения"""

import re
from typing import Optional

def extract_video_id(url: str) -> Optional[str]:
    """Извлечение ID видео из URL"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)',
        r'youtube\.com/embed/([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None