# Dashboard architecture and behaviour

## Goal

A self-contained Pico W dashboard on a 4.2-inch black/white/red e-paper panel.
No Raspberry Pi agent, no clock (the panel needs ~16–23 s per full refresh), and
no permanent writes to the board's existing program.

## Boot flow

1. Allocate the two 15 KB canvas planes **before** the panel clear and the
   network stack fragment the heap.
2. Load the UI/font modules.
3. Initialise the panel, run the vendor **init + clear** waveform, and wait
   for the waveform (~16–23 s).
4. Connect to `krys_dom_IoT` (2.4 GHz, WPA2).
5. Try NTP; if it fails, use the weather HTTP `Date` header.
6. Resolve the DNS name with a PTR lookup and verify it forward.
7. Fetch Open-Meteo current + 3-day + 12-hour data.
8. Render the dashboard and perform one full refresh.
9. Enter the loop: hourly top-of-the-hour refresh + button events.

`First frame` is the last startup log line. The loop then prints nothing until
a button event or the hourly refresh; silence is normal, not a hang.

First boot is about 45–60 s because the panel clear and the first frame each
cost one full waveform.

## Data sources

### Pico W itself

- IP, netmask, gateway, DNS server from `wlan.ifconfig()`
- SSID, BSSID, channel, RSSI
- MAC address (also needed for the router's static DHCP reservation)
- DHCP hostname from `network.hostname()` (`pico-dash`)
- uptime from `time.ticks_ms()` / `ticks_diff`
- heap free/allocated from `gc.mem_free()` / `gc.mem_alloc()`
- flash used/total from `os.statvfs('/')`
- RP2040 die temperature from `machine.ADC(4)`
- CPU frequency, reset cause, MicroPython release

There is **no Linux load average**. The dashboard shows **Aktywny** — the
percentage of the interval since the previous gather spent in fetch, render and
panel refresh. It is reset after the boot frame so the first hourly value is
not inflated by the initial clear. Treat it as an activity/duty figure, not a
load average.

### DNS name

The DNS name is set in the router, not on the Pico. The driver cannot read the
router's zone. At each refresh:

1. Take the DHCP address.
2. Query the DHCP-provided DNS server for a PTR record of the reversed address.
3. Verify the returned name resolves back to the same address.
4. Fall back to `config.DNS_NAME`, then the DHCP hostname.

On this network the PTR returned
`raspberry-pi-pico-w-01.iot`, verified against `192.168.4.51`. Because that
name is 26 characters, the **dashboard shows the short DHCP name `pico-dash`**
and a check mark; the full DNS name is on the Network and About pages.

### Weather

Open-Meteo, Łódź (`51.7592, 19.4560`), `Europe/Warsaw`, metric units. The API
needs no key. The dashboard shows current conditions, three daily rows and a
12-hour temperature/precipitation chart on the Weather page. See
`weather.md`.

### Weather cache and offline

- The parsed weather dict is cached in RAM for 10 minutes.
- Hourly refreshes force a new fetch; button presses may reuse the cache.
- A failed fetch reuses the cache and marks it `nieaktualne`.
- With no cache the weather panel shows `Brak danych` / `OFFLINE`; the rest of
  the dashboard (clock/date if synced, network, metrics) still renders.
- If Wi-Fi is down, `net.ensure()` retries with a timeout (8 s on button
  refresh, 20 s on boot/hourly). The clock keeps running from its last anchor.

## Time

- NTP (`ntptime.settime()`) is tried at boot and whenever the clock is not yet
  synced.
- The weather HTTP `Date` header is the fallback; it also re-anchors the clock
  on each forced hourly fetch, correcting drift.
- `Clock` keeps a UTC epoch plus a `ticks_ms()` base, and applies the offset
  returned by Open-Meteo (`utc_offset_seconds`). The fallback before weather is
  a small European DST calculation (last Sundays of March/October).
- There is deliberately **no on-screen clock**. The header shows the date;
  the footer shows the last update and the next hourly refresh.

## Refresh policy

- Full refresh only; no partial update.
- Default: every hour at the top of the hour (+5 s), plus a refresh on a button
  press.
- Measured 15.8–23.2 s per full frame on this older unit.
- The panel stays awake between updates; sleeping would require another
  init/clear waveform on this revision.
- `config.NIGHTLY_CLEAR` can add a white clear at 03:00 for ghosting; it is off
  by default. The hourly refresh already satisfies the panel's 24 h advice.

## Pages

| # | Page | Contents |
| --- | --- | --- |
| 1 | KRYSDOM | year grid/percentage, 3-day weather, network, system |
| 2 | Pogoda | current details, 3-day forecast, 12 h chart |
| 3 | Sieć | DHCP/DNS name and verification, IP, mask, gateway, DNS server, MAC, SSID, channel, RSSI, HTTP timing, reset cause, firmware |
| 4 | Możliwości | colour swatches, dither charts, font specimen, geometry, refresh telemetry |
| 5 | O programie | panel facts, refresh policy, button legend, sources, version |

- **KEY0 / GP15** = previous page.
- **KEY1 / GP17** = next page.
- Any press changes the page and refreshes; the hourly refresh refreshes the
  current page.
- Every page shows red `<` and `>` hints in black-outlined white boxes on the
  left edge: `<` at the bottom of the year grid (KEY0 height) and `>` at the
  MAC row (KEY1 height). These are visual hints only; the input path is
  unchanged. The panel has no touch controller, so tapping the markers does
  nothing.
- If a unit's switches do not respond, `button_diag.py` prints the raw
  GP15/GP17 levels; `pin_scan.py` scans all free GPIOs in both pull-up and
  pull-down modes. The annotated side-switch location is
  `docs/images/button-location.jpg`.
- The two switches are the side-actuated tactile switches on the **left PCB
  edge** and are wired to GND. They are **verified on this unit**: pressing
  KEY0 (GP15) or KEY1 (GP17) changes the page and refreshes; the live log shows
  both short and long events. The panel is not touch. External momentary
  switches between GP15/GP17 and GND also work. The hourly refresh is
  independent of the buttons. If a unit's switches are unavailable, edit
  `PAGE` in `show_page.py` and run it to display one page directly.

## Rendering and memory

- `lib/canvas.py` is a pure-Python dual-plane 1-bit canvas. It runs unchanged
  on the Pico and in `tools/preview.py`.
- Plane order: MSB first, 50 bytes/row, native red encoding (0 = red).
- Fonts: IBM Plex Mono, Regular 11 px (small), SemiBold 14 px (medium), and a
  SemiBold 24 px **subset** for digits, comma, percent, degree, `C`, `minus`
  and `×`. The subset saves about 20 KB of heap.
- The canvas (30 KB) is allocated before the panel clear. The UI/font modules
  are loaded after a `gc.collect()`; the driver writes planes directly without
  a 15 KB copy. This order was required to fit the RP2040 heap reliably.
- Plane clears are streamed in 256-byte chunks in both `Canvas.clear()` and the
  driver clear. A long button session once hit `MemoryError` on a 15 KB
  temporary after a weather fetch; chunked fills remove that allocation.
- Dithering: ordered 4×4 Bayer; there is no true grayscale on this panel.

## Configuration

`config.py` contains the SSID (`krys_dom_IoT`), location, refresh policy, pin
map and UI options. `secrets.py` contains only the Wi-Fi password and is
gitignored. `RUN_ONCE = True` is a one-frame hardware test switch; leave it
`False` for the normal loop.

## Preview and tests

```sh
python3 tools/preview.py --frame all --scale 2   # host PNGs, no panel
python3 -m unittest discover -s tools -p 'test_*.py'
```

The preview uses the same canvas/pages/fonts and a deterministic fixture. It is
much faster than a 16–23 s hardware refresh and is the recommended way to
iterate on layout.

## Known limitations

- No partial refresh and no true grayscale; red is the third colour.
- 15.8–23.2 s per full frame; no live clock.
- First boot has two full waveforms (clear + dashboard).
- The panel is not touch; page changes use the side switches (verified).
- The panel must be initialised and cleared before the first frame; the driver
  does this automatically.
- TLS certificate verification is not pinned; weather data is public and the
  client falls back to HTTP if the handshake fails.
- The IoT WLAN must allow DNS and outbound HTTP/HTTPS; NTP is optional.
