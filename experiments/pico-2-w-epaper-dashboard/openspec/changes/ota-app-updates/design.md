## Context

- Board: Pico 2 W (RP2350), MicroPython v1.29.0 custom build with `lib/`
  frozen; `sys.path` is `['', '.frozen', '/lib']`, so today frozen modules win.
- Flash: 2560 KB LittleFS, ~80 KB used. Runtime `.mpy` set: ~80 KB.
- Heap: 361 KB free with the app running frozen.
- Existing pieces reused: `store` (atomic JSON save), `http_client.get_to_file`
  (streamed download with size cap), `supervisor` (watchdog `beat()`, tagged
  resets, crash counter), the KEY0 power-up check, `/metrics` + `/healthz`.

## Goals / Non-goals

- Goal: update the application without USB, with automatic rollback, and
  never leave the board unbootable.
- Goal: reject anything not published by the user (signature) or not built
  for this firmware.
- Non-goal: updating MicroPython itself (USB only), ROMFS, A/B firmware
  partitions, push-triggered updates, delta updates.

## Decisions

### 1. Frozen firmware = factory image, OTA slots overlay it

`otaboot.select()` inserts `/ota/<slot>` at `sys.path[0]`, ahead of `''` and
`.frozen`, so the slot's `lib` modules **and** `config.mpy` win. Deleting the
state (or KEY1 at power-up) means plain frozen code. Rollback is always
possible because the factory image cannot be overwritten over the air.

### 2. Never shipped over the air

`otaboot`, `main.py`, `secrets.py` and `certs/` are never part of a bundle;
the publisher refuses them and the device rejects any manifest path outside
`lib/<name>.mpy` and `config.mpy`, or containing `..`. So the code that
decides what to boot, the Wi-Fi password and the HMAC key change only over USB.

### 3. Boot flow (`main.py` → frozen `otaboot`)

```
main.py: import otaboot; otaboot.select(); import app; app.boot()

select():
  KEY1 held at power-up        -> factory for this boot (state untouched)
  state.trial set:
      attempts += 1 (saved before importing anything else)
      attempts > 3             -> blacklist trial build, trial = None,
                                  fall through to active (or factory)
      else                     -> use trial slot
  state.active set             -> use active slot
  else                         -> factory
```

Counting attempts on flash *before* the app starts covers Python crashes,
hangs (watchdog reset) and power loss alike; the RAM-backed crash counter in
watchdog scratch is not enough because a power-on reset clears it.

### 4. Commit point

`app` calls `otaboot.commit()` where it already calls
`supervisor.clear_crashes()` — right after the first frame reaches the panel.
`commit()` turns `trial` into `active`, keeps the old active as `previous`,
and resets `attempts`. A build that cannot draw one frame in 3 boots is never
committed.

### 5. Update check (`ota.check()`)

Runs after an hourly refresh (never during a panel refresh), at most every
`OTA_CHECK_MINUTES` (default 60), only while Wi-Fi is up:

1. `GET {OTA_BASE_URL}/apps/pico-epaper-dashboard/manifest` with
   `If-None-Match` and `X-Device-Id: <MAC>`; 304 → done.
2. `GET …/manifest.sig`; verify HMAC-SHA256 over the **exact manifest bytes**
   with `secrets.OTA_KEY` (constant-time compare). Bad → `bad_signature`.
3. Parse; require `app == "pico-epaper-dashboard"`, `board == "RPI_PICO2_W"`,
   `micropython == sys.implementation` version, `mpy` ABI match,
   `build > active build`, build not blacklisted. Otherwise `incompatible` /
   `none`. The monotonic `build` number blocks replaying an older signed
   manifest; rolling back = publishing a new build with old content.
4. Check free flash (≥ 2 × bundle size), wipe the inactive slot, stream each
   file from `{OTA_BASE_URL}/files/<sha256>` with `get_to_file` (size cap from the manifest), verify sha256, call
   `supervisor.beat()` between files. Any mismatch → wipe slot,
   `hash_mismatch`; the running slot is untouched.
5. Save state `trial = <slot>, attempts = 0` (atomic), then
   `supervisor.reset("OTA")`.
6. Report each step to `POST {OTA_BASE_URL}/report` (`downloaded`,
   `installed`, `committed`, `rolled_back`, `failed` with the reason), best
   effort; reports never block the update.

### 6. Manifest

```json
{"schema": 1, "app": "pico-epaper-dashboard", "version": "0.4.0", "build": 7,
 "target": {"board": "RPI_PICO2_W", "micropython": "1.29.0", "mpy": "6.3"},
 "files": [{"path": "lib/app.mpy", "size": 6871, "sha256": "…"}, …]}
```

`manifest.sig` holds the hex HMAC. Plain HTTP is acceptable because both the
manifest (HMAC) and every file (sha256 listed in the signed manifest) are
authenticated; the key never leaves `secrets.py` (board and local host).

### 7. Publisher (`tools/ota_publish.py`)

Builds the runtime `.mpy` set + `config.mpy` with mpy-cross 1.29.0 (shared
with `tools/build.py`), assigns `build = last + 1` (stored in
`ota/last_build` in the repo or read back from the host), writes
`manifest.json`/`manifest.sig` into `build/ota/`, and uploads with
`--upload` only (dry run by default). It refuses `secrets.py`, `main.py`,
`otaboot` and unknown paths.

### 8. Observability

- `pico_ota_info{version,build,slot,state} 1` — `state` is
  `factory|active|trial`.
- `pico_ota_checks_total{result}` — `none|updated|bad_signature|incompatible|hash_mismatch|no_space|fail`.
- `pico_ota_rollbacks_total`; `/healthz` gains `ota_version`, `ota_slot`,
  `ota_state`, `ota_last_check`.
- Boot log line includes the slot/build; reset tag `OTA` (new `_TAGS` entry).

## Risks / Trade-offs

- **Heap**: bytecode in RAM instead of flash. ~80 KB of `.mpy` should cost
  well under 200 KB; measured before enabling (task 5.2). If it is too tight,
  fonts stay frozen and are excluded from bundles (they rarely change).
- **Shared HMAC key**: anyone with `secrets.py` can sign. Same trust boundary
  as the Wi-Fi password; acceptable on the IoT VLAN.
- **Version skew** between a slot and frozen modules: avoided by full bundles
  and by putting the slot first on `sys.path`.
- **Firmware change under an active slot**: after a USB flash to a different
  MicroPython, `otaboot` drops the slot if its `micropython`/`mpy` no longer
  match and boots factory.

## Decisions taken (2026-11-11)

- **Bundle host**: the central OTA registry in krysdom-api `iot-registry`
  (change `iot-registry-ota`), shared with the XIAO ESP32-S3 and the Uno Q.
  It stores the manifest/signature verbatim (never the key), tracks
  downloads and reports, emits OTel metrics, and notifies via hermes-agent
  on Telegram. `OTA_BASE_URL = "http://iot-registry.k3s/ota/v1"`.
- **Install**: fully automatic; publishing is the approval.
