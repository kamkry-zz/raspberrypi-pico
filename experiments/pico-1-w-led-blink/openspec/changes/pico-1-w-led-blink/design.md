## Context

See `proposal.md` for motivation and `specs/` for requirements. This change is scoped to one self-contained experiment at `experiments/pico-1-w-led-blink/`, which also contains its own OpenSpec root. Verified environment:

- Raspberry Pi Pico W (RP2040), MicroPython 1.23.0 (2024-06-02), serial `/dev/cu.usbmodem1101`.
- The board presents a USB CDC serial port only; "Board in FS mode" is the USB Full-Speed product string, not a mounted filesystem.
- The board's flash already contains `main.py` (about 22 KB, a 4.2-inch e-paper program) and a `lib/` directory.
- `mpremote` is not installed system-wide; a temporary virtualenv was used to confirm that `machine.Pin("LED")` works and that `mpremote` can list and read board files.
- OpenSpec resolves the nearest root, so a root at `experiments/pico-1-w-led-blink/openspec/` works when commands run from that directory.

## Goals / Non-Goals

**Goals:**

- Make the experiment directory the unit of work: code, docs, tooling requirements, backups, and planning artifacts all live inside it.
- A default workflow that verifies code on hardware without mutating the board's stored program.
- Accurate board documentation for the Pico W variant, including the non-obvious LED wiring.

**Non-Goals:**

- C/C++ Pico SDK development, flashing custom UF2 firmware, or replacing MicroPython.
- Wi-Fi, Bluetooth, or e-paper experiments.
- Automated host-side tests or CI; verification is manual and hardware-dependent.
- Refactoring or removing the existing e-paper program on the board.
- A shared repo-level Python environment or OpenSpec root.

## Decisions

- **Experiment-local OpenSpec root.** `openspec/` lives inside `experiments/pico-1-w-led-blink/`, so the experiment can be moved or copied as a complete unit and its change history travels with it. Alternative: one repo-level root; simpler to run from the repository, but it couples experiments and contradicts the self-contained goal.
- **Root `AGENTS.md` is repo-level guidance, not part of the experiment's OpenSpec scope.** It records the layout, hardware facts, and safety rules so an agent entering at the repository root finds the experiment and runs OpenSpec from the correct directory.
- **MicroPython, not the C/C++ SDK.** The board already runs MicroPython and holds working user code; switching toolchains would require flashing firmware and risk the existing program.
- **`mpremote run` is the default verification path.** It executes a local file over the serial REPL without writing to the board filesystem. Deployment via `mpremote fs cp` is documented but explicit, and requires a backup first. Alternative: Thonny, rejected because it is GUI-driven and not reproducible in an agent session.
- **Duplicate small amounts of code per experiment instead of a shared library.** Experiments are learning artifacts; isolation makes each directory copyable and prevents a change in one experiment from breaking another.
- **Use `machine.Pin("LED")`.** On the Pico W the LED is driven through `WL_GPIO0` on the CYW43439, so `Pin(25)` does not control it. The string identifier is board-agnostic across Pico and Pico W in MicroPython 1.23.
- **Experiment-local virtualenv and pinned `mpremote`.** `.venv/`, `requirements.txt`, and `backups/` live inside the experiment and are gitignored there, so the directory remains portable.
- **Backups live in the experiment's gitignored `backups/`.** The e-paper program is user work not present elsewhere in the repository; preserving it locally is a safety requirement, but it should not be committed without the user's decision.

## Risks / Trade-offs

- **Overwriting the e-paper `main.py`** → Mandatory backup before deploy, `mpremote run` as the default, and a documented restore command.
- **Running OpenSpec from the repository root** → It reports no root; `AGENTS.md` and the experiment README must state that commands run from `experiments/pico-1-w-led-blink/`.
- **Root guidance drifting from the experiment** → Keep the root `AGENTS.md` limited to layout, hardware facts, and safety rules, and point to the experiment README for details.
- **Serial port contention** → Never run `mpremote` commands in parallel; document `mpremote connect list` instead of hardcoding the port.
- **Port name changes across reconnects** → Prefer `mpremote connect auto` and document that the verified name is only an example.
- **MicroPython version differences** → Target features present in 1.23.0 and record the verified version; avoid newer APIs.
- **Deploying an experiment changes boot behaviour** → Explicitly document that copying to `:main.py` replaces the boot program, and how to restore the backup.

## Migration Plan

1. Create the experiment directory and move the OpenSpec root and change into it.
2. Back up the board's current `main.py` to `experiments/pico-1-w-led-blink/backups/` before any write to the board.
3. Verify with `mpremote run main.py` from the experiment directory; no board files change.
4. Optionally deploy with `mpremote fs cp main.py :main.py` and reset the board.
5. Roll back by copying the saved backup back to `:main.py` and resetting.
