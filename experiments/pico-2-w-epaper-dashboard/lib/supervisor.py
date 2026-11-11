"""Boot supervisor: hardware watchdog, maintenance mode and crash backoff.

The RP2040/RP2350 watchdog (as MicroPython exposes it) tops out at ~8.3 s and cannot be stopped once armed, but
a full e-paper refresh blocks for 16-24 s.  The hardware WDT is therefore fed
from a soft ``machine.Timer`` callback, but only while the application keeps
calling :func:`beat`.  Soft timer callbacks run from the MicroPython scheduler
(also inside ``time.sleep*`` and blocking socket waits), so:

* a long but healthy panel refresh or HTTP request keeps the board alive;
* a Python-level hang (no ``beat()`` for ``stall_ms``) stops feeding and the
  hardware resets the board;
* a hang in C code that never reaches the scheduler stops feeding as well.

Maintenance mode (no app, no watchdog, plain REPL) is entered for exactly one
boot when either:

* the ``/maint`` flag file exists (written by Ctrl-C from ``mpremote``), or
* KEY0 (GP15, active low) is held while the board powers up.

The next reset or power cycle returns to the normal, self-starting dashboard.
"""

import gc
import os
import time

import machine

FLAG = "/maint"
WDT_TIMEOUT_MS = 8000
FEED_PERIOD_MS = 1000

# WATCHDOG_SCRATCH0/1 survive watchdog and machine.reset() resets but are
# cleared by a power-on reset.  The boot ROM uses scratch 4-7 (RP2040) and
# 2-7 (RP2350).  The watchdog block moved: 0x40058000 on the RP2040 is the USB
# PLL on the RP2350, so writing the RP2040 address there kills USB.
import sys

_WATCHDOG = 0x400D8000 if "RP2350" in sys.implementation._machine else 0x40058000
_SCRATCH0 = _WATCHDOG + 0x0C
_SCRATCH1 = _WATCHDOG + 0x10
_MAGIC = 0x5A5A0000
# machine.reset() on the RP2040/RP2350 goes through the watchdog, so a deliberate
# reset reads as WDT.  Tag deliberate resets so a real WDT trip stands out.
_TAGS = ("", "CRASH", "MAINT", "WIFI", "DEPLOY", "MEM", "OTA")
boot_tag = None  # tag of the reset that started this boot, if deliberate

_wdt = None
_timer = None
_beat = time.ticks_ms()
_stall_ms = 300000
_up_last = time.ticks_ms()
_up_ms = 0


def _flag_exists():
    try:
        os.stat(FLAG)
        return True
    except OSError:
        return False


def take_reset_tag():
    """Read and clear the deliberate-reset tag (call once, early in boot)."""
    global boot_tag
    value = machine.mem32[_SCRATCH1]
    machine.mem32[_SCRATCH1] = 0
    if value & 0xFFFF0000 == _MAGIC and 0 < value & 0xFFFF < len(_TAGS):
        boot_tag = _TAGS[value & 0xFFFF]
    return boot_tag


def reset(tag):
    """machine.reset() with a tag that the next boot reports as reset cause."""
    machine.mem32[_SCRATCH1] = _MAGIC | _TAGS.index(tag)
    time.sleep_ms(100)
    machine.reset()


def maintenance_requested(key_pin=None):
    """Return the reason string for a maintenance boot, or None.

    The flag is consumed here, so maintenance mode lasts for one boot only.
    """
    if _flag_exists():
        try:
            os.remove(FLAG)
        except OSError:
            pass
        return "flag"
    if key_pin is not None:
        try:
            pin = machine.Pin(key_pin, machine.Pin.IN, machine.Pin.PULL_UP)
            held = 0
            for _ in range(10):
                if pin.value() == 0:
                    held += 1
                time.sleep_ms(10)
            if held >= 8:
                return "KEY0"
        except Exception:
            pass
    return None


def enter_maintenance():
    """Persist the flag and reset; the next boot stays in the REPL."""
    try:
        with open(FLAG, "w") as handle:
            handle.write("1")
    except OSError:
        pass
    print("Maintenance: rebooting into REPL (no watchdog) for one boot")
    reset("MAINT")


def _tick_uptime():
    global _up_last, _up_ms
    now = time.ticks_ms()
    delta = time.ticks_diff(now, _up_last)
    if delta > 0:
        _up_ms += delta
    _up_last = now


def uptime_ms():
    """Monotonic uptime that does not wrap after ~6 days like ticks_ms."""
    _tick_uptime()
    return _up_ms


def _feed(_timer_obj):
    _tick_uptime()
    if _wdt is not None and time.ticks_diff(time.ticks_ms(), _beat) < _stall_ms:
        _wdt.feed()


def beat():
    global _beat
    _beat = time.ticks_ms()
    _tick_uptime()


def start(stall_ms=300000):
    """Arm the hardware watchdog.  It cannot be disarmed until reset."""
    global _wdt, _timer, _stall_ms
    _stall_ms = int(stall_ms)
    beat()
    _wdt = machine.WDT(timeout=WDT_TIMEOUT_MS)
    _timer = machine.Timer(period=FEED_PERIOD_MS, mode=machine.Timer.PERIODIC, callback=_feed)
    print("Watchdog armed: %d ms hw, %d s stall limit" % (WDT_TIMEOUT_MS, _stall_ms // 1000))


def armed():
    return _wdt is not None


# ------------------------------------------------------------ heap reserve
# The heap has ~60 KB left after the canvas and modules, and fragments over
# time.  A TLS session needs one large contiguous block, so hold one from boot
# and hand it back only around TLS/HTTP work.
_reserve = None
_reserve_size = 0


def reserve(size=None):
    """Take (or re-take) the contiguous heap reserve; returns True if held."""
    global _reserve, _reserve_size
    if size is not None:
        _reserve_size = int(size)
    if _reserve is None and _reserve_size:
        gc.collect()
        try:
            _reserve = bytearray(_reserve_size)
        except MemoryError:
            _reserve = None
    return _reserve is not None


def release():
    """Free the reserve so the next large allocation (TLS) can use it."""
    global _reserve
    _reserve = None
    gc.collect()


# ------------------------------------------------------------ crash backoff
def crash_count():
    value = machine.mem32[_SCRATCH0]
    if value & 0xFFFF0000 == _MAGIC:
        return value & 0xFFFF
    return 0


def _set_crash_count(count):
    machine.mem32[_SCRATCH0] = _MAGIC | (min(count, 0xFFFF) & 0xFFFF)


def clear_crashes():
    _set_crash_count(0)


def crash_reset(reason):
    """Count a fatal error, wait with backoff (keeping the WDT fed), reset.

    The backoff stops a crash loop from running the 24 s panel clear over
    and over: 30 s, 60 s, 120 s ... capped at 15 minutes.
    """
    count = crash_count() + 1
    _set_crash_count(count)
    delay_s = min(30 * (1 << min(count - 1, 5)), 900)
    print("FATAL (%d in a row): %s; reset in %d s" % (count, reason, delay_s))
    until = time.ticks_add(time.ticks_ms(), delay_s * 1000)
    while time.ticks_diff(until, time.ticks_ms()) > 0:
        beat()
        time.sleep_ms(500)
    reset("CRASH")
