"""Scan every free GPIO for a switch closure.

Run:
    .venv/bin/mpremote mount . run pin_scan.py

Press the left-edge KEY0/KEY1 switches while it runs.  The first 60 s use
pull-ups (active-low switches); the second 60 s use pull-downs (active-high).
Every pin change is printed.  Display pins GP8-GP13 are left untouched.
"""

import time

from machine import Pin

# GP0-GP7, GP14-GP22 and GP26-GP28 are free on the Pico W / module.
FREE = (0, 1, 2, 3, 4, 5, 6, 7, 14, 15, 16, 17, 18, 19, 20, 21, 22, 26, 27, 28)


def phase(pull, seconds):
    pins = [Pin(number, Pin.IN, pull) for number in FREE]
    started = time.ticks_ms()
    last = [pin.value() for pin in pins]
    label = "PULL_UP" if pull == Pin.PULL_UP else "PULL_DOWN"
    print("phase", label, "initial", dict(zip(FREE, last)))
    last_heartbeat = started
    while time.ticks_diff(time.ticks_ms(), started) < seconds * 1000:
        for index, pin in enumerate(pins):
            value = pin.value()
            if value != last[index]:
                print("change", FREE[index], last[index], "->", value, "phase", label)
                last[index] = value
        if time.ticks_diff(time.ticks_ms(), last_heartbeat) >= 15000:
            last_heartbeat = time.ticks_ms()
            print("heartbeat", label)
        time.sleep_ms(20)
    print("phase done", label)


print("GPIO scan; press the left-edge switches now")
phase(Pin.PULL_UP, 60)
phase(Pin.PULL_DOWN, 60)
print("done")
