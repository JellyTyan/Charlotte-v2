import hashlib

def url_hash(url: str) -> str:
    """Создает короткий хеш для URL"""
    return hashlib.md5(url.encode()).hexdigest()[:8]