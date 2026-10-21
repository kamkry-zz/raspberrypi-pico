## Why

The repository is empty, while the connected Pico W already runs MicroPython 1.23.0 with a 22 KB e-paper program in `main.py`. Each experiment should be a self-contained unit that can be understood, planned, and run on its own, without depending on files elsewhere in the repository.

## What Changes

- Make `experiments/pico-1-w-led-blink/` the first self-contained experiment. It owns its code, README, board documentation, Python requirements, backups, and its OpenSpec root.
- Put the OpenSpec root inside the experiment at `experiments/pico-1-w-led-blink/openspec/`, so planning and implementation commands run from the experiment directory. The change is named `pico-1-w-led-blink`.
- Add `main.py` that blinks the Pico W onboard LED using `machine.Pin("LED", machine.Pin.OUT)`.
- Add `README.md` and `docs/pico-w.md` inside the experiment, documenting the board, wiring, run command, and expected result.
- Add an experiment-local `requirements.txt` pinning `mpremote` and a `.gitignore` covering `.venv/`, `backups/`, and `__pycache__/`.
- Require backing up the board's existing `main.py` to the experiment's gitignored `backups/` before any deploy that overwrites it.
- Record the repository layout, hardware facts, and safety rules in the root `AGENTS.md`.

## Capabilities

### New Capabilities

- `micropython-experiments`: the convention that each experiment is self-contained, including its own OpenSpec root, documentation, tooling, and backup area.
- `led-blink`: behaviour of the Pico W onboard LED blink experiment.

### Modified Capabilities

## Impact

- New files under `experiments/pico-1-w-led-blink/`: `main.py`, `README.md`, `docs/pico-w.md`, `requirements.txt`, `.gitignore`, and `openspec/`.
- Updated: root `AGENTS.md`.
- Board: the existing e-paper `main.py` is preserved by backup; `mpremote run` is the default verification path.
- Dependency: Python 3 plus `mpremote`; no Pico SDK or C/C++ toolchain required.
