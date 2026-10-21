# AGENTS.md

## Repository layout

- The repo is a collection of self-contained experiments under `experiments/<name>/`.
- `experiments/pico-1-w-led-blink/` — Pico W onboard LED blink; verifies the board, firmware and host tooling.
- `experiments/pico-2-w-epaper-dashboard/` — 4.2-inch red/black/white e-paper dashboard, local panel docs and a capability demo.
- Each experiment owns its `main.py`, `README.md`, `docs/`, `requirements.txt`, `.gitignore`, `backups/`, and its own OpenSpec root at `openspec/`. Do not share code or tooling state between experiments.

## OpenSpec

- There is **no repository-root `openspec/`**. Each experiment has its own root.
- Run every OpenSpec command from the experiment directory:

  ```sh
  cd experiments/pico-2-w-epaper-dashboard
  openspec status --change pico-2-w-epaper-dashboard --json
  openspec validate pico-2-w-epaper-dashboard --strict
  ```

  The same rule applies to `pico-1-w-led-blink`; replace the directory and
  change name.

- Implementation edits belong inside that experiment directory. Root `AGENTS.md` is the only repo-level guidance file.

## Hardware

- Board: Raspberry Pi Pico W (RP2040), MicroPython **1.23.0** (2024-06-02).
- Serial port: `/dev/cu.usbmodem1101`; verify with `.venv/bin/mpremote connect list` rather than assuming it.
- The USB descriptor `Board in FS mode` means **USB Full Speed**, not a mounted filesystem. The board exposes a CDC serial port only; there is no drag-and-drop volume unless it is rebooted into BOOTSEL mode.
- The onboard LED is wired to `WL_GPIO0` on the CYW43439, not `GP25`. Use `machine.Pin("LED", machine.Pin.OUT)`; `Pin(25)` does not control it.
- E-paper panel: Waveshare **Pico-ePaper-4.2-B**, 400×300, red/black/white; the connected unit is the **older revision** (`0x2F` probe = `0xFF`), not the V2/SSD1683 module. Full refresh only; measured 15.8–23.2 s; no true grayscale. Pins: DIN GP11, CLK GP10, CS GP9, DC GP8, RST GP12, BUSY GP13; user switches KEY0/GP15, KEY1/GP17 (active low). The panel has **no touch controller**. The two side-actuated switches on the left PCB edge are verified: KEY0 = previous page, KEY1 = next page. Tapping the printed `<`/`>` markers does nothing.
- Wi-Fi for the dashboard: dedicated **`krys_dom_IoT`** only, 2.4 GHz/WPA2, no fallback. DHCP reserves `192.168.4.51` for MAC `28:cd:c1:0d:34:f0`; DNS PTR discovers `raspberry-pi-pico-w-01.iot` and verifies it. Wi-Fi password lives only in gitignored `secrets.py`.

## Board state and safety

- The board already contains a user program: `main.py` (~22 KB, 4.2-inch e-paper display) and `lib/`. A verified local backup is at `experiments/pico-1-w-led-blink/backups/pico-w-main.py` (gitignored). Do not delete it.
- Default to `mpremote run` / `mpremote mount . run` for verification; both execute without writing to the board filesystem.
- The dashboard is multi-module, so run it from its experiment directory with:

  ```sh
  .venv/bin/mpremote mount . run main.py
  ```

  `main.py` allocates the canvas before the panel clear; do not move that order without checking the heap. The first boot is ~45–60 s (vendor clear + first frame).
- **Never** overwrite `:main.py` without first copying it to the experiment's gitignored `backups/` and verifying the copy:

  ```sh
  .venv/bin/mpremote fs cp :main.py backups/pico-w-main.py
  ```

- Only deploy (`mpremote fs cp main.py :main.py`) when the user explicitly asks. Restore with the reverse copy plus a board reset.
- Serial access is exclusive: never run `mpremote` commands in parallel, including from two agents or tools. A second process fails with "device may be in use by another program".

## Host tooling

- Python 3 plus `mpremote`, installed into an experiment-local `.venv` (gitignored).
- From the experiment directory:

  ```sh
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
  .venv/bin/mpremote mount . run main.py
  ```

  The first experiment is single-file and uses `.venv/bin/mpremote run main.py`.

- Keep `requirements.txt` pinned to the verified `mpremote` version.

## Documentation sources

- Pico-series boards: https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html
- Pico W LED and pinout facts: the same page, "Wireless board layout" section (`WL_GPIO0`).
- MicroPython RP2 quick reference: https://docs.micropython.org/en/latest/rp2/quickref.html
- E-paper module: https://www.waveshare.com/wiki/Pico-ePaper-4.2-B and the curated, locally mirrored docs under `experiments/pico-2-w-epaper-dashboard/docs/`.
- Weather: https://open-meteo.com/ (no key; attribution on screen).
