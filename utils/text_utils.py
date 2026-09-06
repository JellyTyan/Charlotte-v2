import html
import logging
import re

import httpx

logger = logging.getLogger(__name__)


def truncate_string(text: str, max_length: int = 1024) -> str:
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def truncate_html_text(text: str, max_length: int) -> str:
    """
    Truncates plain or HTML-escaped text safely, avoiding sliced HTML entities
    (e.g. cutting '&quot;' into '&qu...').
    """
    if not text or len(text) <= max_length:
        return text
    if max_length <= 3:
        return text[:max_length]

    truncated = text[:max_length - 3]
    # Remove any trailing incomplete HTML entity (e.g. &amp, &qu, &#123)
    truncated = re.sub(r"&[a-zA-Z0-9#]{1,7}$", "", truncated)
    return truncated.rstrip() + "..."


def ensure_html_tags_closed(text: str) -> str:
    """
    Ensures that any opened supported Telegram HTML tags (<blockquote>, <b>, <i>,
    <code>, <s>, <u>, <tg-spoiler>, <a>) are properly closed in correct order.
    """
    if not text:
        return text

    supported_tags = ["blockquote", "b", "i", "code", "s", "u", "tg-spoiler", "a"]
    tag_pattern = re.compile(r"<\s*(/)?\s*([a-zA-Z0-9-]+)(?:\s+[^>]*)?>")
    stack = []

    for match in tag_pattern.finditer(text):
        is_closing = match.group(1) == "/"
        tag_name = match.group(2).lower()
        if tag_name in supported_tags:
            if is_closing:
                if stack and stack[-1] == tag_name:
                    stack.pop()
                elif tag_name in stack:
                    while stack:
                        top = stack.pop()
                        if top == tag_name:
                            break
            else:
                stack.append(tag_name)

    closing_tags = "".join(f"</{tag}>" for tag in reversed(stack))
    return text + closing_tags


def escape_html(text: str) -> str:
    """Escape HTML special characters to prevent parsing errors."""
    return html.escape(text) if text else ""


def escape_markdown(text: str) -> str:
    special_chars = [
        "*", "_", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!",
    ]
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def format_author_link(author_name: str, author_url: str = "", icon: str = "👤") -> str:
    """
    Formats a safe, HTML-escaped author link (e.g. 👤 <a href='...'>Author</a>).
    """
    name = (author_name or "").strip()
    if not name:
        return ""
    name_esc = escape_html(name)
    prefix = f"{icon} " if icon else ""
    if author_url and author_url.strip():
        url_esc = escape_html(author_url.strip())
        return f"{prefix}<a href='{url_esc}'>{name_esc}</a>"
    return f"{prefix}{name_esc}"


def safe_truncate_html(text: str, max_length: int = 1024) -> str:
    """
    Safely truncates HTML text so that the final string:
    1. Does not exceed max_length.
    2. Has no incomplete/severed HTML entities (e.g. &amp).
    3. Has no incomplete/severed HTML opening/closing tags (e.g. <a href="...).
    4. Has all opened supported Telegram tags properly closed in reverse order.
    """
    if not text or len(text) <= max_length:
        return ensure_html_tags_closed(text)

    # First attempt: if text has a blockquote, try truncating just the inner text of blockquote first!
    bq_match = re.search(r"^(.*?)(<blockquote[^>]*>)(.*?)(</blockquote>)(.*)$", text, flags=re.DOTALL)
    if bq_match:
        prefix, bq_open, inner, bq_close, suffix = bq_match.groups()
        fixed_len = len(prefix) + len(bq_open) + len(bq_close) + len(suffix)
        available_inner = max_length - fixed_len
        if available_inner >= 10:
            shrunk_inner = truncate_html_text(inner, available_inner)
            candidate = f"{prefix}{bq_open}{shrunk_inner}{bq_close}{suffix}"
            if len(candidate) <= max_length:
                return candidate

    # Fallback / General truncation: iterative reduction to fit max_length with closing tags
    cut = max_length - 3
    while cut > 0:
        truncated = text[:cut]
        # Remove trailing severed tag (e.g. "<a hr" or "<blo")
        truncated = re.sub(r"<[^>]*$", "", truncated)
        # Remove trailing severed HTML entity (e.g. "&am")
        truncated = re.sub(r"&[a-zA-Z0-9#]{1,7}$", "", truncated)
        candidate = truncated.rstrip() + "..."
        candidate = ensure_html_tags_closed(candidate)
        if len(candidate) <= max_length:
            return candidate
        cut -= 5

    return text[:max_length]


def build_caption(header: str = "", description: str = "", max_total_length: int = 950) -> str:
    """
    Combines a header (e.g. author link / title) and an optional description.
    Wraps non-empty description in a collapsible blockquote (<blockquote expandable>).
    Guarantees that the entire result fits within max_total_length (leaving room for bot ad / signature)
    and that tags are always properly closed.
    """
    header = (header or "").strip()
    description = (description or "").strip()

    if not description:
        return safe_truncate_html(header, max_total_length)

    if not header:
        # Overheads: <blockquote expandable> (23) + </blockquote> (13) = 36
        max_desc_len = max(max_total_length - 36, 10)
        clean_desc = truncate_html_text(description, max_desc_len)
        return f"<blockquote expandable>{clean_desc}</blockquote>"

    # Both header and description
    # Overheads: \n\n (2) + <blockquote expandable> (23) + </blockquote> (13) = 38
    max_header_len = 350
    clean_header = safe_truncate_html(header, max_header_len)

    available_desc_len = max_total_length - len(clean_header) - 38
    if available_desc_len < 30:
        return clean_header

    clean_desc = truncate_html_text(description, available_desc_len)
    return f"{clean_header}\n\n<blockquote expandable>{clean_desc}</blockquote>"


def translate_sync(text: str, target_language: str) -> str:
    """
    Synchronized function to translate text using translators library with fallback.
    """
    if not text:
        return text
    try:
        import translators as ts
        translated = ts.translate_text(text, translator="google", from_language="auto", to_language=target_language)
        if translated:
            return translated
    except Exception as e:
        logger.debug(f"translators failed ({e}), falling back to direct translation")

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                "https://translate.googleapis.com/translate_a/single",
                params={"client": "gtx", "sl": "auto", "tl": target_language, "dt": "t", "q": text},
            )
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and data[0]:
                    return "".join(part[0] for part in data[0] if part and part[0])
    except Exception as e:
        logger.error(f"Translation failed for text: {text}: {e}")
    return text


async def translate_text(text: str, target_language: str = "en") -> str:
    """
    Asynchronously translates text. If text contains a blockquote (<blockquote expandable>...</blockquote>),
    only the inner description is translated, keeping author links and HTML structure intact.
    """
    if not text:
        return text

    import asyncio
    loop = asyncio.get_running_loop()

    # Extract blockquote content if present, to avoid translating author links or destroying HTML tags
    bq_match = re.search(r"^(.*?)(<blockquote[^>]*>)(.*?)(</blockquote>)(.*)$", text, flags=re.DOTALL)
    if bq_match:
        prefix, bq_open, inner_desc, bq_close, suffix = bq_match.groups()
        try:
            translated_inner = await loop.run_in_executor(None, translate_sync, inner_desc, target_language)
            # Budget check so translated description doesn't cause caption overflow
            max_inner_len = 950 - len(prefix) - len(bq_open) - len(bq_close) - len(suffix)
            if max_inner_len > 10 and len(translated_inner) > max_inner_len:
                translated_inner = truncate_html_text(translated_inner, max_inner_len)
            return f"{prefix}{bq_open}{translated_inner}{bq_close}{suffix}"
        except Exception as e:
            logger.error(f"Failed to translate blockquote text: {e}")
            return text

    try:
        translated = await loop.run_in_executor(None, translate_sync, text, target_language)
        if len(translated) > 950:
            translated = safe_truncate_html(translated, 950)
        return translated
    except Exception as e:
        logger.error(f"Failed to translate text: {e}")
        return text
