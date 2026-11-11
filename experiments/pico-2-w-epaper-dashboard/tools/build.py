"""Build the on-board file tree in ``build/`` with precompiled ``.mpy`` modules.

Compiling ~100 KB of source on the Pico at boot leaves the heap too
fragmented for the 26 KB TLS handshake used by the OTLP export.  Shipping
bytecode compiled on the host avoids that.  ``mpy-cross`` must match the
board firmware (MicroPython 1.29.0 on the Pico 2 W, mpy v6).

    .venv/bin/python tools/build.py
    .venv/bin/mpremote mount build run build/main.py    # try without installing
    tools/deploy.sh                                      # install (uses build/)
"""

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
MPY_CROSS = [sys.executable, "-m", "mpy_cross"]
MPY_VERSION = "1.29.0"  # firmware/build.sh MPY_TAG

# Runtime modules only (bring-up/diagnostic helpers are not shipped). Keep in
# sync with firmware/manifest.py (tools/test_ota.py checks it).
LIBS = [
    "app", "buttons", "canvas", "clock", "epd42b", "font_large", "font_medium",
    "font_small", "font_xlarge", "http_client", "icons", "metrics", "net", "ota",
    "otaboot", "pages", "store", "strings_pl", "supervisor", "synmap", "telemetry",
    "timeutil", "weather",
]
# Frozen-only boot/update code: never part of an OTA bundle.
OTA_PROTECTED = ("ota", "otaboot")


def main():
    if not (ROOT / "secrets.py").exists():
        sys.exit("secrets.py missing: copy secrets.example.py and fill it in")
    if BUILD.exists():
        shutil.rmtree(BUILD)
    (BUILD / "lib").mkdir(parents=True)
    (BUILD / "certs").mkdir()

    version = subprocess.run(MPY_CROSS + ["--version"], capture_output=True, text=True)
    print(version.stdout.strip() or version.stderr.strip())
    if "v" + MPY_VERSION not in version.stdout + version.stderr:
        sys.exit("mpy-cross must be %s to match the board (pip install -r requirements.txt)" % MPY_VERSION)

    for name in LIBS:
        subprocess.run(
            MPY_CROSS + ["-o", str(BUILD / "lib" / (name + ".mpy")), str(ROOT / "lib" / (name + ".py"))],
            check=True,
        )
    subprocess.run(MPY_CROSS + ["-o", str(BUILD / "config.mpy"), str(ROOT / "config.py")], check=True)
    # main.py must stay source (the firmware runs main.py); it is a 3-line shim.
    shutil.copy(ROOT / "main.py", BUILD / "main.py")
    shutil.copy(ROOT / "secrets.py", BUILD / "secrets.py")
    shutil.copy(ROOT / "certs" / "k3s-ca.der", BUILD / "certs" / "k3s-ca.der")

    total = sum(p.stat().st_size for p in BUILD.rglob("*") if p.is_file())
    print("build/: %d files, %d bytes" % (len(list(BUILD.rglob("*.*"))), total))


if __name__ == "__main__":
    main()
