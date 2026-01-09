
from urllib.parse import urlparse

ALLOWED_DOMAINS = [
    'youtube.com', 'youtu.be', 'ytimg.com',
    'tiktok.com', 'tiktokcdn.com',
    'instagram.com', 'cdninstagram.com',
    'twitter.com', 'twimg.com', 'x.com',
    'reddit.com', 'redd.it', 'redditmedia.com',
    'soundcloud.com', 'sndcdn.com',
    'spotify.com', 'scdn.co',
    'apple.com', 'mzstatic.com',
    'deezer.com', 'dzcdn.net',
    'pinterest.com', 'pinimg.com',
    'pixiv.net', 'pximg.net',
    'image-cdn-ak.spotifycdn.com'
]

def validate_url(url: str) -> bool:
    try:
        parsed = urlparse(url)

        if parsed.scheme not in ['http', 'https']:
            return False

        if parsed.hostname in ['localhost', '127.0.0.1', '0.0.0.0', '::1']:
            return False

        # if not any(allowed in (parsed.netloc or "") for allowed in ALLOWED_DOMAINS):
        #     return False

        return True
    except:
        return False
