"""Build, sign and publish an OTA release to the iot-registry OTA registry.

    .venv/bin/python tools/ota_publish.py --notes "what changed"            # dry run
    .venv/bin/python tools/ota_publish.py --notes "what changed" --upload   # publish

Publishing IS deploying: every Pico 2 W running this app installs the release
automatically (on trial, rolled back if it cannot draw a frame). Only publish
when the user asks.

- Bundle = ``config.mpy`` + ``lib/*.mpy`` from ``tools/build.py`` (mpy-cross
  1.29.0), minus the frozen-only boot/update modules (``OTA_PROTECTED``).
- ``manifest.json`` (schema 1) is signed with HMAC-SHA256 using ``OTA_KEY``
  from the gitignored ``secrets.py``; the registry stores it verbatim.
- ``build`` = the highest build ever published (yanked included) + 1;
  override with ``--build``.
- Auth: Keycloak client credentials from
  ``~/.config/krysdom/iot-registry-publisher.env`` (realm role ota-publisher).
- Files land in ``build/ota/`` (manifest.json, manifest.sig) for inspection.
"""

import argparse
import base64
import hashlib
import hmac
import json
import os
import runpy
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import build as builder  # noqa: E402

APP = "pico-epaper-dashboard"
BOARD = "RPI_PICO2_W"
ENV_FILE = Path.home() / ".config" / "krysdom" / "iot-registry-publisher.env"
CA_FILE = ROOT / "certs" / "k3s-ca.der"
OUT = ROOT / "build" / "ota"


def bundle_files():
    """[(path in bundle, bytes)] from build/, sorted by path."""
    files = [("config.mpy", (builder.BUILD / "config.mpy").read_bytes())]
    for name in sorted(builder.LIBS):
        if name in builder.OTA_PROTECTED:
            continue
        files.append(("lib/%s.mpy" % name, (builder.BUILD / "lib" / (name + ".mpy")).read_bytes()))
    return files


def make_manifest(files, build, version, notes):
    manifest = {
        "schema": 1,
        "app": APP,
        "build": build,
        "version": version,
        "target": {"board": BOARD, "micropython": builder.MPY_VERSION, "mpy": "6.3"},
        "files": [{"path": p, "size": len(d), "sha256": hashlib.sha256(d).hexdigest()} for p, d in files],
    }
    if notes:
        manifest["notes"] = notes[:512]
    return json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()


def sign(manifest_bytes, key_hex):
    return hmac.new(bytes.fromhex(key_hex), manifest_bytes, hashlib.sha256).hexdigest()


def load_key():
    key = runpy.run_path(str(ROOT / "secrets.py")).get("OTA_KEY", "")
    if len(key) < 32:
        sys.exit("secrets.py OTA_KEY is missing or too short (hex, 32 bytes recommended)")
    return key


def load_env():
    if not ENV_FILE.exists():
        sys.exit("missing %s (Keycloak publisher client credentials)" % ENV_FILE)
    env = {}
    for line in ENV_FILE.read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def _context():
    ctx = ssl.create_default_context()
    if CA_FILE.exists():  # *.k3s is signed by the krysdom self-signed CA
        ctx.load_verify_locations(cadata=CA_FILE.read_bytes())
    return ctx


def _call(method, url, token=None, body=None, form=None):
    headers = {}
    data = None
    if token:
        headers["Authorization"] = "Bearer " + token
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if form is not None:
        data = urllib.parse.urlencode(form).encode()
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=60, context=_context()) as response:  # noqa: S310
            return response.status, json.loads(response.read() or b"null")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode(errors="replace")[:500]


def token(env):
    status, data = _call("POST", env["IOT_REGISTRY_TOKEN_URL"], form={
        "grant_type": "client_credentials",
        "client_id": env["IOT_REGISTRY_PUBLISHER_CLIENT_ID"],
        "client_secret": env["IOT_REGISTRY_PUBLISHER_CLIENT_SECRET"],
    })
    if status != 200:
        sys.exit("token request failed: %s %s" % (status, data))
    return data["access_token"]


def latest_build(env, access):
    """Highest build ever published, yanked ones included (builds never repeat)."""
    status, data = _call("GET", "%s/apps/%s/releases" % (env["IOT_REGISTRY_OTA_URL"], APP), token=access)
    if status == 404:
        sys.exit("app %s is not registered in iot-registry" % APP)
    if status != 200:
        sys.exit("listing releases failed: %s %s" % (status, data))
    return max((release["build"] for release in data), default=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--notes", default="", help="short changelog line (shown on Telegram)")
    parser.add_argument("--build", type=int, help="build number (default: newest + 1)")
    parser.add_argument("--upload", action="store_true", help="publish (default: dry run)")
    args = parser.parse_args(argv)

    key = load_key()
    builder.main()
    files = bundle_files()
    env = load_env()
    access = token(env)
    build = args.build or latest_build(env, access) + 1
    config = runpy.run_path(str(ROOT / "config.py"))
    manifest = make_manifest(files, build, config["VERSION"], args.notes)
    signature = sign(manifest, key)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "manifest.json").write_bytes(manifest)
    (OUT / "manifest.sig").write_text(signature + "\n")
    total = sum(len(d) for _, d in files)
    print("%s %s build %d: %d files, %d bytes -> %s" % (APP, config["VERSION"], build, len(files), total, OUT))
    if not args.upload:
        print("dry run; add --upload to publish (every device installs it automatically)")
        return 0

    status, data = _call("POST", "%s/apps/%s/releases" % (env["IOT_REGISTRY_OTA_URL"], APP), token=access, body={
        "manifest": base64.b64encode(manifest).decode(),
        "signature": signature,
        "files": {hashlib.sha256(d).hexdigest(): base64.b64encode(d).decode() for _, d in files},
    })
    print("publish:", status, data)
    return 0 if status == 201 else 1


if __name__ == "__main__":
    sys.exit(main())
