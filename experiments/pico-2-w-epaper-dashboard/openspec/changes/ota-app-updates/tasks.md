## 1. Decisions (before code)

- [x] 1.1 Bundle host: iot-registry OTA registry (krysdom-api `iot-registry-ota`).
- [x] 1.2 Fully automatic install after publish.

## 2. Device

- [x] 2.1 `lib/otaboot.py`: state file, slot selection, attempt counting, blacklist, KEY1 factory boot, `commit()`; frozen, never in bundles. Slot root `/.ota` (a `/ota` directory shadowed the frozen `ota` module on the board).
- [x] 2.2 `lib/ota.py`: manifest fetch (ETag), HMAC check, compatibility, streamed download into the inactive slot, sha256, free-space check, trial switch; frozen-only too.
- [x] 2.3 `main.py` shim calls `otaboot.select()` before importing `app`.
- [x] 2.4 `app`: commit after the first frame; `ota.check()` ~2 min after boot and every `OTA_CHECK_MINUTES`; OTA hooks can never break `/metrics` or `/healthz`.
- [x] 2.5 `supervisor`: `OTA` reset tag.
- [x] 2.6 `pico_ota_info`, `pico_ota_checks_total`; `/healthz` OTA fields. (Rollbacks are counted by the registry: `iot_registry_ota_device_events_total{event="rolled_back"}`.)
- [x] 2.7 `config.py` `OTA_ENABLED`, `OTA_BASE_URL`, `OTA_APP`, `OTA_CHECK_MINUTES`; `secrets.example.py` `OTA_KEY`.

## 3. Host tooling

- [x] 3.1 `tools/build.py` module list fixed (`font_xlarge`, `synmap`, `ota`, `otaboot`); test checks it against `firmware/manifest.py`.
- [x] 3.2 `tools/ota_publish.py` (dry run by default, `--upload`; build = highest ever + 1).
- [x] 3.3 `tools/deploy.sh` copies `secrets.py` (with `OTA_KEY`) as before; module cleanup list updated.

## 4. Tests (host)

- [x] 4.1 `otaboot`: factory/trial/commit/rollback, maintenance boots not counted, KEY1, firmware change, corrupt state (`tools/test_ota.py`).
- [x] 4.2 `ota`: bad signature (reported once), incompatible firmware, not newer/ETag, hash mismatch keeps the running slot, trial pending.
- [x] 4.3 Publisher manifest/signature verified by the device-side code; slot root cannot shadow a module.

## 5. Hardware verification

- [x] 5.1 Firmware rebuilt with `otaboot`/`ota` frozen and flashed (2026-11-11).
- [x] 5.2 Heap with build 2 active after the first frame: 291,712 B free (factory 359,104 B).
- [x] 5.3 Build 2 published → installed in slot a, trial, committed ~3.5 min after boot; registry `current`.
- [ ] 5.4 Publish a build that raises at import → 3 boots, rollback to the previous slot, build blacklisted.
- [ ] 5.5 Pull power during the download and during the trial boot → board recovers.
- [ ] 5.6 KEY1 at power-up boots factory.

## 6. Docs

- [x] 6.1 README "Over-the-air updates", AGENTS.md.
- [x] 6.2 iot-registry OTA registry deployed (krysdom-api `iot-registry-ota`).
- [x] 6.3 Steps reported to the registry (`installed`, `committed`, `rolled_back`, `failed`).
