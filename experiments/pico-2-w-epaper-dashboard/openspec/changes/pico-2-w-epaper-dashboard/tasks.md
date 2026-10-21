## 1. Scaffold and sources

- [x] 1.1 Create `experiments/pico-2-w-epaper-dashboard/` with config, `secrets.example.py`, `.gitignore`, pinned `requirements.txt`, and an experiment-local OpenSpec root.
- [x] 1.2 Mirror the old 4.2-B manual, V2 manual and module schematic under `docs/datasheets/` with SHA-256 checksums and source URLs.
- [x] 1.3 Write the curated hardware document with specs, pinout, old/V2 commands, refresh behaviour and measured timings.

## 2. Driver and bring-up

- [x] 2.1 Implement the 0x2F revision probe and both legacy and V2 init sequences.
- [x] 2.2 Implement the vendor init+clear sequence; verify that it is required before the first frame on this panel.
- [x] 2.3 Implement native dual-plane transfer (MSB-first, red 0 = red) with block black/red planes and direct SPI writes.
- [x] 2.4 Implement BUSY handling with a 24 s fallback and expose init/transfer/panel/total timings.
- [x] 2.5 Verify a colour bring-up frame on the physical panel and record 604–705 ms init and 15.8–23.2 s full refresh.
- [x] 2.6 Implement the KEY0/GP15 and KEY1/GP17 button path with debounce, short/long press and direct polling.
- [x] 2.7 Confirm the physical module switches on hardware. Verified: KEY0/GP15 and KEY1/GP17 change pages (1/5 → 5/5), with both short and long events in the live log. The panel is not touch.

## 3. Canvas, fonts and preview

- [x] 3.1 Implement the pure-Python dual-plane canvas and verify byte-for-byte equality with `framebuf.MONO_HLSB` for a reference frame.
- [x] 3.2 Generate IBM Plex Mono Polish bitmap fonts (small, medium, and a numeric large subset) with OFL attribution.
- [x] 3.3 Add the stdlib PNG writer, deterministic fixtures and host preview for all pages.
- [x] 3.4 Add unit tests for time/year maths, weather parsing, canvas packing and page rendering.

## 4. Network, time and weather

- [x] 4.1 Connect only to `krys_dom_IoT`, set the DHCP hostname, and expose IP/MAC/SSID/RSSI/status.
- [x] 4.2 Implement DNS PTR discovery plus forward verification; verify `raspberry-pi-pico-w-01.iot` against `192.168.4.51`.
- [x] 4.3 Implement NTP with an HTTP `Date` fallback and Open-Meteo `utc_offset_seconds`/EU DST fallback.
- [x] 4.4 Implement the HTTPS/HTTP weather client, parser, 10-minute cache, stale handling and WMO Polish descriptions.

## 5. Dashboard

- [x] 5.1 Build the year-in-pixels grid and percentage, weather summary, network and system rows.
- [x] 5.2 Build Weather, Network, Capabilities and About pages with the full DNS name and refresh telemetry.
- [x] 5.3 Implement the hourly top-of-the-hour schedule, button refresh, optional nightly clear and offline rendering.
- [x] 5.4 Fit the dashboard and fonts within the RP2040 heap by allocating the canvas before the clear and using the large-font subset.
- [x] 5.5 Verify all five pages on the physical panel and increase the small font to 7×15 for readability.
- [x] 5.6 Draw red `<`/`>` key hints at the physical KEY0/KEY1 heights on every page and remove the old year caption/red rule.
- [x] 5.7 Make any button press navigate (remove the long-press ambiguity), add the raw GP15/GP17 and full free-GPIO diagnostics, and document the side-switch location.
- [x] 5.8 Stream canvas/driver plane clears in 256-byte chunks to remove the 15 KB temporary that caused an intermittent `MemoryError` after a weather fetch.

## 6. Capability demo

- [x] 6.1 Add `demo.py` with the bring-up pattern, a 16-level dither chart and the capabilities page; no Wi-Fi required.

## 7. Documentation and validation

- [x] 7.1 Write README, dashboard, weather, third-party and datasheet documentation.
- [x] 7.2 Update root `AGENTS.md` with the new experiment, panel revision, IoT WLAN, DNS name and safety rules.
- [x] 7.3 Validate the OpenSpec change with `openspec validate pico-2-w-epaper-dashboard --strict`.
- [ ] 7.4 Optional: connect external GP15/GP17 switches; the module's own side switches are already verified.
