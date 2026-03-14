from typing import Union

def format_duration(seconds: Union[int, float, None]) -> str:
    """Форматирует длительность в hh:mm:ss, mm:ss или ss"""
    if not seconds or seconds < 0:
        return "0:00"
    
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    elif minutes > 0:
        return f"{minutes}:{secs:02d}"
    else:
        return f"0:{secs:02d}"
