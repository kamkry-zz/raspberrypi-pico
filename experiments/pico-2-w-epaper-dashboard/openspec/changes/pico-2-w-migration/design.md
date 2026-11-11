## Context

The Pico 2 W keeps the Pico W pinout, the CYW43439 radio and its driver, so
the panel driver, SPI pins (GP8–GP13), keys (GP15/GP17) and Wi-Fi code are
unchanged. What differs is the chip (RP2350, Cortex-M33 at 150 MHz), the
register map, flash size and the minimum MicroPython version.

## Decisions

- **MicroPython v1.29.0** (latest stable on 2026-11-11). Same `.mpy` format
  (v6.3) as 1.23, but `mpy-cross` stays pinned to the firmware version.
- **Frozen firmware kept** even though 520 KB SRAM would fit the source tree:
  frozen bytecode runs from flash, so most of the heap stays free for TLS
  and the canvas.
- **Watchdog scratch base by chip** rather than a new constant: one code base
  runs on both boards, so the Pico W stays a working cold spare.
- **New name and address** (`raspberry-pi-pico-2-wh-02.iot`, `.52`), so both
  boards can be online during preparation; the old reservation stays.
- RP2350 A2 erratum E9 (pull-down latch) does not apply: BUSY and the keys use
  pull-ups and are driven or pulled high.

## Verified on the Pico 2 W (headless, panel still on the Pico W)

- MAC `98:fe:54:1a:80:d7`; joins `krys_dom_IoT` in ~4.6 s, RSSI −40 dBm,
  DHCP reservation `.52` applied.
- Watchdog scratch 0/1 at `0x400D8000` survive `machine.reset()` (scratch 2/3
  are used by the boot ROM); reset cause reads `DEPLOY`.
- `ADC(4)` is the die sensor (same formula); `ssl.SSLContext` and
  `ssl.wrap_socket` present; `reset_cause` constants match.
- Full refresh cycle: hub weather OK (515 ms), map downloaded, render 1.0 s,
  `/healthz` and `/metrics` served; heap free ~362 KB.
