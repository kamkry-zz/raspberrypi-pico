# Pico 1 W LED Blink

Self-contained MicroPython experiment that blinks the onboard LED of a Raspberry Pi Pico W. It verifies the board, firmware, USB serial connection, and host tooling without requiring any external components.

## Hardware

- Raspberry Pi Pico W (RP2040, first generation).
- USB data cable.
- No external wiring or components.

## Board state

- MicroPython 1.23.0 (2024-06-02).
- USB CDC serial port, for example `/dev/cu.usbmodem1101` on macOS. Verify the current port with `mpremote connect list`.
- The board's flash currently contains a user `main.py` for an e-paper display plus a `lib/` directory. Treat it as valuable: this experiment uses `mpremote run` and never writes to the board by default.

## Setup

Run these commands from this experiment directory:

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/mpremote connect list
```

## Run (non-destructive, recommended)

```sh
.venv/bin/mpremote run main.py
```

Expected result: the onboard LED alternates on and off approximately every 0.5 seconds. The program prints `LED on` / `LED off` once per cycle.

Stop it with `Ctrl-C`. The program turns the LED off and exits without a traceback. This does not modify the board's stored `main.py`.

## Deploy (optional)

Deploying replaces the board's boot program. Back it up first and verify the copy:

```sh
mkdir -p backups
.venv/bin/mpremote fs cp :main.py backups/pico-w-main.py
shasum -a 256 backups/pico-w-main.py
.venv/bin/mpremote exec "import hashlib, ubinascii; d=open('main.py','rb').read(); print(ubinascii.hexlify(hashlib.sha256(d).digest()).decode())"
```

The two SHA-256 values must match. Do not use `mpremote cat` for this check: it appends a newline, so the streamed bytes hash differently from the stored file.

Then copy the experiment to the board:

```sh
.venv/bin/mpremote fs cp main.py :main.py
```

Restore the original program, then reset the board:

```sh
.venv/bin/mpremote fs cp backups/pico-w-main.py :main.py
```

## How it works

`machine.Pin("LED", machine.Pin.OUT)` uses the board's LED identifier. On the Pico W the LED is connected to `WL_GPIO0` on the CYW43439 wireless chip, not to `GP25`, so `Pin(25)` would not control it.

## OpenSpec

This experiment owns its OpenSpec root. Run OpenSpec commands from this directory:

```sh
openspec status --change pico-1-w-led-blink
openspec validate pico-1-w-led-blink --strict
```

## Documentation

- [`docs/pico-w.md`](docs/pico-w.md) — verified board, USB, and LED details with official sources.
