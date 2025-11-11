def truncate_string(text: str, max_length: int = 1024) -> str:
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."
