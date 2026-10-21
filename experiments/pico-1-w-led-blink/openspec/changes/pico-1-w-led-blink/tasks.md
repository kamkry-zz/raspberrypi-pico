## 1. Experiment setup

- [x] 1.1 Create `README.md` in the experiment with the verified board summary, host setup, `mpremote run` verification command, deploy command, and backup/restore commands.
- [x] 1.2 Add an experiment-local `requirements.txt` pinning the verified `mpremote` version.
- [x] 1.3 Add an experiment-local `.gitignore` covering `.venv/`, `backups/`, and `__pycache__/`.
- [x] 1.4 Create `docs/pico-w.md` with Pico W hardware facts (RP2040, 264 kB SRAM, 2 MB flash, CYW43439, LED on `WL_GPIO0`, serial-only USB) and links to the official Pico-series and MicroPython documentation.

## 2. Blink experiment

- [x] 2.1 Create `main.py` using `machine.Pin("LED", machine.Pin.OUT)`, a 0.5-second on/off cycle, and a `KeyboardInterrupt` handler that turns the LED off without a traceback.
- [x] 2.2 Document purpose, no wiring, run command, expected result, and interruption behaviour in the experiment `README.md`.

## 3. Board safety and verification

- [x] 3.1 Create an experiment-local `.venv` and install `requirements.txt`.
- [x] 3.2 Detect the board port with `.venv/bin/mpremote connect list` and record it in `docs/pico-w.md` as an example, not a hardcoded requirement.
- [x] 3.3 Back up the board's existing `:main.py` to `backups/pico-w-main.py` and verify the copy matches the board file before any write.
- [x] 3.4 From the experiment directory, verify with `.venv/bin/mpremote run main.py` and confirm the onboard LED blinks.
- [x] 3.5 Confirm with `.venv/bin/mpremote ls` that the board's `main.py` is unchanged after the run-only verification.

## 4. Agent guidance

- [x] 4.1 Verify the root `AGENTS.md` notes describe the experiment-local layout, that OpenSpec commands run from inside the experiment, the verified hardware facts, and the backup rule.

## 5. Final checks

- [x] 5.1 From `experiments/pico-1-w-led-blink/`, run `openspec validate pico-1-w-led-blink --strict` and fix any reported issues.
- [x] 5.2 Review the experiment documentation commands against the actual files and board state.
