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
        # Extract post ID from URL
        match = re.search(r'/comments/([a-z0-9]+)', url)
        if not match:
            raise BotError(ErrorCode.INTERNAL_ERROR, message="Invalid URL format", service=Services.REDDIT, url=url, is_logged=True)
        
        post_id = match.group(1)
        
        # Construct clean API URL using just the post ID
        api_url = f"https://www.reddit.com/comments/{post_id}.json?limit=1"

        headers = {
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://www.reddit.com/",
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
