import asyncio
import logging
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin

from curl_cffi.requests import AsyncSession
from arq.connections import RedisSettings
import aiofiles
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


# ============================================================================
# HTTP & API FUNCTIONS
# ============================================================================

async def universal_http_request(
    ctx,
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    data: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    cookies: Optional[Dict[str, str]] = None,
    timeout: int = 30,
    allow_redirects: bool = True,
    impersonate: str = "chrome136",
) -> Dict[str, Any]:
    """
    Universal HTTP request function with browser impersonation.

    Args:
        ctx: ARQ context
        url: Target URL
        method: HTTP method (GET, POST, PUT, DELETE, etc.)
        headers: Custom headers
        params: URL parameters
        data: Form data
        json_data: JSON body
        cookies: Cookies
        timeout: Request timeout in seconds
        allow_redirects: Follow redirects
        impersonate: Browser to impersonate

    Returns:
        dict: {
            'content': bytes,
            'text': str,
            'status_code': int,
            'headers': dict,
            'url': str,
            'cookies': dict
        }
    """
    logger.info(f"HTTP {method} request to {url}")

    try:
        async with AsyncSession(impersonate=impersonate) as session:
            response = await session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                data=data,
                json=json_data,
                cookies=cookies,
                timeout=timeout,
                allow_redirects=allow_redirects,
            )

            return {
                "content": response.content,
                "text": response.text,
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url),
                "cookies": dict(response.cookies),
            }
    except Exception as e:
        logger.error(f"HTTP request failed: {e}")
        raise


async def universal_api_call(
    ctx,
    base_url: str,
    endpoint: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    auth_token: Optional[str] = None,
    auth_type: str = "Bearer",
    retry_count: int = 3,
    retry_delay: float = 1.0,
) -> Dict[str, Any]:
    """
    Structured API call with automatic retry logic.

    Args:
        ctx: ARQ context
        base_url: API base URL
        endpoint: API endpoint (will be joined with base_url)
        method: HTTP method
        headers: Custom headers
        params: Query parameters
        json_data: JSON request body
        auth_token: Authentication token
        auth_type: Authorization type (Bearer, Token, etc.)
        retry_count: Number of retry attempts
        retry_delay: Delay between retries in seconds

    Returns:
        dict: Parsed JSON response
    """
    url = urljoin(base_url, endpoint)

    if headers is None:
        headers = {}

    if auth_token:
        headers["Authorization"] = f"{auth_type} {auth_token}"

    for attempt in range(retry_count):
        try:
            result = await universal_http_request(
                ctx=ctx,
                url=url,
                method=method,
                headers=headers,
                params=params,
                json_data=json_data,
            )

            if result["status_code"] >= 200 and result["status_code"] < 300:
                import json
                return json.loads(result["text"])

            if attempt < retry_count - 1:
                logger.warning(f"API call failed with status {result['status_code']}, retrying...")
                await asyncio.sleep(retry_delay * (attempt + 1))
            else:
                raise Exception(f"API call failed: {result['status_code']}")

        except Exception as e:
            if attempt < retry_count - 1:
                logger.warning(f"API call error: {e}, retrying...")
                await asyncio.sleep(retry_delay * (attempt + 1))
            else:
                logger.error(f"API call failed after {retry_count} attempts: {e}")
                raise


async def universal_download_bytes(
    ctx,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, Any]] = None,
    max_size: int = 10 * 1024 * 1024,  # 10MB default limit
    impersonate: str = "chrome136",
) -> bytes:
    """
    Download content directly to memory without saving to disk.

    WARNING: Results are stored in Redis, so keep max_size reasonable (<20MB).
    For larger files, use universal_download to save to disk instead.

    Args:
        ctx: ARQ context
        url: File URL
        headers: Custom headers
        params: URL parameters
        max_size: Maximum file size in bytes (default 10MB)
        impersonate: Browser to impersonate

    Returns:
        bytes: Downloaded content

    Raises:
        Exception: If file is too large or download fails
    """
    logger.info(f"Downloading bytes from {url} (max: {max_size} bytes)")

    try:
        async with AsyncSession(impersonate=impersonate) as session:
            response = await session.get(
                url,
                headers=headers,
                params=params,
                stream=True,
            )

            if response.status_code != 200:
                raise Exception(f"Download failed: {response.status_code}")

            # Check content length
            content_length = response.headers.get("Content-Length")
            if content_length:
                size = int(content_length)
                if size > max_size:
                    raise Exception(
                        f"File too large: {size} bytes (max: {max_size}). "
                        f"Use universal_download to save to disk instead."
                    )

            # Download to memory with size check
            chunks = []
            total_size = 0

            async for chunk in response.aiter_content(chunk_size=8192):
                total_size += len(chunk)

                if total_size > max_size:
                    raise Exception(
                        f"File size exceeded: {total_size} bytes (max: {max_size}). "
                        f"Use universal_download to save to disk instead."
                    )

                chunks.append(chunk)

            content = b"".join(chunks)
            logger.info(f"Downloaded {len(content)} bytes")
            return content

    except Exception as e:
        logger.error(f"Download bytes failed: {e}")
        raise


# ============================================================================
# DOWNLOAD FUNCTIONS
# ============================================================================

async def universal_download(
    ctx,
    url: str,
    destination: str,
    headers: Optional[Dict[str, str]] = None,
    chunk_size: int = 8192,
    max_size: Optional[int] = None,
    resume: bool = False,
    impersonate: str = "chrome136",
) -> str:
    """
    Download any file with optional resume support.

    Args:
        ctx: ARQ context
        url: File URL
        destination: Destination file path
        headers: Custom headers
        chunk_size: Download chunk size in bytes
        max_size: Maximum file size in bytes (None for unlimited)
        resume: Support resume download
        impersonate: Browser to impersonate

    Returns:
        str: Downloaded file path
    """
    logger.info(f"Downloading {url} to {destination}")

    dest_path = Path(destination)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    # Check if file exists for resume
    start_byte = 0
    if resume and dest_path.exists():
        start_byte = dest_path.stat().st_size
        logger.info(f"Resuming download from byte {start_byte}")

    if headers is None:
        headers = {}

    if resume and start_byte > 0:
        headers["Range"] = f"bytes={start_byte}-"

    try:
        async with AsyncSession(impersonate=impersonate) as session:
            async with session.stream("GET", url, headers=headers) as response:
                if response.status_code not in [200, 206]:
                    raise Exception(f"Download failed: {response.status_code}")

                # Check content length
                content_length = response.headers.get("Content-Length")
                if content_length:
                    total_size = int(content_length) + start_byte
                    if max_size and total_size > max_size:
                        raise Exception(f"File too large: {total_size} bytes (max: {max_size})")

                mode = "ab" if (resume and start_byte > 0) else "wb"
                total_written = start_byte

                async with aiofiles.open(dest_path, mode) as f:
                    async for chunk in response.aiter_content(chunk_size=chunk_size):
                        total_written += len(chunk)

                        if max_size and total_written > max_size:
                            raise Exception(f"File size exceeded: {total_written} bytes (max: {max_size})")

                        await f.write(chunk)

                logger.info(f"Download complete: {total_written} bytes")
                return str(dest_path)

    except Exception as e:
        logger.error(f"Download failed: {e}")
        # Clean up partial file if not resuming
        if not resume and dest_path.exists():
            dest_path.unlink()
        raise


async def universal_stream_download(
    ctx,
    url: str,
    destination: str,
    headers: Optional[Dict[str, str]] = None,
    chunk_size: int = 65536,  # 64KB chunks for streaming
    callback: Optional[str] = None,  # Optional callback job name
    impersonate: str = "chrome136",
) -> str:
    """
    Stream large files efficiently with optional progress callback.

    Args:
        ctx: ARQ context
        url: File URL
        destination: Destination file path
        headers: Custom headers
        chunk_size: Chunk size (larger for streaming)
        callback: Optional callback function name for progress updates
        impersonate: Browser to impersonate

    Returns:
        str: Downloaded file path
    """
    logger.info(f"Stream downloading {url}")

    dest_path = Path(destination)
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        async with AsyncSession(impersonate=impersonate) as session:
            async with session.stream("GET", url, headers=headers, timeout=None) as response:
                if response.status_code != 200:
                    raise Exception(f"Stream download failed: {response.status_code}")

                content_length = response.headers.get("Content-Length")
                total_size = int(content_length) if content_length else None

                total_written = 0
                async with aiofiles.open(dest_path, "wb") as f:
                    async for chunk in response.aiter_content(chunk_size=chunk_size):
                        await f.write(chunk)
                        total_written += len(chunk)

                        # Optional progress callback
                        if callback and total_size:
                            progress = (total_written / total_size) * 100
                            if int(progress) % 10 == 0:  # Report every 10%
                                logger.debug(f"Download progress: {progress:.1f}%")

                logger.info(f"Stream download complete: {total_written} bytes")
                return str(dest_path)

    except Exception as e:
        logger.error(f"Stream download failed: {e}")
        if dest_path.exists():
            dest_path.unlink()
        raise


# ============================================================================
# DATA EXTRACTION FUNCTIONS
# ============================================================================

async def universal_html_parse(
    ctx,
    html_content: str,
    selector_type: str = "css",
    selectors: Optional[Dict[str, str]] = None,
    extract_type: str = "text",  # text, html, attr
    attribute: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Parse HTML with CSS selectors or XPath.

    Args:
        ctx: ARQ context
        html_content: HTML content to parse
        selector_type: 'css' or 'xpath'
        selectors: Dict of {key: selector_string}
        extract_type: What to extract - 'text', 'html', 'attr'
        attribute: Attribute name if extract_type='attr'

    Returns:
        dict: Extracted data {key: value}
    """
    logger.info(f"Parsing HTML with {selector_type} selectors")

    try:
        soup = BeautifulSoup(html_content, "html.parser")
        results = {}

        if selectors:
            for key, selector in selectors.items():
                if selector_type == "css":
                    elements = soup.select(selector)
                else:
                    # XPath not directly supported by BeautifulSoup
                    raise ValueError("XPath not supported, use CSS selectors")

                if not elements:
                    results[key] = None
                    continue

                # Extract data based on type
                if extract_type == "text":
                    results[key] = [el.get_text(strip=True) for el in elements]
                elif extract_type == "html":
                    results[key] = [str(el) for el in elements]
                elif extract_type == "attr" and attribute:
                    results[key] = [el.get(attribute) for el in elements]
                else:
                    results[key] = None

        return results

    except Exception as e:
        logger.error(f"HTML parsing failed: {e}")
        raise


async def universal_json_extract(
    ctx,
    content: str,
    json_path: Optional[str] = None,
    pattern: Optional[str] = None,
    extract_all: bool = False,
) -> Any:
    """
    Extract JSON from various sources (raw JSON, embedded in HTML, etc.).

    Args:
        ctx: ARQ context
        content: Content to parse
        json_path: Optional JSON path to extract specific data (e.g., "data.items[0]")
        pattern: Regex pattern to find JSON in content
        extract_all: Extract all JSON matches if pattern is used

    Returns:
        Parsed JSON data
    """
    import json

    logger.info("Extracting JSON from content")

    try:
        # If pattern provided, search for JSON
        if pattern:
            matches = re.finditer(pattern, content, re.DOTALL)
            jsons = []

            for match in matches:
                json_str = match.group(1) if match.groups() else match.group(0)
                try:
                    parsed = json.loads(json_str)
                    jsons.append(parsed)
                    if not extract_all:
                        break
                except json.JSONDecodeError:
                    continue

            result = jsons if extract_all else (jsons[0] if jsons else None)
        else:
            # Parse as direct JSON
            result = json.loads(content)

        # Apply JSON path if provided
        if json_path and result:
            parts = json_path.replace("[", ".").replace("]", "").split(".")
            for part in parts:
                if part:
                    if part.isdigit():
                        result = result[int(part)]
                    else:
                        result = result.get(part)
                    if result is None:
                        break

        return result

    except Exception as e:
        logger.error(f"JSON extraction failed: {e}")
        raise


async def universal_regex_extract(
    ctx,
    content: str,
    patterns: Dict[str, str],
    flags: int = 0,
    extract_all: bool = False,
) -> Dict[str, Any]:
    """
    Extract data using regex patterns.

    Args:
        ctx: ARQ context
        content: Content to search
        patterns: Dict of {key: regex_pattern}
        flags: Regex flags (re.DOTALL, re.IGNORECASE, etc.)
        extract_all: Return all matches instead of first

    Returns:
        dict: Extracted data {key: match or [matches]}
    """
    logger.info("Extracting data with regex")

    results = {}

    for key, pattern in patterns.items():
        try:
            if extract_all:
                matches = re.findall(pattern, content, flags)
                results[key] = matches if matches else None
            else:
                match = re.search(pattern, content, flags)
                results[key] = match.group(1) if match and match.groups() else (match.group(0) if match else None)
        except Exception as e:
            logger.error(f"Regex extraction failed for {key}: {e}")
            results[key] = None

    return results


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def universal_url_resolve(
    ctx,
    url: str,
    max_redirects: int = 5,
    impersonate: str = "chrome136",
) -> str:
    """
    Resolve shortened URLs and follow redirects.

    Args:
        ctx: ARQ context
        url: URL to resolve
        max_redirects: Maximum redirects to follow
        impersonate: Browser to impersonate

    Returns:
        str: Final resolved URL
    """
    logger.info(f"Resolving URL: {url}")

    try:
        async with AsyncSession(impersonate=impersonate) as session:
            response = await session.head(url, allow_redirects=True, max_redirects=max_redirects)
            final_url = str(response.url)
            logger.info(f"Resolved to: {final_url}")
            return final_url
    except Exception as e:
        logger.error(f"URL resolution failed: {e}")
        # Fallback to GET if HEAD fails
        try:
            async with AsyncSession(impersonate=impersonate) as session:
                response = await session.get(url, allow_redirects=True, max_redirects=max_redirects)
                return str(response.url)
        except Exception as e2:
            logger.error(f"URL resolution failed completely: {e2}")
            raise


# ============================================================================
# WORKER SETTINGS
# ============================================================================

class WorkerSettings:
    """ARQ light worker settings for non-blocking operations"""
    functions = [
        # HTTP & API
        universal_http_request,
        universal_api_call,
        # Downloads
        universal_download_bytes,
        universal_download,
        universal_stream_download,
        # Data extraction
        universal_html_parse,
        universal_json_extract,
        universal_regex_extract,
        # Utilities
        universal_url_resolve,
    ]
    redis_settings = RedisSettings(host='redis', port=6379)
    queue_name = 'light'
