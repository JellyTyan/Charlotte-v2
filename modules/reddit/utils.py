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
        response = await session.get(url, allow_redirects=True)

        final_url = str(response.url)

        match = re.match(r'(https://www\.reddit\.com/r/[^/]+/comments/[^/?]+(?:/[^/?]+)?)', url)
        if match:
            url = match.group(1)

        headers = {
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Referer": "https://www.reddit.com/",
        }

        response = await session.get(f"{final_url.rstrip('/')}.json?limit=1", headers=headers)
        if response.status_code != 200:
            raise BotError(ErrorCode.INTERNAL_ERROR, message="Invalid URL", service=Services.REDDIT, url=url, is_logged=True)

        return response.json()[0]["data"]["children"][0]["data"]
