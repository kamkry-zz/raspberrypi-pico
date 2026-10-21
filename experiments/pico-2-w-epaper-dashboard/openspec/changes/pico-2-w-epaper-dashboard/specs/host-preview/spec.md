## Purpose

Allow responsive layout iteration and regression testing on the host using the
same canvas/pages/fonts as the Pico, without a 16–23 s hardware refresh.

## ADDED Requirements

### Requirement: Shared rendering code
The canvas, icons, strings, time maths and page layout SHALL be pure Python and
SHALL run unchanged on MicroPython and CPython.

#### Scenario: No hardware imports
- **WHEN** `tools/preview.py` imports the page modules
- **THEN** no `machine`, `network`, `socket` or `ssl` import is required

### Requirement: PNG previews
The tooling SHALL render every page to PNG using only the Python standard
library.

#### Scenario: Generate all pages
- **WHEN** `python3 tools/preview.py --frame all --scale 2` runs
- **THEN** dashboard, weather, network, capabilities, about, bring-up, rain and
  offline images are written

### Requirement: Deterministic fixtures and tests
The tooling SHALL provide deterministic weather/network/metrics fixtures and
stdlib tests for time, weather parsing, canvas packing and page rendering.

#### Scenario: Canvas packing
- **WHEN** the canvas test draws a known black/white/red frame
- **THEN** the plane bytes match the expected MSB-first native encoding

#### Scenario: Test run
- **WHEN** `python3 -m unittest discover -s tools -p 'test_*.py'` runs
- **THEN** all tests pass without a Pico attached
