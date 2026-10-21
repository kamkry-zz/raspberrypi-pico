## Purpose

Demonstrate the 4.2-B's three colours, dithering, fonts, geometry and full
refresh behaviour both as an on-screen page and as a standalone script.

## ADDED Requirements

### Requirement: Capability page
The dashboard SHALL include a capabilities page showing black, red, white and
dithered colour swatches, a font specimen, geometry and refresh telemetry.

#### Scenario: Refresh telemetry
- **WHEN** the capability page is rendered
- **THEN** it shows transfer, panel and total timings plus the measured value
  against the 15 s specification marker

### Requirement: Standalone demo
The experiment SHALL provide `demo.py`, which shows the bring-up pattern, a
16-level red/white and black/white dither chart, and the capability page
without Wi-Fi or `secrets.py`.

#### Scenario: No network
- **WHEN** `demo.py` runs with no Wi-Fi configured
- **THEN** all demo frames render and the panel is left with the last frame

### Requirement: Honest limits
The capability material SHALL state that the panel has three colours, no true
grayscale, no supported partial refresh, and a full refresh of 15.8–23.2 s on
this unit.

#### Scenario: Dithering instead of grey
- **WHEN** a tint is needed
- **THEN** ordered dithering is used rather than claiming a grey level
