"""OTA boot selector: which code runs this boot (frozen; never shipped OTA).

The frozen firmware is the **factory image**. An over-the-air bundle lives in
``/.ota/a`` or ``/.ota/b`` (``config.mpy`` + ``lib/*.mpy``); :func:`select`
puts the chosen slot first on ``sys.path`` so it wins over ``.frozen``.

A newly installed bundle runs on **trial**: every trial boot is counted on
flash *before* the app starts (crash, watchdog hang and power loss all
count), and :func:`commit` (called once the first frame reaches the panel)
makes it active. After ``MAX_ATTEMPTS`` uncommitted boots the trial is
dropped and blacklisted, and the previous slot (or factory) runs again.
Holding KEY1 while powering up boots the factory image for one boot.

State (``/.ota/state.json``, written atomically)::

    {"active": {"slot", "build", "version", "micropython"} | null,
     "trial": {...} | null, "attempts": int, "previous": {...} | null,
     "blacklist": [build, ...], "pending": [{"event", "build", "detail"}],
     "etag": str | null}
"""

import json
import os
import sys

# Not an identifier on purpose: MicroPython imports a bare directory as a
# package and '' precedes '.frozen' on sys.path, so a directory "/ota" would
# shadow the frozen ``ota`` module (seen on the board, 2026-11-11).
ROOT = "/.ota"
STATE_FILE = ROOT + "/state.json"
MAX_ATTEMPTS = 3
KEY_FACTORY = 17  # KEY1, active low
KEY_MAINT = 15  # KEY0: maintenance boots do not count as trial attempts
MAINT_FLAG = "/maint"
BLACKLIST_KEEP = 10
PENDING_KEEP = 8

# What this boot runs; read by the app for metrics and by ota.check().
selected = {"state": "factory", "slot": None, "build": None, "version": None, "reason": ""}


def micropython_version():
    return ".".join(str(part) for part in sys.implementation.version[:3])


def load():
    try:
        with open(STATE_FILE) as handle:
            state = json.load(handle)
        if isinstance(state, dict):
            return state
    except (OSError, ValueError):
        pass
    return {}


def save(state):
    try:
        os.mkdir(ROOT)
    except OSError:
        pass
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(state, handle)
    os.rename(tmp, STATE_FILE)


def slot_path(slot):
    return ROOT + "/" + slot


def _exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _key_held(pin_number):
    try:
        import machine
        import time

        pin = machine.Pin(pin_number, machine.Pin.IN, machine.Pin.PULL_UP)
        held = 0
        for _ in range(10):
            if pin.value() == 0:
                held += 1
            time.sleep_ms(10)
        return held >= 8
    except Exception:  # host tests / no GPIO
        return False


def _maintenance_boot():
    return _exists(MAINT_FLAG) or _key_held(KEY_MAINT)


def _usable(info):
    """A slot is usable if its files exist and match the running MicroPython."""
    return (
        isinstance(info, dict)
        and info.get("slot") in ("a", "b")
        and info.get("micropython") == micropython_version()
        and _exists(slot_path(info["slot"]) + "/lib")
    )


def _queue(state, event, build, detail):
    pending = state.setdefault("pending", [])
    pending.append({"event": event, "build": build, "detail": detail})
    del pending[:-PENDING_KEEP]


def _use(info, kind, reason=""):
    base = slot_path(info["slot"])
    for path in (base + "/lib", base):
        if path in sys.path:
            sys.path.remove(path)
    sys.path.insert(0, base + "/lib")
    sys.path.insert(0, base)  # config.mpy
    selected.update(
        {"state": kind, "slot": info["slot"], "build": info.get("build"), "version": info.get("version"), "reason": reason}
    )


def select(factory_key=KEY_FACTORY):
    """Pick and activate the code for this boot. Never raises."""
    try:
        _select(factory_key)
    except Exception as exc:  # a broken state file must never block the boot
        print("otaboot: %r; booting factory" % (exc,))
        selected.update({"state": "factory", "slot": None, "build": None, "version": None, "reason": "error"})
    print("otaboot: %(state)s slot=%(slot)s build=%(build)s %(reason)s" % selected)
    return selected


def _select(factory_key):
    if _key_held(factory_key):
        selected["reason"] = "KEY1"
        return
    state = load()
    trial = state.get("trial")
    if trial:
        if not _maintenance_boot():
            state["attempts"] = state.get("attempts", 0) + 1
        if state.get("attempts", 0) > MAX_ATTEMPTS or not _usable(trial):
            build = trial.get("build") if isinstance(trial, dict) else None
            blacklist = state.setdefault("blacklist", [])
            if build is not None and build not in blacklist:
                blacklist.append(build)
                del blacklist[:-BLACKLIST_KEEP]
            _queue(state, "rolled_back", build, "not committed after %d boots" % MAX_ATTEMPTS)
            state["trial"] = None
            state["attempts"] = 0
            state["rolled_back"] = build
            save(state)
            selected["reason"] = "rolled back build %s" % build
        else:
            save(state)  # the attempt is on flash before the app starts
            _use(trial, "trial", "attempt %d/%d" % (state["attempts"], MAX_ATTEMPTS))
            return
    active = state.get("active")
    if active and _usable(active):
        _use(active, "active", selected["reason"])
    elif active:
        selected["reason"] = "active slot unusable (firmware changed?)"


def commit():
    """Called after the first frame reached the panel: keep the trial build."""
    if selected["state"] != "trial":
        return False
    state = load()
    trial = state.get("trial")
    if not trial or trial.get("slot") != selected["slot"]:
        return False
    state["previous"] = state.get("active")
    state["active"] = trial
    state["trial"] = None
    state["attempts"] = 0
    _queue(state, "committed", trial.get("build"), None)
    save(state)
    selected["state"] = "active"
    print("otaboot: committed build %s" % trial.get("build"))
    return True


def inactive_slot(state):
    active = state.get("active") or {}
    return "b" if active.get("slot") == "a" else "a"
