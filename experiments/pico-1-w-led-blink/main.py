"""Blink the onboard LED on a Raspberry Pi Pico W.

The Pico W LED is connected to WL_GPIO0 on the CYW43439, so use the
board's "LED" identifier rather than GPIO 25.
"""

from machine import Pin
from time import sleep

BLINK_INTERVAL_SECONDS = 0.5

led = Pin("LED", Pin.OUT)

try:
    while True:
        led.toggle()
        print("LED on" if led.value() else "LED off")
        sleep(BLINK_INTERVAL_SECONDS)
except KeyboardInterrupt:
    led.off()
    print("Stopped; LED off")
