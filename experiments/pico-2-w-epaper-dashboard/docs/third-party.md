# Third-party notices

## Waveshare documents

The files under `datasheets/` are copies of Waveshare / Good Display
documentation, included for local reference:

- `4.2inch-e-Paper-B-Old-User-Manual.pdf`
- `4.2inch-e-Paper-B-V2-User-Manual.pdf`
- `Pico-ePaper-4.2-schematic.pdf`

Copyright remains with the original authors. Source URLs, versions and
SHA-256 checksums are recorded in `datasheets/README.md`. Do not redistribute
the PDFs separately from this experiment without checking the original terms.

## IBM Plex Mono

The bitmap fonts in `lib/font_small.py`, `lib/font_medium.py` and
`lib/font_large.py` are generated from IBM Plex Mono.

- Copyright © 2017 IBM Corp.
- Licensed under the SIL Open Font License, Version 1.1.
- License text: `tools/fonts/OFL.txt`.
- Upstream: <https://github.com/IBM/plex>

The large font is a generated subset used only for numerals, `,`, `%`, `-`,
`°`, `C` and `×`, to save heap on the Pico.

## Open-Meteo

Weather data by [Open-Meteo.com](https://open-meteo.com/), licensed under
CC BY 4.0. Attribution appears in the dashboard footer and on the About page.

## Waveshare module photograph

`docs/images/button-location.jpg` is a Waveshare product photograph with
annotations added to show the left-edge KEY0/KEY1 switches. The photograph is
© Waveshare and is included only as a local button-location reference.

## Waveshare demo code

The low-level panel sequence is based on the Waveshare
[Pico_ePaper_Code](https://github.com/waveshare/Pico_ePaper_Code) MicroPython
example that was already running on this board. The driver in this experiment
is a cleaned-up adaptation; it keeps the proven init/clear/update order and
adds timing, revision handling, error reporting and a block red transfer.

## MicroPython

MicroPython is licensed under the MIT license. This experiment targets the
official Raspberry Pi Pico W build, version 1.23.0 (2024-06-02).
