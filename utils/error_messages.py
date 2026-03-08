from fluentogram import TranslatorRunner
from models.errors import ErrorCode

def get_i18n_error_message(code: ErrorCode, i18n: TranslatorRunner) -> str | None:
    """Get translated error message for a specific ErrorCode"""
    match code:
        case ErrorCode.INVALID_URL:
            return i18n.error.invalid.url()
        case ErrorCode.LARGE_FILE:
            return i18n.error.large.file()
        case ErrorCode.SIZE_CHECK_FAIL:
            return i18n.error.fail.check()
        case ErrorCode.DOWNLOAD_FAILED:
            return i18n.error.download.error()
        case ErrorCode.DOWNLOAD_CANCELLED:
            return i18n.error.download.canceled()
        case ErrorCode.PLAYLIST_INFO_ERROR:
            return i18n.error.playlist.info()
        case ErrorCode.METADATA_ERROR:
            return i18n.error.metadata()
        case ErrorCode.NOT_FOUND:
            return i18n.error.no.found()
        case ErrorCode.NOT_ALLOWED:
            return i18n.error.no.allowed()
        case ErrorCode.INTERNAL_ERROR:
            return i18n.error.internal()
        case _:
            return None
