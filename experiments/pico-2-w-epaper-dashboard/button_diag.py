"""Raw GP15/GP17 button diagnostic.

Run:
    .venv/bin/mpremote mount . run button_diag.py

Press the two small left-edge switches while it runs.  It prints every pin
change and a heartbeat every 10 s.
"""

import time

from machine import Pin

pins = [
    Pin(15, Pin.IN, Pin.PULL_UP),
    Pin(17, Pin.IN, Pin.PULL_UP),
]

started = time.ticks_ms()
last = (pins[0].value(), pins[1].value())
last_heartbeat = started
print("GP15 =", last[0], "GP17 =", last[1], "(1 = released)")
print("Press the left-edge switches now; running for 120 s")

while time.ticks_diff(time.ticks_ms(), started) < 120000:
    now = (pins[0].value(), pins[1].value())
    if now != last:
        print("change: GP15", now[0], "GP17", now[1], "at", time.ticks_ms())
        last = now
    if time.ticks_diff(time.ticks_ms(), last_heartbeat) >= 10000:
        last_heartbeat = time.ticks_ms()
        print("heartbeat: GP15", now[0], "GP17", now[1])
    time.sleep_ms(20)

print("done")
