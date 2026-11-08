#!/usr/bin/env bash
# Flash a UF2 to the Pico W without pressing BOOTSEL.
#
#   firmware/flash.sh                                   # firmware/out/firmware-dashboard.uf2
#   firmware/flash.sh backups/RPI_PICO_W-20240602-v1.23.0.uf2   # roll back to stock
#
# The app is interrupted (one maintenance boot), machine.bootloader() exposes
# the RPI-RP2 drive and the UF2 is copied to it; the board then reboots into
# the new firmware.  The LittleFS region (top 848 KB) is not touched, so
# main.py, config, secrets and certs survive.  If anything goes wrong, hold
# BOOTSEL while plugging in USB and copy the stock UF2 to RPI-RP2 by hand.
set -euo pipefail
cd "$(dirname "$0")/.."

UF2=${1:-firmware/out/firmware-dashboard.uf2}
MP=.venv/bin/mpremote
PORT=${PORT:-$($MP connect list | awk '/MicroPython/ {print $1; exit}')}
VOLUME=/Volumes/RPI-RP2
[ -f "$UF2" ] || { echo "Missing $UF2 (run firmware/build.sh)"; exit 1; }
[ -n "$PORT" ] || { echo "No MicroPython board found"; exit 1; }

python3 - "$UF2" <<'EOF'
import struct, sys
data = open(sys.argv[1], "rb").read()
end = 0
for i in range(0, len(data), 512):
    m0, m1, _, addr, size = struct.unpack_from("<IIIII", data, i)
    if (m0, m1) != (0x0A324655, 0x9E5D5157):
        sys.exit("not a UF2 file")
    end = max(end, addr + size)
fs_start = 0x10000000 + 2 * 1024 * 1024 - 848 * 1024
if end > fs_start:
    sys.exit("firmware would overlap the filesystem (0x%x > 0x%x)" % (end, fs_start))
print("UF2 ok: ends at 0x%x, filesystem at 0x%x" % (end, fs_start))
EOF

echo "== Reaching the REPL (maintenance boot)"
for _ in 1 2 3 4; do
  $MP connect "$PORT" exec "print('REPL_OK')" 2>/dev/null | grep -q REPL_OK && break
  sleep 4
done

echo "== Rebooting into the ROM bootloader"
$MP connect "$PORT" exec "import machine; machine.bootloader()" >/dev/null 2>&1 || true
for _ in $(seq 1 30); do [ -d "$VOLUME" ] && break; sleep 1; done
[ -d "$VOLUME" ] || { echo "$VOLUME did not appear"; exit 1; }

echo "== Copying $UF2"
# -X: macOS extended attributes make a plain cp fail on the RP2 drive.  The
# drive ejects itself when done, which may race cp's final close.
cp -X "$UF2" "$VOLUME/" || [ ! -d "$VOLUME" ] || { echo "copy to $VOLUME failed"; exit 1; }
for _ in $(seq 1 30); do [ -e "$PORT" ] && break; sleep 1; done
[ -e "$PORT" ] && echo "== Board is back on $PORT (the app starts on its own)" \
  || { echo "Serial port did not come back"; exit 1; }
