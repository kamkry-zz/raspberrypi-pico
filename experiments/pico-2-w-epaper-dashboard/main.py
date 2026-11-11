"""Pico W e-paper dashboard entry point (self-starting, watchdog-protected).

Installed on the board as ``:main.py`` it starts on every power-up:

1. arm the hardware watchdog (see ``lib/supervisor.py``);
2. start Wi-Fi association while the panel runs its 24 s vendor clear;
3. sync the clock (NTP, HTTP ``Date`` fallback), fetch Open-Meteo, display;
4. refresh at the top of every hour; while offline, retry the network with
   backoff and redraw only once fresh data is available;
5. push OTLP metrics/logs/traces to observatory.k3s and serve /metrics.

Maintenance (plain REPL, no watchdog) for one boot: press Ctrl-C (mpremote
does this) or hold KEY0 while powering up.  See README "Deploying".

Run from the host without installing:

    .venv/bin/mpremote mount . run main.py
"""

import sys

sys.path.append("lib")

# Pick the code for this boot: an OTA slot (/ota/a|b) or the frozen factory
# image. otaboot is frozen and never shipped over the air; it never raises.
try:
    import otaboot  # noqa: E402

    otaboot.select()
except ImportError:
    pass

import app  # noqa: E402  (OTA slot, frozen firmware or lib/app.mpy)

app.boot()
