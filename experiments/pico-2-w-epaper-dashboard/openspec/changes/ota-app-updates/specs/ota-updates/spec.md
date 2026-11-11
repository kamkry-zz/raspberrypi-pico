## ADDED Requirements

### Requirement: Signed application bundles
The dashboard SHALL install an over-the-air bundle only when the HMAC-SHA256
signature in `manifest.sig` matches the exact bytes of `manifest.json` under
the `OTA_KEY` from `secrets.py`, and every downloaded file matches the size
and sha256 listed in that manifest.

#### Scenario: Tampered manifest
- **WHEN** `manifest.json` changes after signing
- **THEN** the board records `pico_ota_checks_total{result="bad_signature"}`
  and keeps running its current code

#### Scenario: Corrupted file
- **WHEN** a downloaded file's sha256 differs from the manifest
- **THEN** the inactive slot is wiped, the result is `hash_mismatch`, and the
  running slot is unchanged

### Requirement: Compatibility and replay protection
The dashboard SHALL reject a manifest whose app, board, MicroPython version or
`.mpy` ABI differs from the running firmware, whose `build` is not greater
than the active build, or whose build is blacklisted.

#### Scenario: Old signed manifest replayed
- **WHEN** the host serves a correctly signed manifest with an older build
- **THEN** nothing is downloaded and the result is `none`

### Requirement: Restricted bundle contents
A bundle SHALL contain only `lib/<module>.mpy` files and `config.mpy`; the
boot selector, `main.py`, `secrets.py` and `certs/` MUST NOT be changeable
over the air.

#### Scenario: Path outside the bundle set
- **WHEN** a manifest lists `secrets.py` or a path containing `..`
- **THEN** the whole manifest is rejected as `incompatible`

### Requirement: Trial boot with automatic rollback
A newly installed bundle SHALL run on trial and be committed only after its
first frame reaches the panel; if it is not committed within 3 boots, the
board SHALL return to the previous slot, or to the frozen factory image, and
blacklist that build.

#### Scenario: Bundle crashes at import
- **WHEN** the new bundle raises during start-up on every boot
- **THEN** after the third boot the board runs the previous code, draws a
  frame, and counts `pico_ota_rollbacks_total`

#### Scenario: Power loss during the trial
- **WHEN** power is cut during a trial boot
- **THEN** the attempt still counts, because it is stored on flash before the
  app starts

### Requirement: Factory image always available
The frozen firmware SHALL remain a working factory image: with no active
slot, after a rollback, or when KEY1 is held at power-up, the board SHALL run
the frozen modules only.

#### Scenario: KEY1 at power-up
- **WHEN** KEY1 is held while the board powers up
- **THEN** that boot ignores all OTA slots and the state file is unchanged

### Requirement: OTA observability
`/metrics` SHALL expose `pico_ota_info{version,build,slot,state}`,
`pico_ota_checks_total{result}` and `pico_ota_rollbacks_total`, and `/healthz`
SHALL report the OTA version, slot, state and last check time.

#### Scenario: After a committed update
- **WHEN** build 7 is committed in slot `b`
- **THEN** `pico_ota_info{build="7",slot="b",state="active"}` is 1
