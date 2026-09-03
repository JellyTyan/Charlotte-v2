import html
import logging

import httpx


def truncate_string(text: str, max_length: int = 1024) -> str:
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


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


logger = logging.getLogger(__name__)


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
    Asynchronously translates text using translators.
    """
    if not text:
        return text
    import asyncio
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, translate_sync, text, target_language)
