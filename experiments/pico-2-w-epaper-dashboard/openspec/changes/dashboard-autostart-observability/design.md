## Context

RP2040, MicroPython 1.23.0, ~190 KB GC heap. The canvas needs two contiguous
15 KB planes; the modules take ~89 KB even as `.mpy` (fonts and tables are
loaded into RAM). A full panel refresh blocks 16-24 s.

## Decisions

### Watchdog fed by a soft timer, gated on a heartbeat
The RP2040 WDT maxes out at ~8.3 s and cannot be stopped. A `machine.Timer`
callback feeds it every second while `beat()` was called within
`WATCHDOG_STALL_S` (300 s). Soft timers run from the scheduler, including in
`sleep` and blocking socket waits, so long healthy operations survive while
Python-level stalls and C-level hangs both end in a hardware reset. The panel
wait loop beats through an idle hook, so it has its own 45 s BUSY timeout.

### Maintenance mode instead of a disarmable watchdog
Ctrl-C writes `/maint` and resets; the next boot consumes the flag and stays in
the REPL without a watchdog. KEY0 held at power-up does the same without USB.

### Reset tagging
`machine.reset()` reports as `WDT` on the RP2040. Deliberate resets write a tag
(CRASH, MAINT, WIFI, DEPLOY, MEM) to WATCHDOG_SCRATCH1 so a genuine watchdog
trip is distinguishable; WATCHDOG_SCRATCH0 holds the crash counter.

### Pull metrics, OTLP push disabled
Measured on the board: a CA-verified TLS session to otel.k3s works with ~41 KB
free on a clean heap, but in the running app the largest free block is
~10 KB even with 75 KB free, so the handshake fails with ENOMEM. Lending the
canvas planes and a 24 KB reserve did not produce a large enough block.
Metrics are therefore scraped from `/metrics` by the cluster's
`prometheus/apps` relay (the documented pattern for apps that cannot push
OTLP). The OTLP exporter stays in the code, tested, behind `OTLP_ENABLED`.
Update: the board now runs firmware with `lib/` frozen into flash
(`firmware/build.sh`), leaving ~113 KB free; a trial with OTLP enabled
delivered metrics, logs and traces. Enabling it is deferred.

### Frozen firmware
MicroPython v1.23.0 RPI_PICO_W, built in Docker so the host needs no ARM
toolchain. Same flash layout as stock (firmware < 1200 KB, LittleFS above),
so flashing via `machine.bootloader()` keeps the filesystem. `sys.path` is
`['', '.frozen', '/lib']`: frozen modules win over `/lib`, while `config`,
`secrets`, `certs` and the `main.py` shim stay editable on the filesystem.

## Risks

- The `.iot` name must resolve from cluster DNS and the IoT VLAN must accept
  :9100 from the cluster; verify `up{job="pico-epaper-dashboard"}` after the
  observability change is deployed (fallback target: `192.168.4.51:9100`).
