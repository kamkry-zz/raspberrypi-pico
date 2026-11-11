#!/usr/bin/env bash
# Flash a UF2 to a running Pico W / Pico 2 W without pressing BOOTSEL.
#
#   firmware/flash.sh                                        # firmware/out/firmware-dashboard-RPI_PICO2_W.uf2
#   PORT=/dev/cu.usbmodem101 firmware/flash.sh <file.uf2>    # explicit board
#   firmware/flash.sh backups/RPI_PICO2_W-20260824-v1.29.0.uf2   # roll back to stock
#
# PORT is required when more than one MicroPython board is connected.
# The app is interrupted (one maintenance boot), machine.bootloader() exposes
# the ROM drive (RPI-RP2 on the RP2040, RP2350 on the RP2350) and the UF2 is
# copied to it; the board then reboots into the new firmware.  The LittleFS
# region at the top of flash is not touched, so main.py, config, secrets and
# certs survive.  If anything goes wrong, hold BOOTSEL while plugging in USB
# and copy the stock UF2 to the drive by hand (cp -X).
set -euo pipefail
cd "$(dirname "$0")/.."

UF2=${1:-firmware/out/firmware-dashboard-RPI_PICO2_W.uf2}
MP=.venv/bin/mpremote
[ -f "$UF2" ] || { echo "Missing $UF2 (run firmware/build.sh)"; exit 1; }
if [ -z "${PORT:-}" ]; then
  ports=$($MP connect list | awk '/MicroPython/ {print $1}')
  [ "$(printf '%s\n' "$ports" | grep -c .)" = 1 ] \
    || { echo "Found $(printf '%s\n' "$ports" | grep -c .) MicroPython boards; set PORT=<port>:"; $MP connect list | grep MicroPython; exit 1; }
  PORT=$ports
fi
SERIAL=$($MP connect list | awk -v p="$PORT" '$1 == p {print $2}')

# Check the UF2 targets one chip and stays below that board's filesystem.
read -r CHIP VOLUME < <(python3 - "$UF2" <<'PY'
import struct, sys
data = open(sys.argv[1], "rb").read()
# family id -> (chip, ROM drive, flash bytes, MicroPython LittleFS bytes)
BOARDS = {
    0xE48BFF56: ("RP2040", "RPI-RP2", 2 * 1024 * 1024, 848 * 1024),
    0xE48BFF59: ("RP2350", "RP2350", 4 * 1024 * 1024, 2560 * 1024),
}
ABSOLUTE = 0xE48BFF57  # RP2350-E10 workaround block, not real flash content
end, families = 0, set()
for i in range(0, len(data), 512):
    m0, m1, flags, addr, size, _, _, family = struct.unpack_from("<8I", data, i)
    if (m0, m1) != (0x0A324655, 0x9E5D5157):
        sys.exit("not a UF2 file")
    if flags & 0x2000 and family == ABSOLUTE:
        continue
    families.add(family if flags & 0x2000 else None)
    end = max(end, addr + size)
known = families & set(BOARDS)
if len(known) != 1:
    sys.exit("unexpected UF2 families: %s" % sorted(hex(f) for f in families if f))
chip, volume, flash, fs = BOARDS[known.pop()]
fs_start = 0x10000000 + flash - fs
if end > fs_start:
    sys.exit("firmware would overlap the filesystem (0x%x > 0x%x)" % (end, fs_start))
print("UF2 ok for %s: ends at 0x%x, filesystem at 0x%x" % (chip, end, fs_start), file=sys.stderr)
print(chip, volume)
PY
)
VOLUME=/Volumes/$VOLUME

echo "== Reaching the REPL on $PORT (maintenance boot)"
ok=
for _ in 1 2 3 4; do
  out=$($MP connect "$PORT" exec "import sys; print('REPL_OK', sys.implementation._machine)" 2>/dev/null || true)
  if printf '%s' "$out" | grep -q REPL_OK; then ok=1; break; fi
  sleep 4
done
[ -n "$ok" ] || { echo "Could not reach the REPL on $PORT"; exit 1; }
printf '%s' "$out" | grep -q "$CHIP" \
  || { echo "Board on $PORT is not an $CHIP: $(printf '%s' "$out" | tr -d '\r')"; exit 1; }

echo "== Rebooting into the ROM bootloader"
$MP connect "$PORT" exec "import machine; machine.bootloader()" >/dev/null 2>&1 || true
for _ in $(seq 1 30); do [ -d "$VOLUME" ] && break; sleep 1; done
[ -d "$VOLUME" ] || { echo "$VOLUME did not appear"; exit 1; }

echo "== Copying $UF2"
# -X: macOS extended attributes make a plain cp fail on the ROM drive.  The
# drive ejects itself when done, which may race cp's final close.
cp -X "$UF2" "$VOLUME/" || [ ! -d "$VOLUME" ] || { echo "copy to $VOLUME failed"; exit 1; }
for _ in $(seq 1 30); do
  $MP connect list | grep -q "$SERIAL" && break; sleep 1
done
NEWPORT=$($MP connect list | awk -v s="$SERIAL" '$2 == s {print $1}')
[ -n "$NEWPORT" ] && echo "== Board $SERIAL is back on $NEWPORT (the app starts on its own)" \
  || { echo "Board $SERIAL did not come back"; exit 1; }
