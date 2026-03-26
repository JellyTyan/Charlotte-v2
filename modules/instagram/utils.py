import json

import aiofiles
from curl_cffi.requests import AsyncSession
import re
from models.errors import BotError, ErrorCode
from models.service_list import Services
from utils import random_cookie_file


async def get_cookies():
    """
    Netscape cookies parsing
    """
    cookies_dict = {}

    file_path = random_cookie_file("instagram")

    async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
        async for line in f:
            if not line.strip() or line.startswith('#'):
                continue

            parts = line.strip().split('\t')

            if len(parts) >= 7:
                name = parts[5]
                value = parts[6].strip('"')

                cookies_dict[name] = value

    return cookies_dict, file_path


async def update_cookie_in_file(file_path: str, cookie_name: str, new_value: str):
    async with aiofiles.open(file_path, mode='r', encoding='utf-8') as f:
        lines = await f.readlines()

    updated_lines = []
    is_updated = False

    for line in lines:
        if not line.strip() or line.startswith('#'):
            updated_lines.append(line)
            continue

        parts = line.split('\t')

        if len(parts) >= 7 and parts[5] == cookie_name:
            parts[6] = f"{new_value}\n"
            updated_lines.append('\t'.join(parts))
            is_updated = True
        else:
            updated_lines.append(line)

    if is_updated:
        async with aiofiles.open(file_path, mode='w', encoding='utf-8') as f:
            await f.writelines(updated_lines)


async def get_start_page_tokens(session: AsyncSession, cookies: dict = None):
    url = 'https://www.instagram.com/?deoia=1'

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'ru-RU,ru;q=0.9',
        'dnt': '1',
        'dpr': '2',
        'priority': 'u=0, i',
        'referer': 'https://www.instagram.com/accounts/login/?next=%2F&source=mobile_nav',
        'viewport-width': '374'
    }

    response = await session.get(url, headers=headers, cookies=cookies)

    if response.status_code == 200:
        html = response.text

        fb_dtsg_match = re.search(r'"dtsg"\s*:\s*\{\s*"token"\s*:\s*"([^"]+)"', html)
        jazoest_match = re.search(r'jazoest=(\d+)', html)
        lsd_match = re.search(r'"LSD"\s*,\s*\[\s*\]\s*,\s*\{\s*"token"\s*:\s*"([^"]+)"\s*\}', html)
        spin_r_match = re.search(r'"__spin_r"\s*:\s*(\d+)', html)
        spin_t_match = re.search(r'"__spin_t"\s*:\s*(\d+)', html)
        bloks_match = re.search(
            r'"WebBloksVersioningID"\s*,\s*\[\s*\]\s*,\s*\{\s*"versioningID"\s*:\s*"([^"]+)"\s*\}',
            html)

        if not all([fb_dtsg_match, jazoest_match, lsd_match, spin_r_match, spin_t_match]):
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to fetch Instagram dynamic tokens: {response.status_code}",
                service=Services.INSTAGRAM,
                critical=True,
                is_logged=True
            )

        return {
            'fb_dtsg': fb_dtsg_match.group(1),
            'jazoest': jazoest_match.group(1),
            'lsd': lsd_match.group(1),
            '__spin_r': spin_r_match.group(1),
            '__spin_t': spin_t_match.group(1),
            'x-bloks-version-id': bloks_match.group(
                1) if bloks_match else 'd58190474cbf5a8ccd5ad03b16977e54f06642ba80140d245d37db165770bbf1'
        }
    else:
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to fetch Instagram page: {response.status_code}",
            service=Services.INSTAGRAM,
            critical=True,
            is_logged=True
        )


async def get_post_data(url: str):
    graphql_url = 'https://www.instagram.com/graphql/query'

    match = re.search(r"instagram\.com/p/([\w-]+)", url)

    if not match:
        raise BotError(
            code=ErrorCode.INVALID_URL,
            service=Services.INSTAGRAM,
            message="Invalid Instagram URL",
            critical=True,
            is_logged=True,
            url=url
        )
    shortcode = match.group(1)

    cookies, file_path = await get_cookies()

    async with AsyncSession(impersonate="chrome131_android") as session:
        dynamic_vars = await get_start_page_tokens(session, cookies)

        csrf_token = session.cookies.get('csrftoken', cookies['csrftoken'])

        if csrf_token != cookies['csrftoken']:
            await update_cookie_in_file(file_path, "csrftoken", csrf_token)
            cookies['csrftoken'] = csrf_token

        post_headers = {
            'accept': '*/*',
            'accept-language': 'ru-RU,ru;q=0.9',
            'content-type': 'application/x-www-form-urlencoded',
            'origin': 'https://www.instagram.com',
            'referer': f'https://www.instagram.com/p/{shortcode}/',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'x-asbd-id': '129477',  # Обычно статика
            'x-csrftoken': cookies["csrftoken"],
            'x-ig-app-id': '1217981644879628',  # Статика для Web Instagram
            'x-fb-friendly-name': 'PolarisPostRootQuery',
            'x-fb-lsd': dynamic_vars['lsd'],
            'x-bloks-version-id': dynamic_vars['x-bloks-version-id'],
        }

        data = {
            'av': cookies['ds_user_id'],
            '__d': 'www',
            '__user': '0',
            '__a': '1',
            '__req': '1',  # Начинаем с 1
            'fb_dtsg': dynamic_vars['fb_dtsg'],
            'jazoest': dynamic_vars['jazoest'],
            'lsd': dynamic_vars['lsd'],
            '__spin_r': dynamic_vars['__spin_r'],
            '__spin_b': 'trunk',
            '__spin_t': dynamic_vars['__spin_t'],
            'fb_api_caller_class': 'RelayModern',
            'fb_api_req_friendly_name': 'PolarisPostRootQuery',
            'server_timestamps': 'true',
            'doc_id': '25951076901259180',
            'variables': json.dumps({"shortcode": shortcode}),
            '__hs': '20537.HYP:instagram_web_pkg.2.1...0',
        }

        response_post = await session.post(graphql_url, headers=post_headers, data=data)

        post_data = {
            "shortcode": shortcode,
            "full_name": None,
            "username": None,
            "caption": None,
            "images": []
        }

        if response_post.status_code == 200:
            json_data = response_post.json()

            items = json_data.get("data", {}) \
                .get("xdt_api__v1__media__shortcode__web_info", {}) \
                .get("items", [])

            if not items:
                raise BotError(
                    code=ErrorCode.METADATA_ERROR,
                    message=f"Failed to fetch metadata for Instagram: {response_post.status_code}",
                    service=Services.INSTAGRAM,
                    critical=True,
                    is_logged=True,
                    url=url
                )

            item = items[0]

            user_info = item.get("user") or {}
            post_data["full_name"] = user_info.get("full_name")
            post_data["username"] = user_info.get("username")

            caption_info = item.get("caption") or {}
            post_data["caption"] = caption_info.get("text")

            post_data["media"] = []

            carousel_media = item.get("carousel_media")

            if carousel_media:
                for media in carousel_media:
                    video_versions = media.get("video_versions")
                    if video_versions:
                        post_data["media"].append(video_versions[0].get("url"))
                    else:
                        candidates = media.get("image_versions2", {}).get("candidates", [])
                        if candidates:
                            post_data["media"].append(candidates[0].get("url"))
            else:
                video_versions = item.get("video_versions")
                if video_versions:
                    post_data["media"].append(video_versions[0].get("url"))
                else:
                    candidates = item.get("image_versions2", {}).get("candidates", [])
                    if candidates:
                        post_data["media"].append(candidates[0].get("url"))

            return post_data

        else:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to fetch Instagram post data: {response_post.status_code}",
                service=Services.INSTAGRAM,
                critical=True,
                is_logged=True,
                url=url
            )
