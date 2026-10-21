## Context

The panel is a Waveshare Pico-ePaper-4.2-B plugged onto a Pico W running
MicroPython 1.23.0. Verified facts:

- 400 × 300, red/black/white, no true grayscale.
- This unit probes as the **old revision** (`0x2F` reads `0xFF`); the legacy
  `0x10`/`0x13`/`0x12` command set is used.
- The module's working legacy program always runs `Init()` + `Clear()` before
  drawing. Without the clear the panel retained the previous image.
- Full refresh is 14 s in the V2 datasheet, 15 s in the wiki, and measured at
  15.8–23.2 s here.
- The panel's BUSY line is unreliable for the old revision; the vendored
  `ReadBusy()` waits when it sees a low pulse, otherwise a fixed fallback is
  needed.
- The frame must fit in the RP2040 heap together with Wi-Fi/TLS/JSON. The two
  15 KB canvas planes must be allocated before the panel clear and the network
  stack.
- Wi-Fi is the dedicated `krys_dom_IoT` network; DHCP has a static reservation
  for MAC `28:cd:c1:0d:34:f0`; the PTR lookup discovers
  `raspberry-pi-pico-w-01.iot`.

The user asked for a Pico-only dashboard (no Raspberry Pi agent), a red/black/
white design, no clock, hourly refresh plus buttons, Polish UI, Łódź weather,
and a small capability demo.

## Goals / Non-Goals

**Goals:**

- A reliable driver for this exact panel revision, with measured timings and a
  documented init/clear sequence.
- A readable, dense dashboard using all three colours, the year grid, weather,
  network and system metrics.
- A host preview and unit tests that do not need the panel.
- Local, curated hardware documentation and mirrored source PDFs.
- Non-destructive verification: no writes to the board's existing program.

**Non-Goals:**

- A live clock or partial refresh.
- True grayscale or a Raspberry Pi host agent.
- Replacing the board's school-timetable program by default.
- A web server or cloud service.

## Decisions

- **Vendor sequence, not a clean-room rewrite.** The final driver keeps the
  proven `Init()` / `Clear()` / `Display()` order. This was necessary on the
  old panel; purely idiomatic reimplementations failed during bring-up.
- **Block red transfer.** The vendor display sends the red plane byte-by-byte
  (~18 s); the driver sends both planes as blocks (88 ms transfer), verified
  visually on this unit. The vendor clear still uses block planes.
- **Init+clear once, panel stays awake.** Sleeping would require another
  clear/wake waveform. The hourly refresh writes a new full frame without
  re-initialising.
- **No clock, hourly refresh.** 15.8–23.2 s per frame makes a minute clock
  impractical. Refresh at the top of the hour (+5 s); buttons force a refresh.
- **Pico-only data.** No Pi agent. `loadavg` is replaced by an honest
  “Aktywny” interval duty figure. The full DNS name is discovered with a PTR
  lookup because the Pico cannot read the router's zone.
- **Polish UI, English docs.** Repo docs and OpenSpec stay in English; the
  panel and weather are Polish.
- **Portable canvas + host preview.** A pure-Python MSB-first canvas is shared
  by device and host. It was verified byte-for-byte against
  `framebuf.MONO_HLSB` on the board.
- **Font subset for the large size.** The large font contains only the
  characters used at that size, saving ~20 KB of heap.
- **Secrets only in `secrets.py`.** SSID in config, password gitignored.
- **Run-only default.** `mpremote mount . run main.py`; deploy only on explicit
  request with a backup of `main.py` and `lib/`.

## Risks / Trade-offs

- **Long refresh / no clock** → hourly schedule, explicit “Akt.” timestamp.
- **BUSY unreliability** → measured `ReadBusy()` plus a 24 s fallback; the
  Capabilities page shows the real duration.
- **Heap fragmentation** → canvas before clear/network, `gc.collect()`, large
  font subset, direct `send_data1`, 256-byte chunked plane fills (avoids a
  15 KB temporary that caused an intermittent `MemoryError` after a fetch).
- **Physical buttons** → verified on the module: KEY0/GP15 previous, KEY1/GP17
  next; the panel is not touch; external switches are optional; hourly refresh
  independent.
- **IoT VLAN** → must allow DNS and outbound weather; no fallback network.
- **TLS / NTP** → HTTPS with HTTP fallback; HTTP `Date` time fallback.
- **Ghosting** → hourly full refresh; optional nightly clear off by default.
- **Long DNS name** → short DHCP name on the dashboard, full name on Network
  and About.

## Migration Plan

1. Create the experiment directory and OpenSpec root (done).
2. Verify the panel with the vendor sequence and record timings (done).
3. Build the canvas/fonts/preview and pages (done).
4. Wire Wi-Fi, DNS PTR, NTP/HTTP-Date and Open-Meteo (done).
5. Run one-frame and loop tests; verify the side switches (KEY0/GP15
   previous, KEY1/GP17 next) and document the non-touch hints (done).
6. Finish docs, tests, OpenSpec validation (this change).
7. Optional: connect external GP15/GP17 switches; deploy only with explicit
   approval after backing up the board.
