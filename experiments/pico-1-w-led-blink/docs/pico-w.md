# Raspberry Pi Pico W — verified board notes

Verified on 2026-10-20 against the board connected to this Mac.

## Board

| Property | Value |
| --- | --- |
| Model | Raspberry Pi Pico W (first generation, wireless) |
| Microcontroller | RP2040, dual-core Arm Cortex-M0+, up to 133 MHz |
| SRAM | 264 kB |
| Flash | 2 MB |
| GPIO | 26 multi-function pins |
| Wireless | Infineon CYW43439, Wi-Fi 802.11n 2.4 GHz and Bluetooth 5.2 |
| Onboard LED | `WL_GPIO0` on the CYW43439, not `GP25` |
| USB | 1.1 device, CDC serial only in normal MicroPython mode |

The Pico W is the first-generation wireless variant. It is not a Pico 2 W (RP2350); do not apply RP2350-specific configuration.

## Firmware and serial connection

- MicroPython 1.23.0, build `v1.23.0 on 2024-06-02`.
- `os.uname()` reports `sysname='rp2'`, `machine='Raspberry Pi Pico W with RP2040'`.
- The USB descriptor is `MicroPython Board in FS mode`. **FS means USB Full Speed**, not a mounted filesystem. In normal operation the board exposes only a serial port.
- There is no mass-storage volume unless the board is rebooted into BOOTSEL mode (hold BOOTSEL while connecting).
- Verified serial device on this Mac: `/dev/cu.usbmodem1101`. The name can change after reconnecting; always check:

  ```sh
  .venv/bin/mpremote connect list
  ```

- Serial access is exclusive. Only one `mpremote` or terminal process may use the port at a time; a second process fails with a port-in-use error.

## Onboard LED

The Pico W LED is wired to the CYW43439 wireless chip through `WL_GPIO0`. It is not connected to RP2040 `GP25` (that is the non-wireless Pico layout).

Use the board identifier, which works on both Pico and Pico W:

```python
from machine import Pin
led = Pin("LED", Pin.OUT)
```

`Pin(25)` does not control the onboard LED on a Pico W.

## Current board contents

At verification time the board stored:

- `main.py` — about 22 KB, a 4.2-inch e-paper display program.
- `lib/` — supporting modules.

This user program is not present elsewhere in the repository. Back it up before deploying anything to `:main.py`:

```sh
mkdir -p backups
.venv/bin/mpremote fs cp :main.py backups/pico-w-main.py
shasum -a 256 backups/pico-w-main.py
.venv/bin/mpremote exec "import hashlib, ubinascii; d=open('main.py','rb').read(); print(ubinascii.hexlify(hashlib.sha256(d).digest()).decode())"
```

The two SHA-256 values must match. `mpremote cat` appends a newline and is not suitable for byte-exact verification.

Verified backup on 2026-10-20: 22,772 bytes, SHA-256 `40c63fa10156cbc84706022f687937997fe9342d158b06072b927961e58a4c90`.

## Sources

- Raspberry Pi Pico-series documentation (models, Pico 1 variants, wireless layout, LED on `WL_GPIO0`):
  https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html
- MicroPython RP2 quick reference:
  https://docs.micropython.org/en/latest/rp2/quickref.html
- MicroPython Pico W firmware downloads:
  https://micropython.org/download/RPI_PICO_W/
