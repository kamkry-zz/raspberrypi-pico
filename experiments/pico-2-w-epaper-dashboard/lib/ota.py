"""Over-the-air application updates from the iot-registry OTA registry.

Frozen and never shipped over the air (like ``otaboot``), so a bad bundle can
never break the updater. Protocol: krysdom-api
``openspec/changes/iot-registry-ota``; device side: this experiment's
``openspec/changes/ota-app-updates``.

:func:`check` (called after an hourly refresh, Wi-Fi up):

1. send queued status reports (committed / rolled_back) to the registry;
2. ``GET {OTA_BASE_URL}/apps/{OTA_APP}/manifest`` with ``If-None-Match`` and
   ``X-Device-Id``; 304/404 = nothing to do;
3. ``GET .../manifest.sig`` and verify HMAC-SHA256 with ``secrets.OTA_KEY``;
4. check app, board, MicroPython version, build (> active, not blacklisted)
   and paths (only ``config.mpy`` and ``lib/<module>.mpy``, never the
   protected boot modules);
5. stream every file into the inactive slot, verifying size and sha256;
6. mark it as trial, report ``installed`` and reset into it.
"""

import gc
import hashlib
import json
import os
import socket

import config
import otaboot

BOARD = "RPI_PICO2_W"
PROTECTED = ("otaboot", "ota")
MAX_MANIFEST = 16384
MAX_FILE = 256 * 1024
TIMEOUT_S = 12

results = {}  # result -> count, for pico_ota_checks_total
last = {"check": None, "result": None}


# ------------------------------------------------------------------ crypto
def hmac_sha256(key, message):
    block = 64
    if len(key) > block:
        key = hashlib.sha256(key).digest()
    key = key + b"\x00" * (block - len(key))
    inner = hashlib.sha256(bytes(b ^ 0x36 for b in key))
    inner.update(message)
    outer = hashlib.sha256(bytes(b ^ 0x5C for b in key))
    outer.update(inner.digest())
    return outer.digest()


def _hex(data):
    return "".join("%02x" % b for b in data)


def _same(a, b):
    """Constant-time comparison of two equal-length strings."""
    if len(a) != len(b):
        return False
    diff = 0
    for x, y in zip(a, b):
        diff |= ord(x) ^ ord(y)
    return diff == 0


def verify(manifest_bytes, signature, key_hex):
    if not key_hex:
        return False
    try:
        key = bytes(int(key_hex[i:i + 2], 16) for i in range(0, len(key_hex), 2))
    except ValueError:
        return False
    return _same(_hex(hmac_sha256(key, manifest_bytes)), signature.strip().lower())


# -------------------------------------------------------------- validation
def _safe_path(path):
    if not isinstance(path, str) or ".." in path or path.startswith("/"):
        return False
    if path == "config.mpy":
        return True
    if not (path.startswith("lib/") and path.endswith(".mpy")):
        return False
    name = path[4:-4]
    if not name or name in PROTECTED:
        return False
    return all(c.isalpha() or c.isdigit() or c == "_" for c in name)


def problem(manifest, state, running_mp):
    """None if the manifest may be installed, else the reason (a short string)."""
    if not isinstance(manifest, dict) or manifest.get("schema") != 1:
        return "schema"
    if manifest.get("app") != config.OTA_APP:
        return "app"
    target = manifest.get("target") or {}
    if target.get("board") != BOARD:
        return "board"
    if target.get("micropython") != running_mp:
        return "micropython"
    build = manifest.get("build")
    if not isinstance(build, int) or build <= 0:
        return "build"
    active = state.get("active") or {}
    if build <= (active.get("build") or 0):
        return "not newer"
    if build in state.get("blacklist", []):
        return "blacklisted"
    files = manifest.get("files")
    if not isinstance(files, list) or not files:
        return "files"
    for entry in files:
        if not isinstance(entry, dict) or not _safe_path(entry.get("path")):
            return "path"
        size = entry.get("size")
        if not isinstance(size, int) or not 0 < size <= MAX_FILE:
            return "size"
        sha = entry.get("sha256")
        if not isinstance(sha, str) or len(sha) != 64:
            return "sha256"
    return None


# -------------------------------------------------------------------- http
def _split(url):
    if not url.startswith("http://"):
        raise ValueError("OTA_BASE_URL must be http://")
    rest = url[7:]
    slash = rest.find("/")
    host, path = (rest, "/") if slash < 0 else (rest[:slash], rest[slash:])
    port = 80
    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)
    return host, port, path


def _open(method, url, headers=None, body=None):
    """Send a request; return (sock, status, headers, leftover body bytes)."""
    host, port, path = _split(url)
    sock = socket.socket()
    sock.settimeout(TIMEOUT_S)
    try:
        sock.connect(socket.getaddrinfo(host, port)[0][-1])
        lines = ["%s %s HTTP/1.0" % (method, path), "Host: %s" % host,
                 "User-Agent: %s" % config.USER_AGENT, "Connection: close"]
        for key, value in (headers or {}).items():
            lines.append("%s: %s" % (key, value))
        if body is not None:
            lines.append("Content-Type: application/json")
            lines.append("Content-Length: %d" % len(body))
        sock.send(("\r\n".join(lines) + "\r\n\r\n").encode())
        if body is not None:
            sock.send(body)
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(512)
            if not chunk:
                break
            data += chunk
            if len(data) > 8192:
                raise OSError("header too large")
        head, _, rest = bytes(data).partition(b"\r\n\r\n")
        rows = head.split(b"\r\n")
        status = int(rows[0].split()[1]) if rows and len(rows[0].split()) >= 2 else 0
        found = {}
        for row in rows[1:]:
            key, _, value = row.partition(b":")
            found[key.strip().lower().decode()] = value.strip().decode()
        return sock, status, found, rest
    except Exception:
        sock.close()
        raise


def _read(sock, headers, rest, limit):
    length = int(headers.get("content-length", "-1"))
    if length > limit:
        raise OSError("body too large")
    body = bytearray(rest)
    while length < 0 or len(body) < length:
        chunk = sock.recv(1024)
        if not chunk:
            break
        body += chunk
        if len(body) > limit:
            raise OSError("body too large")
    return bytes(body)


def _get(url, headers=None, limit=MAX_MANIFEST):
    sock, status, found, rest = _open("GET", url, headers)
    try:
        return status, found, _read(sock, found, rest, limit) if status == 200 else b""
    finally:
        sock.close()
        gc.collect()


def _download(url, path, size, sha256, beat):
    """Stream ``url`` into ``path``; raise unless size and sha256 match."""
    sock, status, found, rest = _open("GET", url)
    try:
        if status != 200:
            raise OSError("HTTP %d" % status)
        digest = hashlib.sha256()
        written = 0
        with open(path, "wb") as handle:
            chunk = rest
            while True:
                if chunk:
                    if written + len(chunk) > size:
                        raise OSError("file larger than manifest")
                    handle.write(chunk)
                    digest.update(chunk)
                    written += len(chunk)
                if written >= size:
                    break
                chunk = sock.recv(min(1024, size - written))
                if not chunk:
                    break
                beat()
        if written != size or _hex(digest.digest()) != sha256:
            raise OSError("hash mismatch")
    finally:
        sock.close()
        gc.collect()


# ------------------------------------------------------------------ helpers
def _device():
    import net

    return net.mac_address() or "unknown"


def report(event, build, detail=None):
    """POST one status event to the registry; False on any failure."""
    body = json.dumps({"device": _device(), "app": config.OTA_APP, "build": build,
                       "event": event, "detail": (detail or "")[:200] or None}).encode()
    try:
        sock, status, _, _ = _open("POST", config.OTA_BASE_URL + "/report", body=body)
        sock.close()
        return status in (200, 202)
    except Exception as exc:
        print("OTA report %s failed: %r" % (event, exc))
        return False
    finally:
        gc.collect()


def flush_reports():
    """Deliver queued reports (committed / rolled_back) best effort."""
    state = otaboot.load()
    pending = state.get("pending") or []
    if not pending:
        return 0
    sent = 0
    for item in pending:
        if not report(item.get("event"), item.get("build"), item.get("detail")):
            break
        sent += 1
    if sent:
        state = otaboot.load()  # re-read: keep anything queued meanwhile
        state["pending"] = (state.get("pending") or [])[sent:]
        otaboot.save(state)
    return sent


def _rmtree(path):
    try:
        entries = os.ilistdir(path)
    except (OSError, AttributeError):
        return
    for entry in entries:
        name, kind = entry[0], entry[1]
        full = path + "/" + name
        if kind == 0x4000:
            _rmtree(full)
        else:
            os.remove(full)
    os.rmdir(path)


def _mkdirs(path):
    current = ""
    for part in path.strip("/").split("/"):
        current += "/" + part
        try:
            os.mkdir(current)
        except OSError:
            pass


def _free_bytes():
    stat = os.statvfs("/")
    return stat[0] * stat[3]


def _count(result):
    results[result] = results.get(result, 0) + 1
    last["result"] = result
    return result


def _fail(state, build, reason):
    """Report a failure once per build, then remember it."""
    if build is not None and state.get("failed_build") != build:
        if report("failed", build, reason):
            state["failed_build"] = build
            otaboot.save(state)
    return _count(reason.split(":")[0].replace(" ", "_"))


# -------------------------------------------------------------------- check
def check(beat=lambda: None, reset=None):
    """One update check. Returns a result string; resets the board on install."""
    import time

    last["check"] = time.time()
    flush_reports()
    state = otaboot.load()
    if state.get("trial"):
        return _count("trial_pending")
    base = config.OTA_BASE_URL + "/apps/" + config.OTA_APP
    headers = {"X-Device-Id": _device()}
    if state.get("etag"):
        headers["If-None-Match"] = state["etag"]
    status, found, manifest_bytes = _get(base + "/manifest", headers)
    if status in (304, 404):
        return _count("none")
    if status != 200:
        return _count("fail")
    status, _, signature = _get(base + "/manifest.sig", limit=256)
    try:
        manifest = json.loads(manifest_bytes)
    except ValueError:
        manifest = None
    build = manifest.get("build") if isinstance(manifest, dict) else None
    if status != 200 or not verify(manifest_bytes, signature.decode(), getattr(_secrets(), "OTA_KEY", "")):
        return _fail(state, build, "bad_signature")
    reason = problem(manifest, state, otaboot.micropython_version())
    if reason in ("not newer", "blacklisted"):
        state["etag"] = found.get("etag")
        otaboot.save(state)
        return _count("none")
    if reason:
        return _fail(state, build, "incompatible: " + reason)
    total = sum(entry["size"] for entry in manifest["files"])
    if _free_bytes() < 2 * total + 16384:
        return _fail(state, build, "no_space")

    slot = otaboot.inactive_slot(state)
    root = otaboot.slot_path(slot)
    _rmtree(root)
    try:
        for entry in manifest["files"]:
            path = root + "/" + entry["path"]
            _mkdirs(path.rsplit("/", 1)[0])
            _download(config.OTA_BASE_URL + "/files/" + entry["sha256"], path, entry["size"], entry["sha256"], beat)
            beat()
    except Exception as exc:
        _rmtree(root)
        return _fail(state, build, "hash_mismatch: %r" % (exc,) if "hash" in str(exc) else "download: %r" % (exc,))

    state["trial"] = {"slot": slot, "build": build, "version": manifest.get("version"),
                      "micropython": otaboot.micropython_version()}
    state["attempts"] = 0
    state["etag"] = found.get("etag")
    otaboot.save(state)
    report("installed", build, "slot %s" % slot)
    print("OTA: build %s installed in slot %s; resetting into trial" % (build, slot))
    _count("updated")
    if reset:
        reset()
    return "updated"


def _secrets():
    try:
        import secrets

        return secrets
    except ImportError:
        return None
