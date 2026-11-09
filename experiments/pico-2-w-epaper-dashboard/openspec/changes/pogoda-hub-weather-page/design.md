## Context

Pico W, MicroPython 1.23.0 with the dashboard frozen into flash; ~107 KB GC
heap free after boot; full panel refresh ~16 s; refresh hourly and on key
press. The hub contract (payload and `PHM1` map format) is owned by krysdom-api
`openspec/changes/archive/2026-11-09-pogoda-hub/design.md`.

## Decisions

- **Hub first, Open-Meteo fallback.** `weather.fetch` tries the hub; on any
  error it fetches Open-Meteo as before (the fallback has no wind blocks,
  warnings or synop; the page degrades to current wind/gusts). The UTC offset
  comes from the hub's local `now` and the HTTP `Date` header (15-min steps).
- **Plain HTTP to the hub.** TLS costs ~1.2–1.6 s and heap per request on this
  board; the data is public and the hub serves `/v1` without a redirect. The
  board can verify the internal CA (`certs/k3s-ca.der`) if this changes.
- **Map streamed to flash, never held in RAM.** `http_client.get_to_file`
  writes the 25,016 B body in 1 KB chunks to `/map.bin.tmp`, validates magic,
  size and geometry, then renames. `If-None-Match` makes the hourly check a
  304. `synmap.blit` `readinto`s each plane straight into the canvas buffers
  (both are panel-native: 50 B rows, MSB-first, 0 = ink).
- **Map check cadence.** At most every 30 min, forced on the hourly refresh;
  a failure keeps the cached file and never fails the frame.
- **Layout** follows the design canvas in device pixels; deviation: the info
  band starts at x 16 (the key markers occupy x 0–11), and the XL font is
  24×36 (ink crop) instead of 24×40.
- **Default page.** `PAGES[0]` is the weather page; `app.py` boots on page 0.

## Verification (2026-11-09, on hardware)

- Host: 40 tests pass (`python3 -m unittest discover -s tools -p 'test_*.py'`).
- Firmware built and flashed; boot frame ok, version 0.3.0, heap free 107 KB.
- `show_page.py` drew the weather page (hub data) and the map page on the
  panel (15.8 s refresh each); `/map.bin` 25,016 B with the hub ETag; after a
  reset the boot check returned 304 (`dashboard_map_fetches{result="unchanged"}`).
