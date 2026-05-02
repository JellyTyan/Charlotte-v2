import hashlib
import hmac
import logging
import re
import struct
import time
import urllib.parse

from curl_cffi.requests import AsyncSession

from models.errors import BotError, ErrorCode
from models.service_list import Services

logger = logging.getLogger(__name__)


def decode_secret(secret_str):
    t = 33
    n = 9
    r_arr = []
    for i, char in enumerate(secret_str):
        val = ord(char) ^ ((i % t) + n)
        r_arr.append(str(val))
    return "".join(r_arr).encode('utf-8')


def generate_hotp(secret_bytes, counter, digits=6):
    counter_bytes = struct.pack(">Q", counter)
    mac = hmac.new(secret_bytes, counter_bytes, hashlib.sha1).digest()
    offset = mac[-1] & 0x0F
    binary = struct.unpack(">I", mac[offset:offset+4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** digits)).zfill(digits)


def generate_totp(secret_bytes, timestamp_sec=None, period=30, digits=6):
    if timestamp_sec is None:
        timestamp_sec = time.time()
    counter = int(timestamp_sec // period)
    return generate_hotp(secret_bytes, counter, digits)


def get_totp_params():
    target_secret = ',7/*F("rLJ2oxaKL^f+E1xvP@N'
    secret_bytes = decode_secret(target_secret)
    current_ts = time.time()
    totp = generate_totp(secret_bytes, current_ts)
    return {
        "reason": "init",
        "productType": "web-player",
        "totp": totp,
        "totpServer": totp,
        "totpVer": "61"
    }


pattern = re.compile(
    r'new\s+\w+\.\w+\(\s*"([^"]+)"\s*,\s*"query"\s*,\s*"([a-f0-9]{64})"',
    re.IGNORECASE | re.DOTALL
)


def extract_hash(content: str, target_name: str) -> str | None:
    for name, hash_ in pattern.findall(content):
        if name == target_name:
            return hash_
    return None


async def get_access_token(session: AsyncSession) -> dict:
    """Получение токена доступа через браузерный API"""
    logger.debug("Requesting Spotify browser access token")
    
    try:
        await session.get("https://open.spotify.com/")
        
        totp_params = get_totp_params()
        query_string = urllib.parse.urlencode(totp_params)
        url = f"https://open.spotify.com/api/token?{query_string}"
        
        headers = {
            'accept': 'application/json',
            'referer': 'https://open.spotify.com/',
        }
        
        response = await session.get(url, headers=headers)
        
        if response.status_code != 200:
            logger.error(f"Failed to get Spotify token: {response.status_code}")
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to get token: {response.status_code}",
                service=Services.SPOTIFY,
                is_logged=True,
                critical=True,
            )
        
        data = response.json()
        access_token = data.get("accessToken")
        client_token = data.get("clientToken")
        
        if not access_token:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Access token not found in response",
                service=Services.SPOTIFY,
                is_logged=True,
                critical=True,
            )
        
        logger.debug("Spotify browser access token received")
        return {"access_token": access_token, "client_token": client_token}
        
    except BotError:
        raise
    except Exception as e:
        logger.error(f"Failed to get Spotify token: {e}")
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get token: {e}",
            service=Services.SPOTIFY,
            is_logged=True,
            critical=True,
        )


async def get_operation_hash(session: AsyncSession, operation_name: str) -> str:
    """Получение хэша операции из JS файла"""
    try:
        headers = {
            'accept': '*/*',
            'app-referer': 'https://open.spotify.com/',
        }
        response = await session.get(
            "https://open.spotifycdn.com/cdn/build/web-player/web-player.3cbcbc64.js",
            headers=headers
        )
        
        if response.status_code == 200:
            js_content = response.text
            hash_value = extract_hash(js_content, operation_name)
            if hash_value:
                return hash_value
        
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to extract hash for {operation_name}",
            service=Services.SPOTIFY,
            is_logged=True,
            critical=True,
        )
    except BotError:
        raise
    except Exception as e:
        logger.error(f"Failed to get operation hash: {e}")
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get operation hash: {e}",
            service=Services.SPOTIFY,
            is_logged=True,
            critical=True,
        )
