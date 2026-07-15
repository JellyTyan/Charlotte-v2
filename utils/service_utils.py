import httpx
from models.errors import BotError, ErrorCode
from models.service_list import Services


def handle_lossless_response(response: httpx.Response, url: str, service: Services) -> dict:
    """
    Parses response from lossless-core, maps error codes to ErrorCode enum,
    and raises structured BotError on failure.
    """
    data = None
    try:
        data = response.json()
    except Exception:
        pass

    is_error = False
    error_code_str = None
    error_msg = None

    if data and isinstance(data, dict):
        if data.get("status") == "error" or response.status_code != 200:
            is_error = True
            err_obj = data.get("error", {})
            if isinstance(err_obj, dict):
                error_code_str = err_obj.get("code")
                error_msg = err_obj.get("message")
            if not error_msg:
                error_msg = data.get("message")
    elif response.status_code != 200:
        is_error = True
        error_msg = response.text

    if not is_error:
        if data and "data" in data:
            return data["data"]
        return data

    # Default fallback mapped code
    mapped_code = ErrorCode.INTERNAL_ERROR

    if error_code_str:
        if error_code_str in ("UNSUPPORTED_SERVICE", "INVALID_INPUT"):
            mapped_code = ErrorCode.INVALID_URL
        elif error_code_str == "TRACK_NOT_FOUND":
            mapped_code = ErrorCode.NOT_FOUND
        elif error_code_str == "PREVIEW_ONLY":
            mapped_code = ErrorCode.PREVIEW_ONLY
        # DOWNLOAD_FAILED, LOSSLESS_FAILED → INTERNAL_ERROR (default)
    else:
        # Fallback based on HTTP status code
        if response.status_code == 400:
            mapped_code = ErrorCode.INVALID_URL
        elif response.status_code == 404:
            mapped_code = ErrorCode.NOT_FOUND
        elif response.status_code == 422:
            mapped_code = ErrorCode.PREVIEW_ONLY
        # 500/502/503 → INTERNAL_ERROR (default)

    # Check for region restriction in error message (overrides above)
    if error_msg:
        err_lower = error_msg.lower()
        if any(keyword in err_lower for keyword in ("geo", "country", "region", "geoblock")):
            mapped_code = ErrorCode.REGION_RESTRICTED

    raise BotError(
        code=mapped_code,
        url=url,
        service=service,
        message=f"Lossless Core Error ({response.status_code}): {error_msg or 'Unknown error'}",
        is_logged=True,
        critical=False,
    )

