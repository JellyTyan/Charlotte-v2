import base64
import logging

import httpx

from models.errors import BotError, ErrorCode

TOKEN_URL = "https://accounts.spotify.com/api/token"

logger = logging.getLogger(__name__)


async def get_access_token(session: httpx.AsyncClient, spotify_client_id: str, spotify_secret: str) -> str:
    """Получение токена доступа через Client Credentials Flow"""
    logger.debug("Requesting Spotify access token")
    auth_header = base64.b64encode(
        f"{spotify_client_id}:{spotify_secret}".encode()
    ).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {"grant_type": "client_credentials"}

    response = await session.post(TOKEN_URL, headers=headers, data=data)

    if response.status_code != 200:
        logger.error(f"Failed to get Spotify token: {response.status_code}")
        logger.debug(f"Response details: {response.text}")
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to get token: {response.status_code}",
            is_logged=True,
            critical=True,
        )

    try:
        result = response.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON response: {e}")
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Invalid JSON response from Spotify",
            is_logged=True,
            critical=True,
        )
    
    logger.debug("Spotify access token received")
    if "access_token" not in result:
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            message="Access token not found in response",
            is_logged=True,
            critical=True,
        )
    return result["access_token"]
