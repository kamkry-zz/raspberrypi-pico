## 1. Data

- [x] 1.1 `weather.parse_hub` + hub-first fetch with Open-Meteo fallback; offset from hub `now` + HTTP `Date`.
- [x] 1.2 `http_client.get_to_file` (streamed, `If-None-Match`); `lib/synmap.py` (fetch, validate, info, blit).
- [x] 1.3 `config.py`: hub URLs, map cache files, check cadence, version 0.3.0.

## 2. Pages

- [x] 2.1 XL digit font (`tools/build_fonts.py` spec, generated `lib/font_xlarge.py`).
- [x] 2.2 New Pogoda page per the design canvas (sun arc, 4-hour wind blocks, hours, warnings/synop band, 4 days).
- [x] 2.3 New synoptic map page (blit, Łódź marker, analysis box, legend, attribution).
- [x] 2.4 Pogoda is the default (first) page; map second; 6 pages.
- [x] 2.5 Fixes: small moon crescent, key markers drawn last, short header date.

## 3. Tests and delivery

- [x] 3.1 Host tests: hub parsing, page variants (day/night/warning/stale/fallback), map blit, default page; previews in `docs/images/`.
- [x] 3.2 Firmware rebuilt with the new frozen modules; config deployed with `tools/deploy.sh`; firmware flashed with `firmware/flash.sh`.
- [x] 3.3 On-panel check of both pages; map 304 path verified after reset.
