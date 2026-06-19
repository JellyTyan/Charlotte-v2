from fluentogram import TranslatorRunner
from models.errors import ErrorCode

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
        case _:
            return None
