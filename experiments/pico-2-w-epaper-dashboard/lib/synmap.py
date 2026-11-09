"""IMGW synoptic map from pogoda-hub, cached on flash and blitted into the canvas.

The hub serves ``/v1/map.bin`` in this panel's native encoding: a 16-byte
``PHM1`` header (``>4sHHIHH``: magic, width, height, analysis epoch UTC, flags,
reserved) followed by the black and red planes (MSB-first, 0 = ink), 400x250.
The body is streamed to flash (no 25 KB heap block) and copied row by row into
``canvas.black`` / ``canvas.red`` at render time.
"""

import os
import struct
import time

import config
import http_client
import store
import telemetry

HEADER = ">4sHHIHH"
HEADER_SIZE = 16
MAGIC = b"PHM1"
WIDTH = 400
HEIGHT = 250
PLANE = WIDTH // 8 * HEIGHT
FLAG_STALE = 1

_last_check_ticks = None


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def info(path=None):
    """Header of the cached map: dict(analysis, stale) or None if missing/invalid."""
    path = path or config.MAP_CACHE_FILE
    try:
        with open(path, "rb") as handle:
            head = handle.read(HEADER_SIZE)
        magic, width, height, analysis, flags, _ = struct.unpack(HEADER, head)
    except (OSError, ValueError):
        return None
    if magic != MAGIC or width != WIDTH or height != HEIGHT:
        return None
    return {"analysis": analysis, "stale": bool(flags & FLAG_STALE)}


def fetch(force=False):
    """Refresh the cached map if due; 304 keeps the file. Returns the info dict."""
    global _last_check_ticks
    due = (
        force
        or _last_check_ticks is None
        or time.ticks_diff(time.ticks_ms(), _last_check_ticks) >= config.MAP_CHECK_MINUTES * 60000
    )
    if not due:
        return info()
    _last_check_ticks = time.ticks_ms()
    meta = store.load(config.MAP_META_FILE) or {}
    etag = meta.get("etag") if _exists(config.MAP_CACHE_FILE) else None
    tmp = config.MAP_CACHE_FILE + ".tmp"
    try:
        status, new_etag = http_client.get_to_file(
            config.HUB_MAP_URL, tmp, etag=etag, timeout=config.HTTP_TIMEOUT_S
        )
        if status == 200:
            if info(tmp) is None or os.stat(tmp)[6] != HEADER_SIZE + 2 * PLANE:
                raise OSError("invalid map body")
            try:
                os.remove(config.MAP_CACHE_FILE)
            except OSError:
                pass
            os.rename(tmp, config.MAP_CACHE_FILE)
            store.save(config.MAP_META_FILE, {"etag": new_etag})
            telemetry.inc("dashboard.map.fetches", {"result": "new"})
        elif status == 304:
            telemetry.inc("dashboard.map.fetches", {"result": "unchanged"})
        else:
            raise OSError("HTTP %d" % status)
    except Exception as exc:
        telemetry.inc("dashboard.map.fetches", {"result": "fail"})
        telemetry.log("Map fetch failed: %r" % (exc,), "WARN")
    return info()


def blit(canvas, y, path=None):
    """Copy the cached planes into the canvas at row ``y``. Returns False if no map."""
    path = path or config.MAP_CACHE_FILE
    if info(path) is None or canvas.stride != WIDTH // 8:
        return False
    rows = min(HEIGHT, canvas.height - y)
    span = rows * canvas.stride
    start = y * canvas.stride
    with open(path, "rb") as handle:
        handle.seek(HEADER_SIZE)
        handle.readinto(memoryview(canvas.black)[start:start + span])
        handle.seek(HEADER_SIZE + PLANE)
        handle.readinto(memoryview(canvas.red)[start:start + span])
    return True
