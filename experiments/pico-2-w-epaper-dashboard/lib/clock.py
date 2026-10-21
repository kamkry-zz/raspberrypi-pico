"""Monotonic local clock anchored to NTP or the weather HTTP Date."""

import time

import config
import timeutil as T


class Clock:
    def __init__(self):
        self.base_epoch = None
        self.base_ticks = None
        self.offset_s = config.UTC_OFFSET_FALLBACK_S

    def set(self, epoch, offset_s=None):
        self.base_epoch = int(epoch)
        self.base_ticks = time.ticks_ms()
        if offset_s is not None:
            self.offset_s = int(offset_s)

    def set_offset(self, offset_s):
        self.offset_s = int(offset_s)

    def epoch(self):
        if self.base_epoch is None:
            return None
        elapsed = time.ticks_diff(time.ticks_ms(), self.base_ticks) // 1000
        return self.base_epoch + elapsed

    def now(self):
        epoch = self.epoch()
        if epoch is None:
            return None
        return T.local_tuple(epoch, self.offset_s)

    def synced(self):
        return self.base_epoch is not None
