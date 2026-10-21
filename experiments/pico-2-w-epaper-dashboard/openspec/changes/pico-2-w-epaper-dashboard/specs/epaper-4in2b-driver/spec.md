## Purpose

Provide a reliable, documented driver for the Waveshare Pico-ePaper-4.2-B
(400 × 300, red/black/white) on a Pico W, including both the legacy and V2
command sets and the vendor init/clear requirement.

## ADDED Requirements

### Requirement: Revision-aware initialisation
The driver SHALL probe the panel with command `0x2F` during init and select
the legacy or V2 command sequence from the returned byte.

#### Scenario: Legacy panel
- **WHEN** the probe byte is not `0x01`
- **THEN** the driver uses the legacy `0x04`/`0x00=0x0F` init and the
  `0x10`/`0x13`/`0x12` display commands

#### Scenario: V2 panel
- **WHEN** the probe byte is `0x01`
- **THEN** the driver uses the V2 `0x12`/`0x3C`/`0x18`/`0x11`/`0x44`/`0x45`
  init and the `0x24`/`0x26`/`0x22`/`0x20` display commands

### Requirement: Init and clear before the first frame
The driver SHALL run the vendor init followed by the vendor clear waveform
before the first dashboard frame.

#### Scenario: First frame after construction
- **WHEN** the driver is constructed
- **THEN** it resets, initialises, writes the vendor clear planes and waits for
  the waveform before the first display call

### Requirement: Native dual-plane transfer
The driver SHALL accept two native 15,000-byte planes (50 bytes per row,
300 rows, MSB-first) and write them to the panel.

#### Scenario: Plane encoding
- **WHEN** a pixel is black, white or red
- **THEN** the black/red plane bits are `0/1`, `1/1` and `1/0` respectively

#### Scenario: Block transfer
- **WHEN** a frame is displayed
- **THEN** the black and red planes are sent as block transfers in a single
  CS-low transaction each, and the measured transfer is about 88 ms

### Requirement: Full refresh only
The driver SHALL perform full-screen refreshes and SHALL NOT claim partial
refresh support for the 4.2-B module.

#### Scenario: Refresh timing
- **WHEN** a frame is displayed
- **THEN** the driver waits for BUSY or a 24 s fallback and exposes the
  measured transfer, panel and total times

### Requirement: Sleep and wake
The driver SHALL expose the vendor sleep command and SHALL require init and
clear after waking from deep sleep.

#### Scenario: Normal dashboard loop
- **WHEN** the dashboard refreshes hourly
- **THEN** the panel remains awake and no sleep/wake clear is inserted

### Requirement: User switches
The driver SHALL support the schematic switches KEY0 on GP15 and KEY1 on GP17
as active-low inputs with debounce and short/long press detection.

#### Scenario: Module switches
- **WHEN** KEY0 or KEY1 on the left PCB edge is pressed
- **THEN** the button layer reports the press and the dashboard changes page;
  the panel itself has no touch input

#### Scenario: External switches
- **WHEN** a momentary switch connects GP15 or GP17 to GND
- **THEN** the button layer reports a short or long press without requiring
  the module's physical switches
