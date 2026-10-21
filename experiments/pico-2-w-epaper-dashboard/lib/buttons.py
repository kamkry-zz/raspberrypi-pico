"""Debounced page buttons with short/long press detection."""

import time

from machine import Pin


class Buttons:
    def __init__(self, pins=(15, 17), debounce_ms=300, long_ms=1200):
        self.pins = [Pin(pin, Pin.IN, Pin.PULL_UP) for pin in pins]
        self.debounce_ms = debounce_ms
        self.long_ms = long_ms
        self.last = [0 for _ in pins]
        self.pressed = [0 for _ in pins]
        self.down = [False for _ in pins]
        self.latched = None
        for index, pin in enumerate(self.pins):
            pin.irq(trigger=Pin.IRQ_FALLING, handler=self._handler(index))

    def _handler(self, index):
        def handler(pin):
            now = time.ticks_ms()
            if time.ticks_diff(now, self.last[index]) >= self.debounce_ms:
                self.last[index] = now
                self.pressed[index] = now
                self.latched = index

        return handler

    def poll(self):
        now = time.ticks_ms()

        # Direct polling fallback: catches a press even if the IRQ did not
        # fire.  The IRQ still latches presses that happen during a display.
        if self.latched is None:
            for index, pin in enumerate(self.pins):
                if pin.value() == 0:
                    if not self.down[index] and time.ticks_diff(now, self.last[index]) >= self.debounce_ms:
                        self.last[index] = now
                        self.pressed[index] = now
                        self.latched = index
                        self.down[index] = True
                else:
                    self.down[index] = False

        index = self.latched
        if index is None:
            return None
        if self.pins[index].value() == 0:
            if time.ticks_diff(now, self.pressed[index]) >= self.long_ms:
                self.latched = None
                return ("long", index)
            return None
        self.latched = None
        return ("short", index)
