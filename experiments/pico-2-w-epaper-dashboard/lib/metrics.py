"""Pico W metrics for the dashboard."""

import gc
import os
import time

import machine

_BOOT_TICKS = time.ticks_ms()
_ACTIVE_MS = 0
_LAST_GATHER_TICKS = _BOOT_TICKS
_LAST_ACTIVE_MS = 0


def mark_active(milliseconds):
    global _ACTIVE_MS
    if milliseconds > 0:
        _ACTIVE_MS += int(milliseconds)


def reset_interval():
    """Start a fresh activity-reporting interval (used after boot)."""
    global _LAST_GATHER_TICKS, _LAST_ACTIVE_MS
    _LAST_GATHER_TICKS = time.ticks_ms()
    _LAST_ACTIVE_MS = _ACTIVE_MS


def uptime_s():
    return time.ticks_diff(time.ticks_ms(), _BOOT_TICKS) // 1000


def reset_cause():
    try:
        value = machine.reset_cause()
    except Exception:
        return "—"
    for name, label in (
        ("PWRON_RESET", "PWRON"),
        ("HARD_RESET", "HARD"),
        ("WDT_RESET", "WDT"),
        ("DEEPSLEEP_RESET", "DEEPSLEEP"),
        ("SOFT_RESET", "SOFT"),
    ):
        expected = getattr(machine, name, None)
        if expected is not None and value == expected:
            return label
    return str(value)


def internal_temp():
    try:
        raw = machine.ADC(4).read_u16()
        voltage = raw * 3.3 / 65535.0
        return 27.0 - (voltage - 0.706) / 0.001721
    except Exception:
        return 0.0


def flash_usage():
    try:
        stat = os.statvfs("/")
        block = stat[0]
        total = block * stat[2]
        free = block * stat[4]
        return total - free, total
    except Exception:
        return 0, 0


def gather(panel=None, active_ms=None):
    global _LAST_GATHER_TICKS, _LAST_ACTIVE_MS

    gc.collect()
    free = gc.mem_free()
    allocated = gc.mem_alloc()
    flash_used, flash_total = flash_usage()
    uptime = uptime_s()

    now = time.ticks_ms()
    elapsed = time.ticks_diff(now, _LAST_GATHER_TICKS)
    active = _ACTIVE_MS - _LAST_ACTIVE_MS if active_ms is None else int(active_ms)
    _LAST_GATHER_TICKS = now
    _LAST_ACTIVE_MS = _ACTIVE_MS

    if elapsed > 0:
        active_pct = 100.0 * active / elapsed
    else:
        active_pct = 0.0
    if active_pct < 0.0:
        active_pct = 0.0
    if active_pct > 100.0:
        active_pct = 100.0
    try:
        frequency = machine.freq() // 1_000_000
    except Exception:
        frequency = 0

    metrics = {
        "uptime_s": uptime,
        "heap_used": allocated,
        "heap_total": free + allocated,
        "flash_used": flash_used,
        "flash_total": flash_total,
        "temp_c": internal_temp(),
        "active_pct": active_pct,
        "freq_mhz": frequency,
        "reset_cause": reset_cause(),
        "firmware": os.uname().release,
        "transfer_ms": 0,
        "busy_ms": 0,
        "total_ms": 0,
        "refresh_count": 0,
    }
    if panel is not None:
        metrics.update(
            {
                "transfer_ms": panel.last_transfer_ms,
                "busy_ms": panel.last_busy_ms,
                "total_ms": panel.last_total_ms,
                "refresh_count": panel.refresh_count,
                "revision": panel.revision,
            }
        )
    return metrics
