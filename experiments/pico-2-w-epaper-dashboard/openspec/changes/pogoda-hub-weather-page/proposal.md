## Why

The weather page (12-hour chart, 3 days, current details) answered "what is it
now" but not "how is the day going" or "what is the weather pattern". The user
asked for a page dominated by today's weather with the next hours, a smaller
multi-day forecast, the sun's progress between sunrise and sunset, average wind
and the IMGW synoptic map. The map (740×655 colour PNG, ~730 KB) cannot be
downloaded or decoded on a Pico W, so a LAN hub now does the heavy lifting.

Design canvas (reviewed 2026-11-09): https://claude.ai/artifact/PfMRoe4M9om8C97cGrQJHU

## What Changes

- Weather data from the krysdom-api **pogoda-hub**
  (`http://pogoda-hub.k3s/v1/weather`, ≈3 KB pre-reduced JSON; plain HTTP on the
  LAN by design); Open-Meteo stays as the automatic fallback.
- New **Pogoda** page, now the default page shown at boot: XL temperature
  (new 24×36 digit font), feels-like, the sun's arc with today's progress (or
  time to sunrise at night), mean wind in six 4-hour blocks with direction and
  gusts, the next 8 hours, IMGW warnings for Łódź, the IMGW Łódź synop, and
  the next 4 days.
- New **Mapa synoptyczna** page (second): the hub's 400×250 black/red map
  (`/v1/map.bin`, panel-native planes) streamed to flash (`/map.bin`, ETag/304)
  and copied row by row into the canvas; Łódź marker, analysis time and age,
  legend, IMGW attribution ("dane przetworzone").
- Page order: Pogoda, Mapa, KRYSDOM, Sieć, Możliwości, O programie (6 pages).
- Small fixes: visible crescent for small moon icons; key markers drawn last;
  short date in the header when the title is long.
- Firmware rebuilt (new frozen modules `font_xlarge`, `synmap`); config 0.3.0.

## Impact

- `lib/weather.py`, `lib/pages.py`, `lib/synmap.py` (new), `lib/http_client.py`
  (`get_to_file`), `lib/icons.py`, `lib/strings_pl.py`, `lib/app.py`,
  `lib/font_xlarge.py` (new), `config.py`, `firmware/manifest.py`, tools/tests.
- Depends on krysdom-api `pogoda-hub` (deployed 2026-11-09, PR #1946); flash
  use +28 KB for the cached map.
