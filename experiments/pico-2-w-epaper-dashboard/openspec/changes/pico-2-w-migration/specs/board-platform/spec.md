## ADDED Requirements

### Requirement: Runs on the Pico 2 W
The dashboard SHALL run on a Raspberry Pi Pico 2 W (RP2350) with MicroPython
v1.29.0 and its `lib/` frozen into flash, and SHALL keep running unchanged on
a Pico W (RP2040) cold spare.

#### Scenario: Deliberate reset on the RP2350
- **WHEN** the app resets itself with a tag (for example `DEPLOY`)
- **THEN** the tag is written to the RP2350 watchdog scratch register at
  `0x400D8000 + 0x10` and the next boot reports it as the reset cause

### Requirement: Tooling refuses ambiguous targets
`firmware/flash.sh` and `tools/deploy.sh` SHALL refuse to run without `PORT`
when more than one MicroPython board is connected, and `firmware/flash.sh`
SHALL refuse a UF2 built for a different chip than the connected board.

#### Scenario: Two boards connected
- **WHEN** both the Pico W and the Pico 2 W are on USB and `PORT` is unset
- **THEN** the script lists both ports and exits without touching a board
