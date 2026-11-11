## Why

Every dashboard change today needs USB: `firmware/build.sh` + `firmware/flash.sh`
for `lib/`, `tools/deploy.sh` for config, and any `mpremote` connection
interrupts the running board. The Pico 2 W has 361 KB of heap free with the
app running (the Pico W had 106 KB), so the whole app can now run from
`.mpy` files loaded into RAM instead of only from frozen flash. That makes
over-the-air updates of the application safe and simple, without touching the
MicroPython firmware.

Scope is **option A only**: application updates (dashboard `.mpy` modules and
`config.mpy`). MicroPython firmware updates stay on USB (`firmware/flash.sh`);
ROMFS and RP2350 A/B firmware partitions are out of scope.

## What Changes

- **Two bundle slots on flash** (`/ota/a`, `/ota/b`) plus `/ota/state.json`.
  The frozen firmware stays the **factory image**: with no active slot, or
  after a rollback, the board runs exactly what is frozen today.
- **Boot selector** `otaboot` (frozen, never shipped over the air): picks the
  active or trial slot, puts it first on `sys.path` (ahead of `.frozen`), and
  counts trial boots on flash. Holding **KEY1 at power-up** boots the factory
  image for one boot (KEY0 stays maintenance mode).
- **Pull-based update check** after the hourly refresh: fetch a signed
  manifest over plain HTTP on the LAN, verify the HMAC-SHA256 signature, check
  compatibility (board, MicroPython and `.mpy` version, build number), stream
  each file into the inactive slot and verify its sha256, then reset into the
  new slot **on trial**.
- **Trial and rollback**: the new slot is committed only after its first
  frame reaches the panel. If it does not within 3 boots (crash, hang/watchdog,
  power loss counted on flash), the board reverts to the previous slot (or
  factory) and blacklists that build.
- **Full bundles, not deltas**: every release ships all runtime modules
  (~80 KB), so frozen and OTA code never mix within one run.
- **Publisher** `tools/ota_publish.py`: builds the bundle with mpy-cross
  1.29.0, writes `manifest.json` + `manifest.sig`, and publishes them to the
  central **iot-registry** OTA registry (krysdom-api change `iot-registry-ota`). Publishing is the new deploy step ("deploy only when the user
  asks" applies to it).
- **Observability**: `pico_ota_info{version,build,slot,state}` and
  `pico_ota_checks_total{result}` on `/metrics`; OTA fields on `/healthz`;
  boot reset tag `OTA`.
- Fix `tools/build.py`: its module list misses `font_xlarge` and `synmap`.
- One last USB firmware flash is needed to add `otaboot` and the new tag.

## Impact

- New: `lib/otaboot.py`, `lib/ota.py`, `tools/ota_publish.py`, tests.
- Changed: `main.py` shim, `lib/app.py` (commit + check hook), `lib/supervisor.py`
  (`OTA` tag), `lib/metrics.py`/`telemetry.py`, `config.py` (`OTA_*`),
  `secrets.example.py` (`OTA_KEY`), `firmware/manifest.py`, `tools/build.py`,
  `tools/deploy.sh`, README, AGENTS.md.
- Needs the iot-registry OTA registry (krysdom-api change `iot-registry-ota`):
  device API `http://iot-registry.k3s/ota/v1/`, app id `pico-epaper-dashboard`.
  Install is fully automatic once a release is published.
- Heap: the app's bytecode moves from flash to RAM while a slot is active;
  target ≥150 KB free after the first frame (measured in task 5.2).
