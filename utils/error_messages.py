from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from fluentogram import TranslatorRunner
from models.errors import ErrorCode


def get_error_keyboard(i18n: TranslatorRunner | None = None, owner_id: int | None = None) -> InlineKeyboardMarkup:
    """Create an inline keyboard with a 'Close' button for error messages."""
    close_text = i18n.get("btn-close") if i18n else "✕ Close"
    cb_data = f"close_error:{owner_id}" if owner_id else "close_error"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=close_text, callback_data=cb_data)]
    ])


def get_i18n_error_message(code: ErrorCode, i18n: TranslatorRunner) -> str | None:
    """Get translated error message for a specific ErrorCode"""
    match code:
        case ErrorCode.INVALID_URL:
            return i18n.get("error-invalid-url")
        case ErrorCode.PRIVATE_CONTENT:
            return i18n.get("error-private-content")
        case ErrorCode.LARGE_FILE:
            return i18n.get("error-large-file")
        case ErrorCode.NOT_ALLOWED:
            return i18n.get("error-not-allowed")
        case ErrorCode.INTERNAL_ERROR:
            return i18n.get("error-internal")
        case ErrorCode.NOT_FOUND:
            return i18n.get("error-not-found")
        case ErrorCode.REGION_RESTRICTED:
            return i18n.get("error-region-restricted")
        case ErrorCode.AGE_RESTRICTED:
            return i18n.get("error-age-restricted")
        case ErrorCode.DOWNLOAD_CANCELLED:
            return i18n.get("error-download-canceled")
        case ErrorCode.PREVIEW_ONLY:
            return i18n.get("error-preview-only")
        case ErrorCode.SEND_ERROR:
            return None
        case _:
            return None
