## Why

The connected Pico W already drives a Waveshare Pico-ePaper-4.2-B panel as a
school timetable. The panel has a large red/black/white surface but the
existing program only uses a small part of its capability. This experiment
turns it into a self-contained home dashboard for Łódź and documents the panel
properly, without a Raspberry Pi host and without overwriting the existing
board program.

The panel is the **older 4.2-B revision** (0x2F = 0xFF), not the current V2.
It has no partial refresh and no true grayscale; a full frame takes 15.8–23.2 s
on this unit. The design therefore refreshes hourly at the top of the hour,
not every minute, and has no live clock.

## What Changes

- Add `experiments/pico-2-w-epaper-dashboard/` with its own OpenSpec root,
  README, docs, tooling, backups and gitignored secrets.
- Add a verified 4.2-B driver: revision probe, legacy/V2 init, vendor
  init+clear, block plane transfer, BUSY fallback, timings and sleep.
- Add a portable pure-Python dual-plane canvas and Polish bitmap fonts. The
  same layout code runs on the Pico and in the host preview.
- Add dashboard pages: year progress, 3-day weather + 12-hour chart, network
  identity/DNS, system metrics, capabilities/refresh telemetry, about.
- Use Open-Meteo for Łódź, NTP/HTTP-Date time, and DHCP DNS PTR discovery of
  the full DNS name (`raspberry-pi-pico-w-01.iot`), with forward verification.
- Add a standalone `demo.py` capability showcase.
- Add host-rendered PNG previews, deterministic fixtures and stdlib tests.
- Mirror the old 4.2-B manual, V2 manual and schematic with SHA-256 checksums.
- Keep the board program untouched by default via `mpremote mount . run`.

## Capabilities

### New Capabilities

- `epaper-4in2b-driver`: the verified panel sequence, plane encoding, full
  refresh timing, init/clear, BUSY handling and sleep.
- `dashboard`: Pico-only metrics, year progress, Polish weather and network
  pages, hourly refresh and offline behaviour.
- `capability-demo`: the capabilities page and the standalone demo patterns.
- `host-preview`: shared canvas rendering to PNG, fixtures and tests without
  hardware.
- `experiment-safety`: non-destructive runs, secrets handling, WLAN policy and
  deployment rules.

### Modified Capabilities

## Impact

- New files only under `experiments/pico-2-w-epaper-dashboard/`; root
  `AGENTS.md` is updated with the experiment and board/WLAN facts.
- The board's existing `main.py` and `lib/` are not modified by the normal
  `mpremote mount` workflow.
- Runtime: MicroPython 1.23.0, Pico W, `krys_dom_IoT` (2.4 GHz WPA2), Open-Meteo
  (no key), Pico-ePaper-4.2-B old revision.
- The page buttons are wired KEY0/GP15 and KEY1/GP17; verified on this unit:
  KEY0 goes to the previous page, KEY1 to the next. The panel is not touch;
  the printed `<`/`>` markers are visual hints only.
