## Purpose

Provide a repeatable, self-contained structure for MicroPython experiments on the Pico W, with safe tooling that never destroys existing programs on the board.

## ADDED Requirements

### Requirement: Self-contained experiment directories
Each experiment SHALL live in its own directory under `experiments/` and contain all files needed to understand, plan, and run it, without importing code from another experiment.

#### Scenario: Experiment can be copied alone
- **WHEN** a single experiment directory is copied to another machine
- **THEN** its `main.py`, `README.md`, `docs/`, `requirements.txt`, and `openspec/` are sufficient to run and understand the experiment

#### Scenario: Directory naming
- **WHEN** a new experiment is added
- **THEN** its directory is named descriptively in kebab-case under `experiments/`, for example `experiments/pico-1-w-led-blink/`

### Requirement: Experiment-local OpenSpec root
Each experiment SHALL contain its own OpenSpec root at `openspec/`, and OpenSpec commands for that experiment SHALL be run from the experiment directory.

#### Scenario: Planning stays with the experiment
- **WHEN** an agent runs OpenSpec commands for this experiment
- **THEN** it changes into `experiments/pico-1-w-led-blink/` first, where `openspec/changes/pico-1-w-led-blink/` is resolved as the change

#### Scenario: No repo-root OpenSpec dependency
- **WHEN** the experiment directory is moved or copied
- **THEN** its OpenSpec artifacts move with it and do not depend on a repository-root `openspec/` directory

### Requirement: Experiment documentation
Every experiment README SHALL state its purpose, required wiring, the command to run it, and the observable expected result. Board and tooling details SHALL be documented inside the experiment.

#### Scenario: Reader can reproduce an experiment
- **WHEN** a reader opens an experiment README
- **THEN** they can determine whether any wiring is needed and which command to run

### Requirement: Non-destructive verification
The documented default way to verify an experiment SHALL execute it without writing to the board's filesystem.

#### Scenario: Run without deploying
- **WHEN** an experiment is verified with `mpremote run main.py` from its own directory
- **THEN** the program executes and the board's stored `main.py` is unchanged

### Requirement: Backup before overwriting board files
Before any command that overwrites the board's existing `main.py`, a copy MUST be saved to the experiment's local `backups/` directory, and `backups/` MUST be excluded from version control.

#### Scenario: Existing program is preserved
- **WHEN** a deploy would replace the board's `main.py`
- **THEN** the previous contents exist in `backups/` before the replacement occurs

#### Scenario: Backup is mandatory
- **WHEN** no backup of the current board `main.py` exists
- **THEN** deployment MUST NOT proceed

### Requirement: Board and tooling documentation
The experiment SHALL document the verified board model, firmware version, serial connection, and the exact setup and run commands, citing the official Pico-series documentation as the source of hardware facts.

#### Scenario: New session can connect
- **WHEN** a new session reads the experiment documentation
- **THEN** it can install the tooling, discover the serial port, run the experiment, and know not to overwrite board files without a backup

### Requirement: Exclusive serial access
Only one process SHALL access the board's serial port at a time.

#### Scenario: Concurrent commands are avoided
- **WHEN** an agent or developer runs board commands
- **THEN** commands are issued sequentially, because concurrent access fails with a port-in-use error
