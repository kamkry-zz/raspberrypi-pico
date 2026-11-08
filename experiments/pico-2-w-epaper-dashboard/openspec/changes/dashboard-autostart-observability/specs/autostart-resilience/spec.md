## ADDED Requirements

### Requirement: Self-starting dashboard
The installed board SHALL start the dashboard on every power-up and display a
fresh frame without a host connection.

#### Scenario: Power restored
- **WHEN** power returns after a cut
- **THEN** the board boots the dashboard, joins `krys_dom_IoT`, syncs time and
  shows current weather within about 60 s

#### Scenario: Network not ready at boot
- **WHEN** Wi-Fi or the internet is unavailable during the first refresh
- **THEN** the last persisted weather is shown marked stale, and the network
  is retried with backoff (60 s up to 15 min) and the panel redrawn once fresh
  data is fetched

### Requirement: Hang and crash recovery
The board SHALL reset itself when the application stops making progress or
fails fatally.

#### Scenario: Application stall
- **WHEN** the app does not heartbeat for `WATCHDOG_STALL_S`
- **THEN** the hardware watchdog resets the board and the next boot reports
  `reset_cause=WDT`

#### Scenario: Fatal exception
- **WHEN** an unhandled exception escapes the app
- **THEN** it is logged and the board resets after a backoff that doubles per
  consecutive crash (30 s up to 15 min)

### Requirement: Power-loss-safe persistence
Files written by the app SHALL never be left half-written by a power cut.

#### Scenario: Cut during a cache write
- **WHEN** power fails while the weather cache is written
- **THEN** the next boot reads either the previous or the new file, and a
  corrupt file is discarded rather than blocking the boot

### Requirement: Maintenance access
The installed dashboard SHALL remain reachable for `mpremote` despite the
armed watchdog.

#### Scenario: mpremote connects
- **WHEN** a host sends Ctrl-C to the running app
- **THEN** the board reboots once into the REPL without the app or watchdog,
  and the next reset resumes the dashboard
