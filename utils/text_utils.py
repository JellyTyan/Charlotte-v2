import asyncio
import html
import logging
from concurrent.futures import ThreadPoolExecutor

import translators as ts


def truncate_string(text: str, max_length: int = 1024) -> str:
    if not text or len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def escape_html(text: str) -> str:
    """Escape HTML special characters to prevent parsing errors."""
    return html.escape(text) if text else ""

def escape_markdown(text: str) -> str:
    special_chars = [
        "*",
        "_",
        "[",
        "]",
        "(",
        ")",
        "~",
        "`",
        ">",
        "#",
        "+",
        "-",
        "=",
        "|",
        "{",
        "}",
        ".",
        "!",
    ]
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text

logger = logging.getLogger(__name__)

executor = ThreadPoolExecutor()

def translate_sync(text: str, target_language: str) -> str:
    """
    Synchronized function to translate text.

    :param text: Text to be translated.
    :param target_language: Target language for translation.
    :return: Translated text.
    """
    translated = ts.translate_text(text, translator="google", from_language="auto", to_language=target_language)
    if translated is None:
        logger.error(f"Translation failed for text: {text}")
        return "Translation Error"
    return translated


async def translate_text(text: str, target_language: str = "en") -> str:
    """
    Asynchronously translates text using GoogleTranslator.

    :param text: Text to be translated.
    :param target_language: Target language for translation.
    :return: Translated text.
    """
    loop = asyncio.get_running_loop()
    try:
        translated = await loop.run_in_executor(
            executor, translate_sync, text, target_language
        )
        return translated
    except Exception as e:
        logger.error(f"Error during translation: {str(e)}")
        return "Translation Error"
