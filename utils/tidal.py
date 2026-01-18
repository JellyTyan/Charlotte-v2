import asyncio
import base64
import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from typing import List, Optional, Tuple

import httpx
import aiofiles
from aiofiles import os as aios

logger = logging.getLogger(__name__)

class TidalUtil:
    HEADERS = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'origin': 'https://tidal.squid.wtf',
        'referer': 'https://tidal.squid.wtf/',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'x-client': 'BiniLossless/v3.4',
    }

    SEARCH_URL = 'https://vogel.qqdl.site/search/'
    TRACK_URL = 'https://triton.squid.wtf/track/'

    async def search(self, query: str, limit: int = 10) -> List[dict]:
        """
        Search for tracks on Tidal.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.SEARCH_URL,
                    params={'s': query, 'limit': limit},
                    headers=self.HEADERS,
                    timeout=10.0
                )

                if response.status_code != 200:
                    logger.error(f"Tidal search failed: {response.status_code} - {response.text}")
                    return []

                data = response.json()
                if 'data' in data and 'items' in data['data']:
                    return data['data']['items']
                return []
        except Exception as e:
            logger.error(f"Error searching Tidal: {e}")
            return []

    async def get_track_info(self, track_id: int) -> Optional[dict]:
        """
        Get track download info, trying HI_RES_LOSSLESS then LOSSLESS.
        """
        qualities = ['HI_RES_LOSSLESS', 'LOSSLESS']

        async with httpx.AsyncClient() as client:
            for quality in qualities:
                try:
                    logger.debug(f"Trying Tidal download with quality: {quality}")
                    response = await client.get(
                        self.TRACK_URL,
                        params={'id': track_id, 'quality': quality},
                        headers=self.HEADERS,
                        timeout=10.0
                    )

                    if response.status_code == 200:
                        data = response.json()
                        if 'data' in data:
                            track_data = data['data']
                            track_data['actual_quality'] = track_data.get('audioQuality', quality)
                            return track_data
                except Exception as e:
                    logger.error(f"Error checking Tidal quality {quality}: {e}")

        return None

    async def download(self, track_id: int, filename: str) -> Optional[str]:
        """
        Download a track from Tidal. Returns the path to the downloaded file or None.
        """
        info = await self.get_track_info(track_id)
        if not info:
            logger.warning(f"Could not get Tidal info for track {track_id}")
            return None

        try:
            download_url = None
            dash_manifest = None

            if 'url' in info:
                download_url = info['url']
            elif 'manifest' in info:
                manifest_decoded = base64.b64decode(info['manifest']).decode('utf-8')

                # Check for XML DASH manifest
                if manifest_decoded.strip().startswith('<'):
                    dash_manifest = manifest_decoded
                else:
                    try:
                        manifest_json = json.loads(manifest_decoded)
                        if 'urls' in manifest_json and manifest_json['urls']:
                            download_url = manifest_json['urls'][0]
                    except json.JSONDecodeError:
                        logger.error("Failed to decode Tidal manifest JSON")

            if dash_manifest:
                return await self._download_dash(dash_manifest, filename)
            elif download_url:
                return await self._download_direct(download_url, filename)
            else:
                logger.error("No valid download URL or manifest found")
                return None

        except Exception as e:
            logger.error(f"Error downloading from Tidal: {e}")
            return None

    async def _download_direct(self, url: str, filename: str) -> Optional[str]:
        """Download directly from URL"""
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream("GET", url, headers=self.HEADERS, timeout=None) as response:
                    if response.status_code != 200:
                        logger.error(f"Failed to download stream: {response.status_code}")
                        return None

                    async with aiofiles.open(filename, 'wb') as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            await f.write(chunk)
            return filename
        except Exception as e:
            logger.error(f"Direct download error: {e}")
            if await aios.path.exists(filename):
                await aios.remove(filename)
            return None

    async def _download_dash(self, manifest_xml: str, filename: str) -> Optional[str]:
        """Download DASH segments and merge them"""
        try:
            logger.info("Processing DASH manifest...")
            namespaces = {'ns': 'urn:mpeg:dash:schema:mpd:2011'}
            root = ET.fromstring(manifest_xml)

            # Extract segment template info
            # This is a simplified parser specifically for Tidal's DASH structure
            representation = root.find(".//ns:Representation", namespaces)
            if representation is None:
                logger.error("Could not find Representation in DASH manifest")
                return None

            segment_template = representation.find("ns:SegmentTemplate", namespaces)
            if segment_template is None:
                logger.error("Could not find SegmentTemplate in DASH manifest")
                return None

            init_url = segment_template.get("initialization")
            media_url_template = segment_template.get("media")

            if not init_url or not media_url_template:
                logger.error("Missing templates in DASH manifest")
                return None

            # Create temp directory
            temp_dir = filename + "_temp"
            os.makedirs(temp_dir, exist_ok=True)

            # Download init segment
            init_path = os.path.join(temp_dir, "init.mp4")
            await self._download_direct(init_url, init_path)

            # Parse timeline to get segments
            timeline = segment_template.find("ns:SegmentTimeline", namespaces)
            segments = []
            current_time = 0

            if timeline is not None:
                for s in timeline.findall("ns:S", namespaces):
                    duration = int(s.get("d"))
                    repeat = int(s.get("r", 0))

                    for _ in range(repeat + 1):
                        segments.append(current_time)
                        current_time += duration
            else:
                # Fallback if no timeline (shouldn not happen for Tidal)
                pass

            # Download media segments
            segment_files = [init_path]
            async with httpx.AsyncClient() as client:
                for i, _ in enumerate(segments):
                    # Tidal uses $Number$ template, usually 1-indexed
                    seg_url = media_url_template.replace("$Number$", str(i + 1))
                    seg_path = os.path.join(temp_dir, f"seg_{i+1}.mp4")

                    logger.debug(f"Downloading segment {i+1}...")
                    # await self._download_direct(seg_url, seg_path) - Reusing client is better
                    try:
                        async with client.stream("GET", seg_url, headers=self.HEADERS, timeout=None) as response:
                             if response.status_code == 200:
                                async with aiofiles.open(seg_path, 'wb') as f:
                                    async for chunk in response.aiter_bytes(chunk_size=8192):
                                        await f.write(chunk)
                                segment_files.append(seg_path)
                             else:
                                 logger.warning(f"Failed to download segment {i+1}")
                    except Exception as e:
                        logger.error(f"Error downloading segment {i+1}: {e}")

            # Merge with ffmpeg
            logger.info("Merging segments with ffmpeg...")

            # Create a file list for ffmpeg
            list_file_path = os.path.join(temp_dir, "files.txt")
            async with aiofiles.open(list_file_path, "w") as f:
                for path in segment_files:
                    # ffmpeg concat needs safe paths
                    safe_path = os.path.basename(path).replace("'", "'\\''")
                    await f.write(f"file '{safe_path}'\n")

            # Run ffmpeg
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-f", "concat",
                "-safe", "0",
                "-i", list_file_path,
                "-c", "copy",
                "-y",
                filename,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.error(f"FFmpeg merge failed: {stderr.decode()}")
                return None

            # Cleanup
            try:
                import shutil
                shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir: {e}")

            return filename

        except Exception as e:
            logger.error(f"DASH download error: {e}")
            return None
