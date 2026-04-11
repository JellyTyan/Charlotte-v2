import asyncio
import html
import json
import logging
import os
import random
import re

import aiofiles
from curl_cffi.requests import AsyncSession
from curl_cffi.requests.exceptions import TooManyRedirects

from models.errors import BotError, ErrorCode
from models.service_list import Services
from storage.cache.redis_client import cache_get, cache_set
from .account_manager import get_available_account, record_request, mark_account_banned

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────

POST_CACHE_TTL = 86400          # 24 hours
MAX_ACCOUNT_RETRIES = 3         # how many different accounts to try per request

# Headers that a real Chrome 131 on Android generates
_CHROME131_ANDROID_UA = (
    "Mozilla/5.0 (Linux; Android 13; SM-S901B) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Mobile Safari/537.36"
)
_SEC_CH_UA = '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"'
_SEC_CH_UA_MOBILE = "?1"
_SEC_CH_UA_PLATFORM = '"Android"'

# ── Cookie helpers ─────────────────────────────────────────────────────────────

async def get_cookies(cookie_file: str):
    """Parse a Netscape-format cookie file and return (dict, filepath)."""
    cookies_dict = {}
    async with aiofiles.open(cookie_file, mode="r", encoding="utf-8") as f:
        async for line in f:
            if not line.strip() or line.startswith("#"):
                continue
            parts = line.strip().split("\t")
            if len(parts) >= 7:
                name = parts[5]
                value = parts[6].strip('"')
                value = html.unescape(value)
                cookies_dict[name] = value

    account_name = os.path.basename(cookie_file)
    logger.debug(
        "[%s] Loaded %d cookies from file: %s",
        account_name,
        len(cookies_dict),
        ", ".join(cookies_dict.keys()) if cookies_dict else "<none>",
    )

    _KEY_COOKIES = ("sessionid", "csrftoken", "ds_user_id", "rur", "mid")
    for name in _KEY_COOKIES:
        if name in cookies_dict:
            val = cookies_dict[name]
            masked = val[:4] + "*" * max(0, len(val) - 8) + val[-4:] if len(val) > 8 else "****"
            logger.debug("[%s] Cookie %-12s = %s", account_name, name, masked)
        else:
            logger.debug("[%s] Cookie %-12s = <missing>", account_name, name)

    return cookies_dict, cookie_file


async def update_cookie_in_file(file_path: str, cookie_name: str, new_value: str):
    async with aiofiles.open(file_path, mode="r", encoding="utf-8") as f:
        lines = await f.readlines()

    updated_lines = []
    is_updated = False
    for line in lines:
        if not line.strip() or line.startswith("#"):
            updated_lines.append(line)
            continue
        parts = line.split("\t")
        if len(parts) >= 7 and parts[5] == cookie_name:
            parts[6] = f"{new_value}\n"
            updated_lines.append("\t".join(parts))
            is_updated = True
        else:
            updated_lines.append(line)

    if is_updated:
        async with aiofiles.open(file_path, mode="w", encoding="utf-8") as f:
            await f.writelines(updated_lines)


# ── Start-page token extraction ────────────────────────────────────────────────

async def get_start_page_tokens(session: AsyncSession, cookies: dict | None = None):
    url = "https://www.instagram.com/?deoia=1"

    headers = {
        "accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
            "application/signed-exchange;v=b3;q=0.7"
        ),
        "accept-language": "en-US,en;q=0.9",
        "dnt": "1",
        "dpr": "2",
        "priority": "u=0, i",
        "referer": "https://www.instagram.com/accounts/login/?next=%2F&source=mobile_nav",
        "sec-ch-ua": _SEC_CH_UA,
        "sec-ch-ua-mobile": _SEC_CH_UA_MOBILE,
        "sec-ch-ua-platform": _SEC_CH_UA_PLATFORM,
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "user-agent": _CHROME131_ANDROID_UA,
        "viewport-width": "412",
    }

    # Small random delay before hitting Instagram
    await asyncio.sleep(random.uniform(0.3, 0.8))

    try:
        response = await session.get(url, headers=headers, cookies=cookies, max_redirects=10)
    except TooManyRedirects:
        logger.error(
            "Instagram returned too many redirects — account likely banned/logged-out. "
            "Will mark account as banned and rotate to next cookie."
        )
        raise BotError(
            code=ErrorCode.ACCOUNT_BANNED,
            message="Instagram account banned/logged-out: too many redirects",
            service=Services.INSTAGRAM,
            is_logged=True,
        )

    if response.status_code == 200:
        html = response.text

        fb_dtsg_match  = (
            re.search(r'"DTSGInitialData"\s*,\s*\[\]\s*,\s*\{"token"\s*:\s*"([^"]+)"', html)
            or re.search(r'"DTSGInitData"\s*,\s*\[\]\s*,\s*\{"token"\s*:\s*"([^"]+)"', html)
            or re.search(r'"dtsg"\s*:\s*\{\s*"token"\s*:\s*"([^"]+)"', html)  # legacy fallback
        )
        jazoest_match  = re.search(r"jazoest=(\d+)", html)
        lsd_match      = re.search(r'"LSD"\s*,\s*\[\s*\]\s*,\s*\{\s*"token"\s*:\s*"([^"]+)"\s*\}', html)
        spin_r_match   = re.search(r'"__spin_r"\s*:\s*(\d+)', html)
        spin_t_match   = re.search(r'"__spin_t"\s*:\s*(\d+)', html)
        bloks_match    = re.search(
            r'"WebBloksVersioningID"\s*,\s*\[\s*\]\s*,\s*\{\s*"versioningID"\s*:\s*"([^"]+)"\s*\}',
            html,
        )

        if not all([fb_dtsg_match, jazoest_match, lsd_match, spin_r_match, spin_t_match]):
            token_status = {
                "fb_dtsg":   bool(fb_dtsg_match),
                "jazoest":   bool(jazoest_match),
                "lsd":       bool(lsd_match),
                "__spin_r":  bool(spin_r_match),
                "__spin_t":  bool(spin_t_match),
            }
            missing_tokens = [k for k, v in token_status.items() if not v]
            logger.error(
                "Failed to extract Instagram tokens. Missing: %s | Found: %s",
                ", ".join(missing_tokens),
                ", ".join(k for k, v in token_status.items() if v) or "<none>",
            )

            _BAN_SIGNALS = {
                "login_required":  "login_required",
                "checkpoint_url":  '"checkpoint_url"',
                "not_logged_in":   "not_logged_in",
                "onetap_login":    "OneTapLoginPage",
                "spam_signal":     '"spam"',
                "rate_limited":    "Please wait a few minutes",
                "consent_page":    "ConsentPage",
                "age_gate":        "ageGate",
            }
            detected = [label for label, signal in _BAN_SIGNALS.items() if signal in html]
            if detected:
                logger.error(
                    "Instagram account appears banned/logged-out — signals detected: %s. "
                    "Will mark account as banned and rotate to next cookie.",
                    ", ".join(detected),
                )
                raise BotError(
                    code=ErrorCode.ACCOUNT_BANNED,
                    message=f"Instagram account banned/logged-out: {', '.join(detected)}",
                    service=Services.INSTAGRAM,
                    is_logged=True,
                )
            else:
                logger.warning(
                    "Instagram start-page: tokens missing but no ban signals detected — "
                    "page structure may have changed."
                )
                raise BotError(
                    code=ErrorCode.INTERNAL_ERROR,
                    message=f"Failed to fetch Instagram dynamic tokens: {response.status_code}",
                    service=Services.INSTAGRAM,
                    critical=True,
                    is_logged=True,
                )

        assert fb_dtsg_match and jazoest_match and lsd_match and spin_r_match and spin_t_match
        return {
            "fb_dtsg":            fb_dtsg_match.group(1),
            "jazoest":            jazoest_match.group(1),
            "lsd":                lsd_match.group(1),
            "__spin_r":           spin_r_match.group(1),
            "__spin_t":           spin_t_match.group(1),
            "x-bloks-version-id": bloks_match.group(1) if bloks_match
                                  else "d58190474cbf5a8ccd5ad03b16977e54f06642ba80140d245d37db165770bbf1",
        }
    else:
        raise BotError(
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Failed to fetch Instagram page: {response.status_code}",
            service=Services.INSTAGRAM,
            critical=True,
            is_logged=True,
        )


def _detect_ban_response(response) -> bool:
    """
    Return True if Instagram is telling us the account is blocked/limited.
    Covers HTTP status codes and JSON challenge flags.
    """
    if response.status_code in (401, 403):
        return True

    # Some bans come back as 200 with a login/checkpoint body
    try:
        body = response.text
        if any(signal in body for signal in (
            '"checkpoint_url"',
            "login_required",
            '"spam"',
            "Please wait a few minutes",
        )):
            return True
    except Exception:
        pass

    return False


# ── Main public function ───────────────────────────────────────────────────────

async def get_post_data(url: str):
    graphql_url = "https://www.instagram.com/graphql/query"

    match = re.search(r"instagram\.com/p/([\w-]+)", url)
    if not match:
        raise BotError(
            code=ErrorCode.INVALID_URL,
            service=Services.INSTAGRAM,
            message="Invalid Instagram URL",
            critical=True,
            is_logged=True,
            url=url,
        )
    shortcode = match.group(1)

    # ── 1. Redis cache hit ────────────────────────────────────────────────────
    cache_key = f"ig:post:{shortcode}"
    cached = await cache_get(cache_key)
    if cached:
        logger.info("Instagram post cache hit: %s", shortcode)
        return cached

    # ── 2. Try accounts with retry ────────────────────────────────────────────
    last_error = None
    tried: list[str] = []

    for attempt in range(MAX_ACCOUNT_RETRIES):
        cookie_file = await get_available_account()
        if not cookie_file:
            logger.error(
                "No available Instagram accounts after %d attempt(s). "
                "Tried: %s",
                attempt,
                ", ".join(tried) if tried else "<none>",
            )
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message="No available Instagram accounts (all banned or rate-limited)",
                service=Services.INSTAGRAM,
                critical=True,
                is_logged=True,
                url=url,
            )

        account_name = os.path.basename(cookie_file)
        tried.append(account_name)
        logger.info(
            "[attempt %d/%d] Using account: %s",
            attempt + 1, MAX_ACCOUNT_RETRIES, account_name,
        )

        try:
            post_data = await _fetch_post_data(
                graphql_url, url, shortcode, cookie_file
            )
            # ── 3. Store in Redis ─────────────────────────────────────────────
            await cache_set(cache_key, post_data, ttl=POST_CACHE_TTL)
            logger.info("Instagram post cached: %s", shortcode)
            return post_data

        except BotError as e:
            if e.code == ErrorCode.ACCOUNT_BANNED:
                logger.error(
                    "[%s] Account banned/rate-limited — reason: %s. "
                    "Marking as banned and rotating (attempt %d/%d).",
                    account_name, e.message, attempt + 1, MAX_ACCOUNT_RETRIES,
                )
                await mark_account_banned(cookie_file)
                last_error = e
                continue
            raise

    # All attempts exhausted
    logger.error(
        "All %d Instagram account(s) failed for shortcode=%s. Tried: %s",
        MAX_ACCOUNT_RETRIES, shortcode, ", ".join(tried),
    )
    raise last_error or BotError(
        code=ErrorCode.INTERNAL_ERROR,
        message="All Instagram accounts failed",
        service=Services.INSTAGRAM,
        critical=True,
        is_logged=True,
        url=url,
    )


async def _fetch_post_data(graphql_url: str, url: str, shortcode: str, cookie_file: str) -> dict:
    """Make the actual Instagram GraphQL request using a given cookie file."""
    account_name = os.path.basename(cookie_file)
    logger.info("[%s] Starting fetch for shortcode=%s", account_name, shortcode)

    cookies, file_path = await get_cookies(cookie_file)

    _REQUIRED = ("sessionid", "csrftoken")
    missing = [c for c in _REQUIRED if not cookies.get(c)]
    if missing:
        logger.error(
            "[%s] Missing required cookies: %s. Account is invalid/logged-out.",
            account_name, ", ".join(missing),
        )
        raise BotError(
            code=ErrorCode.ACCOUNT_BANNED,
            message=f"Instagram account missing required cookies: {', '.join(missing)}",
            service=Services.INSTAGRAM,
            is_logged=True,
        )
    else:
        logger.debug(
            "[%s] All required cookies present (%s)",
            account_name, ", ".join(_REQUIRED),
        )

    # Record the request for rate-limiting
    await record_request(file_path)

    async with AsyncSession(impersonate="chrome131_android") as session:
        dynamic_vars = await get_start_page_tokens(session, cookies)
        logger.debug(
            "[%s] Dynamic tokens obtained: lsd=%s, fb_dtsg=%s…",
            account_name,
            dynamic_vars.get("lsd", "?"),
            dynamic_vars.get("fb_dtsg", "?")[:8] + "…" if dynamic_vars.get("fb_dtsg") else "?",
        )

        csrf_token = session.cookies.get("csrftoken", cookies.get("csrftoken", ""))
        if csrf_token and csrf_token != cookies.get("csrftoken"):
            old_masked = (cookies.get("csrftoken") or "")[:6] + "…"
            new_masked = csrf_token[:6] + "…"
            logger.info(
                "[%s] csrftoken refreshed by session: %s -> %s (persisting to file)",
                account_name, old_masked, new_masked,
            )
            await update_cookie_in_file(file_path, "csrftoken", csrf_token)
            cookies["csrftoken"] = csrf_token
        else:
            logger.debug(
                "[%s] csrftoken unchanged, no file update needed",
                account_name,
            )

        post_headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded",
            "dnt": "1",
            "origin": "https://www.instagram.com",
            "referer": f"https://www.instagram.com/p/{shortcode}/",
            "sec-ch-ua": _SEC_CH_UA,
            "sec-ch-ua-mobile": _SEC_CH_UA_MOBILE,
            "sec-ch-ua-platform": _SEC_CH_UA_PLATFORM,
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": _CHROME131_ANDROID_UA,
            "x-asbd-id": "129477",
            "x-csrftoken": cookies.get("csrftoken", ""),
            "x-ig-app-id": "1217981644879628",
            "x-fb-friendly-name": "PolarisPostRootQuery",
            "x-fb-lsd": dynamic_vars["lsd"],
            "x-bloks-version-id": dynamic_vars["x-bloks-version-id"],
        }

        data = {
            "av":                  cookies.get("ds_user_id", "0"),
            "__d":                 "www",
            "__user":              "0",
            "__a":                 "1",
            "__req":               "1",
            "fb_dtsg":             dynamic_vars["fb_dtsg"],
            "jazoest":             dynamic_vars["jazoest"],
            "lsd":                 dynamic_vars["lsd"],
            "__spin_r":            dynamic_vars["__spin_r"],
            "__spin_b":            "trunk",
            "__spin_t":            dynamic_vars["__spin_t"],
            "fb_api_caller_class": "RelayModern",
            "fb_api_req_friendly_name": "PolarisPostRootQuery",
            "server_timestamps":   "true",
            "doc_id":              "25951076901259180",
            "variables":           json.dumps({"shortcode": shortcode}),
            "__hs":                "20537.HYP:instagram_web_pkg.2.1...0",
        }

        # Throttle before sending
        await asyncio.sleep(random.uniform(0.5, 1.5))

        response_post = await session.post(graphql_url, headers=post_headers, data=data)

        # ── Ban detection ─────────────────────────────────────────────────────
        if _detect_ban_response(response_post):
            raise BotError(
                code=ErrorCode.ACCOUNT_BANNED,
                message="Instagram account is banned or rate-limited",
                service=Services.INSTAGRAM,
                is_logged=True,
                url=url,
            )

        if response_post.status_code == 429:
            raise BotError(
                code=ErrorCode.ACCOUNT_BANNED,
                message="Instagram rate-limited (429)",
                service=Services.INSTAGRAM,
                is_logged=True,
                url=url,
            )

        if response_post.status_code != 200:
            raise BotError(
                code=ErrorCode.INTERNAL_ERROR,
                message=f"Failed to fetch Instagram post data: {response_post.status_code}",
                service=Services.INSTAGRAM,
                critical=True,
                is_logged=True,
                url=url,
            )

        json_data = response_post.json()
        items = (
            json_data.get("data", {})
            .get("xdt_api__v1__media__shortcode__web_info", {})
            .get("items", [])
        )

        if not items:
            raise BotError(
                code=ErrorCode.METADATA_ERROR,
                message="Failed to fetch metadata for Instagram post",
                service=Services.INSTAGRAM,
                critical=True,
                is_logged=True,
                url=url,
            )

        item = items[0]

        user_info  = item.get("user") or {}
        caption_info = item.get("caption") or {}

        post_data: dict = {
            "shortcode": shortcode,
            "full_name": user_info.get("full_name"),
            "username":  user_info.get("username"),
            "caption":   caption_info.get("text"),
            "media":     [],
        }

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
