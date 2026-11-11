## Why

The dashboard ran on a Pico W (RP2040, 264 KB SRAM, 2 MB flash) on
MicroPython 1.23.0. With the frozen firmware it had ~113 KB of heap; TLS
(OTLP push) only fits after freezing, and source runs hit MemoryError. The
user moved it to a **Raspberry Pi Pico 2 WH** (RP2350, 520 KB SRAM, 4 MB flash,
same CYW43439 radio, same pinout, pre-soldered headers) that plugs into the
same Pico-ePaper-4.2-B socket. Downtime is acceptable.

## What Changes

- Firmware: MicroPython **v1.29.0** for `RPI_PICO2_W` (the RP2350 needs ≥1.25)
  with `lib/` frozen; `firmware/build.sh` takes `MPY_TAG`/`BOARD` (default
  v1.29.0/RPI_PICO2_W, old Pico W build still reproducible) and caches per tag.
- `mpy-cross` pinned to 1.29.0 (`requirements.txt`, `tools/build.py` check).
- `lib/supervisor.py`: the watchdog block moved (RP2040 `0x40058000`, RP2350
  `0x400D8000`); on the RP2350 the old address is the **USB PLL**, so the
  scratch-register base is chosen from `sys.implementation._machine`.
- `firmware/flash.sh`: RP2350 ROM drive (`RP2350`), 4 MB flash / 2560 KB
  LittleFS layout, ignores the RP2350-E10 absolute block, refuses a UF2 for
  the wrong chip, needs `PORT` with more than one board connected and follows
  the board by USB serial number.
- `tools/deploy.sh`: needs `PORT` with more than one board; the frozen-firmware
  probe no longer imports `app` (fails on a fresh board without `config.mpy`).
- Network identity: `raspberry-pi-pico-2-wh-02.iot`, DHCP-reserved
  `192.168.4.52` for MAC `98:fe:54:1a:80:d7`; the Pico W keeps `192.168.4.51`
  as `raspberry-pi-pico-1-w-01.iot` (cold spare). `OTEL_INSTANCE` updated.
- krysdom-api `observability`: scrape target moves to
  `raspberry-pi-pico-2-wh-02.iot:9100` (job name and metrics unchanged).

## Impact

- `lib/supervisor.py`, `lib/app.py`, `lib/telemetry.py`, `lib/metrics.py`,
  `lib/strings_pl.py`, `config.py`, `firmware/*`, `tools/build.py`,
  `tools/deploy.sh`, `requirements.txt`, docs.
- Heap free on the running app: ~113 KB → ~360 KB.
- Rollback: plug the Pico W back in (its firmware and files are unchanged) and
  revert the scrape target.
