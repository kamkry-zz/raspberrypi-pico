# Pico-ePaper-4.2-B — verified module notes

Verified on **2026-10-21** against the connected Pico W (RP2040, MicroPython
1.23.0). The unit reports the **older 4.2-B revision**, not the current V2
module. Both command sets are implemented.

## Identification

- Module: **Waveshare Pico-ePaper-4.2-B**, 4.2 inch, 400 × 300, black / white /
  red, SPI, designed to plug onto a Pico/Pico W.
- The plain **Pico-ePaper-4.2** is a different panel: black/white only, four
  grayscale levels, 4 s full refresh, UC8176 controller, no red.
- The current **4.2-B V2** (2025-02-21 manual) uses an SSD1683 controller and
  the `0x24`/`0x26` command set. The unit here answers the `0x2F` probe with
  `0xFF` and uses the legacy `0x10`/`0x13` command set. Do not assume the V2
  pin/command details apply without checking the probe.

The mirrored PDFs are:

| File | Source | Notes |
| --- | --- | --- |
| `datasheets/4.2inch-e-Paper-B-Old-User-Manual.pdf` | <https://files.waveshare.com/upload/7/7f/4.2inch-e-paper-b-specification.pdf> | old 4.2-B manual, 2.5 MB, 2023 |
| `datasheets/4.2inch-e-Paper-B-V2-User-Manual.pdf` | <https://files.waveshare.com/wiki/Pico-ePaper-4.2-B/4.2inch%20e-Paper%20(B)%20V2.pdf> | V2 manual, revision 1.0, 2025-02-21, 3.9 MB |
| `datasheets/Pico-ePaper-4.2-schematic.pdf` | <https://files.waveshare.com/upload/2/20/Pico-ePaper-4.2.pdf> | module schematic, 609 KB, 2 pages |

Checksums are in `datasheets/SHA256SUMS`.

## Specification

| Property | Value | Source |
| --- | --- | --- |
| Screen size | 4.2 inch | wiki |
| Resolution | 400 × 300 | wiki, datasheet |
| Active area | 84.8 × 63.6 mm | wiki, datasheet |
| Pixel pitch | 0.212 × 0.212 mm | wiki, datasheet |
| Pixel density | 132 DPI | V2 datasheet |
| Outline, bare panel | 90.1 × 77.0 × 1.18 mm | wiki |
| Outline, V2 panel | 91 × 77 × 1.2 mm | V2 datasheet |
| Driver board | 93.5 × 78.5 mm | wiki |
| Weight | 16.1 ± 0.3 g | V2 datasheet |
| Colours | red, black, white | wiki |
| Greyscale | none (2 levels; the wiki's "Greyscale: 2") | wiki |
| Controller | SSD1683 on V2; legacy command set on this unit | V2 datasheet, probe |
| Interface | 4-wire SPI, mode 0 (CPOL=0, CPHA=0), write-only | wiki |
| Logic / module supply | VCI 2.2–3.7 V (typ. 3.0 V); module accepts 3.3/5 V | datasheet, wiki |
| Full refresh | 15 s (wiki), 14 s at 25 °C (datasheet), **15.8–23.2 s measured** | wiki/datasheet/measured |
| Refresh power | 38.4 mW typ. (module); 27 mW / 9 mA @ 3.0 V (panel) | wiki/datasheet |
| Sleep current | < 0.01 µA (wiki); 1 µA max (datasheet) | wiki/datasheet |
| Operating temperature | 0–40 °C | datasheet |
| Storage temperature | −25–60 °C | datasheet |
| Optimal storage | 23 ± 2 °C, 55 ± 10 % RH | datasheet |
| Refresh interval | at least every 24 h to avoid ghosting | datasheet |
| Update in direct sunlight | not supported | wiki |

Other handling notes from the datasheet: keep the panel dry, do not touch the
IC bonding area, avoid high temperature/humidity and prolonged sunlight, and
store/ship with a completely white image.

## Pinout

The module plugs directly onto the Pico/Pico W; the same signals are available
on the 8-pin side connector.

| e-Paper signal | Pico pin | Pico GPIO | Direction |
| --- | --- | --- | --- |
| VCC | VSYS | — | power |
| GND | GND | — | ground |
| DIN / MOSI | 14 | GP11 | Pico → panel |
| CLK / SCK | 15 | GP10 | Pico → panel |
| CS | 12 | GP9 | Pico → panel, active low |
| DC | 11 | GP8 | Pico → panel, low = command |
| RST | 13 | GP12 | Pico → panel, active low |
| BUSY | 16 | GP13 | panel → Pico |

The panel is **not touch-sensitive**; the two user switches are the only
on-module input. They are **KEY0 → GP15** and **KEY1 → GP17**, wired to GND
(active low; use the Pico's internal pull-ups). This is confirmed by the
schematic. They are side-actuated tactile switches on the **left PCB edge**;
see `docs/images/button-location.jpg`. They are **verified on this unit**:
pressing KEY0/KEY1 drives raw GP15/GP17 low and changes the page (previous /
next). The earlier bring-up scans missed the press; the panel itself has no
touch controller, so tapping the printed markers does nothing. External
momentary switches on GP15/GP17 also work.

## Data format

The panel stores two 1-bit planes per image:

- 400 pixels / 8 = **50 bytes per row**
- 300 rows = **15,000 bytes per plane**
- each pixel is one bit, **MSB first** within a byte
- 1 = white in the black plane; 0 = black
- the red plane is active-low: 0 = red, 1 = white/no red

Native wire encoding used by this experiment:

| Colour | Black plane | Red plane |
| --- | --- | --- |
| black | 0 | 1 |
| white | 1 | 1 |
| red | 1 | 0 |

Waveshare's Python demo stores its red framebuffer with 1 = red and inverts it
byte-by-byte before sending; the resulting wire byte is the same as this
native encoding.

The MSB-first order was verified **byte-for-byte against
`framebuf.MONO_HLSB`** for the same shapes on this firmware. The wiki's MSB
diagram matches the observed controller behaviour.

## SPI and command sequence

- SPI mode 0, 4 MHz in the vendor demo and this driver.
- CS is active low. DC low = command, high = data.
- The panel is write-only on the SPI data line; the only read is the revision
  probe described below.
- The driver starts with a hardware reset (high 200 ms, low 2 ms, high 200 ms),
  sends `0x2F`, waits 100 ms, bit-bangs one byte on DIN (SCK as output, DIN as
  input with pull-up), restores SPI, then runs the matching init sequence.

Legacy revision (`0x2F` != 0x01):

| Step | Command / data |
| --- | --- |
| power on | `0x04`, wait BUSY |
| panel setting | `0x00 = 0x0F` |
| black plane | `0x10`, 15,000 bytes |
| red plane | `0x13`, 15,000 bytes |
| update | `0x12`, delay 100 ms, wait BUSY |
| sleep | `0x50=0xF7`, `0x02`, wait BUSY, `0x07=0xA5` |

V2 revision (`0x2F` == 0x01):

| Step | Command / data |
| --- | --- |
| soft reset | `0x12`, wait BUSY |
| border waveform | `0x3C = 0x05` |
| temperature sensor | `0x18 = 0x80` |
| data entry | `0x11 = 0x03` |
| RAM X range | `0x44 = 0x00, 0x31` (0–49) |
| RAM Y range | `0x45 = 0x00, 0x00, 0x2B, 0x01` (0–299) |
| cursor | `0x4E = 0x00`, `0x4F = 0x00, 0x00` |
| black plane | `0x24`, 15,000 bytes |
| red plane | `0x26`, 15,000 bytes |
| update | `0x22=0xF7`, `0x20`, wait BUSY |
| sleep | `0x10 = 0x03` |

**Initialisation + vendor clear is mandatory.** The working legacy program
always runs `Init()` followed immediately by `Clear()` before the first
drawing. Without the clear, this panel retained the previous image during
bring-up even though a frame was sent.

The vendor clear writes both planes as blocks:

- black plane `0xFF` (white)
- red plane `0x00`

The vendor *display* routine sends the black plane as a block but the red
plane one byte per CS-low transaction. This driver sends both planes as
blocks; it was verified visually on this unit and reduces the plane transfer
to about **88 ms** (`transfer` timing). If a particular unit shows red-plane
artifacts, fall back to a byte-wise red transfer.

## Refresh behaviour

- Full refresh only in practice. Waveshare's B demo exposes no partial-update
  function; the controller datasheet mentions partial update, but the red
  waveform and vendor B module do not provide a supported partial path.
- The screen flashes during a full refresh; this is normal.
- Specified update time: 14 s at 25 °C (datasheet), 15 s (wiki).
- Measured on this unit: **15.8 s** for a typical dashboard frame and
  **23.2 s** on other runs (temperature/frame dependence). The driver reports
  the actual panel time on the Capabilities page.
- The old panel's BUSY line is high when idle. It sometimes provides a low
  busy pulse during the refresh and sometimes not. The vendored `ReadBusy()`
  waits while low; the driver adds a **24 s fixed fallback** only when no pulse
  appears. This is why a refresh can return after ~16 s or ~23 s.
- The panel is kept **awake** after the first init+clear, matching the working
  legacy program. Sleeping between updates would require another clear/wake
  waveform on this revision. The module's sleep current is tiny; the Pico W is
  USB-powered in this experiment.
- Refresh at least once every 24 h to avoid ghosting. The hourly dashboard
  satisfies this. An optional nightly white clear is available via
  `config.NIGHTLY_CLEAR` (off by default; it adds a second ~16–23 s refresh).

## Measured timings

| Stage | Measurement |
| --- | --- |
| Init + revision probe | 604–705 ms |
| Vendor clear | 15.8 s (ReadBusy) / up to 23.2 s |
| Plane transfer | 88 ms (block black + block red) |
| Full dashboard frame | 15.8–23.2 s panel busy |
| First boot to dashboard | ~45–60 s including clear, Wi-Fi, weather and first frame |

These are measured on the older unit; the V2 may differ. The datasheet's
14 s is a panel-level reference, not a guarantee for this module.

## Rendering notes

- The portable canvas uses the native plane encoding above.
- Pixels are packed MSB-first; this was checked against `framebuf.MONO_HLSB`
  on the board. See `lib/canvas.py`.
- The red plane is not "1 = red"; that is the vendor framebuffer convention.
- Ordered 4×4 Bayer dithering is used for red/white and black/white tints.
  There is no true grayscale on this panel.
- The large font is generated as a subset (digits, comma, percent, degree,
  `C`, `×`) to keep the RP2040 heap free for the two 15 KB canvas planes.

## Power and thermal

- The module is powered from VSYS (3.3/5 V tolerant on the driver board).
- The Pico W's internal temperature sensor is shown as `Temp`; it is the
  RP2040 die temperature, not the room or panel temperature.
- The panel's operating range is 0–40 °C; colour and refresh behaviour degrade
  near the extremes. Do not leave the module in direct sunlight.
- E-paper retains the image without power; a blank panel after unplugging is
  not expected.

## Sources

- Waveshare Pico-ePaper-4.2-B wiki:
  <https://www.waveshare.com/wiki/Pico-ePaper-4.2-B>
- Waveshare Pico-ePaper-4.2 (plain, for comparison):
  <https://www.waveshare.com/wiki/Pico-ePaper-4.2>
- V2 panel manual (local mirror): see `datasheets/`.
- Old 4.2-B panel manual (local mirror): see `datasheets/`.
- Module schematic (local mirror): see `datasheets/`.
- Waveshare Pico e-Paper demo code:
  <https://github.com/waveshare/Pico_ePaper_Code>
- MicroPython RP2 / `machine.SPI` documentation:
  <https://docs.micropython.org/en/v1.23.0/rp2/quickref.html>
- Raspberry Pi Pico-series documentation:
  <https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html>
