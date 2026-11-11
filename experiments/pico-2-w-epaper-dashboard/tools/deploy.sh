#!/usr/bin/env bash
# Install the dashboard on the Pico (2) W so it starts on every power-up.
#
#   tools/deploy.sh            # from experiments/pico-2-w-epaper-dashboard
#   PORT=/dev/cu.usbmodem101 tools/deploy.sh   # required with 2+ boards
#
# Steps: interrupt the running app (it reboots into one maintenance boot with
# no watchdog), back up the board's current :main.py into backups/ (verified),
# build precompiled .mpy files (tools/build.py), copy build/ only, then reset
# so the dashboard starts on its own.
# Never run two mpremote processes at once: serial access is exclusive.
set -euo pipefail
cd "$(dirname "$0")/.."

MP=.venv/bin/mpremote
if [ -z "${PORT:-}" ]; then
  ports=$($MP connect list | awk '/MicroPython/ {print $1}')
  [ "$(printf '%s\n' "$ports" | grep -c .)" = 1 ] \
    || { echo "Need exactly one MicroPython board or PORT=<port>:"; $MP connect list | grep MicroPython; exit 1; }
  PORT=$ports
fi
[ -f secrets.py ] || { echo "secrets.py missing (copy secrets.example.py)"; exit 1; }

wait_port() {
  for _ in $(seq 1 40); do [ -e "$PORT" ] && return 0; sleep 0.5; done
  echo "Board did not re-enumerate on $PORT"; exit 1
}

in_maintenance() {
  $MP connect "$PORT" exec "import os; print('MAINT_OK')" 2>/dev/null | grep -q MAINT_OK
}

echo "== Entering maintenance mode on $PORT"
if ! in_maintenance; then
  # The Ctrl-C from mpremote makes an armed app reboot into maintenance.
  sleep 3; wait_port
  in_maintenance || { sleep 3; wait_port; in_maintenance; } || {
    echo "Could not reach the REPL. Hold KEY0 while plugging in USB and retry."; exit 1; }
fi

echo "== Backing up :main.py"
mkdir -p backups
stamp=$(date +%Y%m%d-%H%M%S)
if $MP connect "$PORT" fs cp :main.py "backups/pico-w-main-$stamp.py"; then
  $MP connect "$PORT" exec "import os; print(os.stat('main.py')[6])" | tr -d '\r' > /tmp/.pico_size.$$
  local_size=$(wc -c < "backups/pico-w-main-$stamp.py" | tr -d ' ')
  [ "$(cat /tmp/.pico_size.$$)" = "$local_size" ] || { echo "Backup size mismatch; aborting"; exit 1; }
  rm -f /tmp/.pico_size.$$
  echo "   backups/pico-w-main-$stamp.py ($local_size bytes, verified)"
fi

echo "== Building precompiled tree"
.venv/bin/python tools/build.py

echo "== Copying build/ to the board"
$MP connect "$PORT" exec "
import os
for d in ('lib', 'certs'):
    try: os.mkdir(d)
    except OSError: pass
for f in ('maint', 'config.py'):  # stale flag; config now ships as .mpy
    try: os.remove(f)
    except OSError: pass
import sys
sys.path.append('lib')
mods = ('app buttons canvas clock epd42b font_large font_medium font_small http_client icons '
        'metrics net pages store strings_pl supervisor telemetry timeutil weather').split()
for m in mods:  # a stale lib/x.py would shadow the new lib/x.mpy
    try: os.remove('lib/' + m + '.py')
    except OSError: pass
"
# With the dashboard firmware (firmware/build.sh + firmware/flash.sh) lib/ is
# compiled into flash and wins over /lib, so only config, secrets, certs and
# the main.py shim are copied; stale lib/*.mpy copies are removed.
# Probe with strings_pl: it imports nothing, so this works on a fresh board
# before config.mpy exists (app imports config).
frozen=$($MP connect "$PORT" exec "
import sys
sys.path.append('lib')
try:
    import strings_pl
    print('FILES' if '/' in strings_pl.__file__ else 'FROZEN')
except ImportError:
    print('FILES')" 2>/dev/null | tr -d '\r' | tail -1)
echo "   board firmware: $frozen"
args=()
while IFS= read -r f; do
  if [ "$frozen" = FROZEN ] && [[ "$f" == lib/* ]]; then continue; fi
  args+=(fs cp "build/$f" ":$f" +)
done < <(cd build && find . -type f ! -name main.py | sed 's|^\./||' | sort)
if [ "$frozen" = FROZEN ]; then
  $MP connect "$PORT" exec "
import os
for f in os.listdir('lib'):
    if f.endswith('.mpy'):
        os.remove('lib/' + f)"
fi
# main.py last: until it lands, the previous program still boots.
$MP connect "$PORT" "${args[@]}" fs cp build/main.py :main.py

echo "== Resetting; first frame appears after ~60 s"
$MP connect "$PORT" exec "import sys; sys.path.append('lib'); import supervisor; supervisor.reset('DEPLOY')" 2>/dev/null || true
