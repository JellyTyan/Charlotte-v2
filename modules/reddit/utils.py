import logging
import re
from curl_cffi.requests import AsyncSession
from models.errors import BotError, ErrorCode
from models.service_list import Services

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """Sanitize filename by removing invalid characters."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", filename)

async def get_post_info(url: str):
    """Get post information from URL."""
    async with AsyncSession(impersonate="chrome136") as session:
        # Remove query params, trailing slash, and any existing .json, then add .json?limit=1
        response = await session.get(url)
        clean_url = response.url.split('?')[0].rstrip('/')
        if clean_url.endswith('.json'):
            clean_url = clean_url[:-5]
        api_url = clean_url + '.json?limit=1'


        headers = {
            "Accept": "application/json, text/plain, */*",
        }

        response = await session.get(api_url, headers=headers)
        if response.status_code != 200:
            logger.error(f"Reddit API returned status {response.status_code} for {api_url}")
            raise BotError(ErrorCode.INTERNAL_ERROR, message="Invalid URL", service=Services.REDDIT, url=url, is_logged=True)

        data = response.json()
        if not data or not isinstance(data, list) or len(data) == 0:
            logger.error(f"Invalid Reddit response structure: {data}")
            raise BotError(ErrorCode.INTERNAL_ERROR, message="Invalid response", service=Services.REDDIT, url=url, is_logged=True)

        return data[0]["data"]["children"][0]["data"]
