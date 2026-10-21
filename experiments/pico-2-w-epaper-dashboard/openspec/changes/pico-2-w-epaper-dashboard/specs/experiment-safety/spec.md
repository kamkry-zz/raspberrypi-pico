## Purpose

Run the experiment without damaging the board's existing program or leaking
network credentials.

## ADDED Requirements

### Requirement: Non-destructive verification
The documented default run SHALL execute from the mounted host directory
without writing to the board filesystem.

#### Scenario: Mount and run
- **WHEN** the experiment is verified with `mpremote mount . run main.py`
- **THEN** the board's stored `main.py` and `lib/` are unchanged

### Requirement: Secrets handling
The Wi-Fi password SHALL exist only in gitignored `secrets.py` and SHALL never
be printed or committed.

#### Scenario: Missing secrets
- **WHEN** `secrets.py` is absent or still contains `CHANGE_ME`
- **THEN** the program reports a clear message and does not attempt a network
  connection

### Requirement: Dedicated WLAN
The Pico SHALL use only `krys_dom_IoT` (2.4 GHz, WPA2) and SHALL NOT fall back
to another SSID.

#### Scenario: Wrong or unavailable network
- **WHEN** `krys_dom_IoT` is unavailable
- **THEN** the dashboard renders offline with cached/empty weather and a clear
  status, without joining another network

### Requirement: Exclusive serial access
Only one process SHALL access the board's serial port at a time.

#### Scenario: Sequential commands
- **WHEN** board commands are run
- **THEN** they are issued one at a time, because a second process fails with a
  port-in-use error

### Requirement: Backup before deployment
Any deployment that overwrites board files SHALL require a verified backup in
the experiment's gitignored `backups/` and explicit user approval.

#### Scenario: No implicit deploy
- **WHEN** the normal verification workflow is used
- **THEN** no `mpremote fs cp` is executed and the board's original program
  remains intact
