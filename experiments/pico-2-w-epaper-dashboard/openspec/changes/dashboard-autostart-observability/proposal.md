## Why

On power-up the board ran the stored LED-blink program, not the dashboard: the
dashboard had only ever been run from the host with `mpremote mount`. The panel
therefore never refreshed after a power cut, and nothing recovered the board
from a hang, a Wi-Fi outage at boot (the router often comes back after the
Pico) or a crash. The device was also invisible to observatory.k3s.

## What Changes

- Install the dashboard as the board's `:main.py` (tiny shim) plus precompiled
  `lib/*.mpy`, built by `tools/build.py` (mpy-cross 1.23.0) and installed by
  `tools/deploy.sh` (maintenance entry, verified backup, copy, tagged reset).
- Add `lib/supervisor.py`: hardware watchdog fed from a soft timer only while
  the app heartbeats; one-boot maintenance mode (Ctrl-C or KEY0 held at
  power-up); crash backoff (30 s → 15 min); tagged deliberate resets.
- Start Wi-Fi association during the 24 s panel clear; re-initialise the radio
  after repeated failures and reboot after 12; retry offline refreshes with
  backoff and redraw only once fresh data arrives.
- Persist the last good weather atomically (`lib/store.py`, tmp + rename) and
  show it as stale when a boot has no network.
- Set the RTC from the HTTP `Date` header when NTP fails.
- Bound the e-paper BUSY wait (45 s) so a stuck line raises instead of hanging.
- Add `lib/telemetry.py`: Prometheus `/metrics` and `/healthz` on :9100, and
  an OTLP/HTTP JSON exporter (metrics, logs, refresh traces) to
  `https://otel.k3s`, CA-verified, **disabled by default** (heap, see design).
- observatory.k3s (krysdom-api repo, separate delivery): `prometheus/apps`
  scrape job `pico-epaper-dashboard`.
- Free the board flash: ~600 KB of unused CPython/Adafruit packages in `/lib`
  were backed up to `backups/pico-w-lib-20261108/` and removed.

## Impact

- Board `:main.py` is now the dashboard; previous program backed up in
  `backups/`. Connecting `mpremote` interrupts the app and reboots it into one
  maintenance boot.
- Weather is fetched over plain HTTP (public data) to keep heap for the app.
