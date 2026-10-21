"""Driver for the Pico-ePaper-4.2-B, based on the proven vendor sequence.

The low-level init/clear/display methods are intentionally kept close to the
working Waveshare MicroPython demo that already runs on this board.  The only
functional changes are:

* clear buffers are built with ``bytes`` instead of 15,000-element lists, so
  they also work when the dashboard fonts and canvas are loaded;
* a full-refresh wait is made explicit after each update;
* timings and a revision property are exposed for the capability page.

The display data is native black plane (1 = white) and native red plane
(0 = red).  The vendor display method expects its red framebuffer to use
1 = red, so :meth:`display` converts before calling it.

This unit reports the **old** revision (0x2F reads 0xFF).  The V2 command path
is retained for completeness and is selected automatically.
"""

import time
import utime
from machine import Pin, SPI

EPD_WIDTH = 400
EPD_HEIGHT = 300
SCK_PIN = 10
DIN_PIN = 11
RST_PIN = 12
DC_PIN = 8
CS_PIN = 9
BUSY_PIN = 13


class EPD42B:
    WIDTH = EPD_WIDTH
    HEIGHT = EPD_HEIGHT
    PLANE_BYTES = (EPD_WIDTH // 8) * EPD_HEIGHT
    FILL_CHUNK = 256

    def __init__(self, waveform_ms=24000, clear_wait_ms=24000):
        self.reset_pin = Pin(RST_PIN, Pin.OUT)
        self.busy_pin = Pin(BUSY_PIN, Pin.IN, Pin.PULL_UP)
        self.cs_pin = Pin(CS_PIN, Pin.OUT)
        self.sck_pin = 1
        self.din_pin = 1
        self.width = EPD_WIDTH
        self.height = EPD_HEIGHT
        self.flag = 0
        self.revision_raw = None
        self.waveform_ms = waveform_ms
        self.asleep = False

        self.last_init_ms = 0
        self.last_transfer_ms = 0
        self.last_busy_ms = 0
        self.last_total_ms = 0
        self.refresh_count = 0

        self.spi = SPI(
            1,
            baudrate=4_000_000,
            sck=Pin(SCK_PIN),
            mosi=Pin(DIN_PIN),
            polarity=0,
            phase=0,
        )
        self.dc_pin = Pin(DC_PIN, Pin.OUT)

        started = time.ticks_ms()
        self.EPD_4IN2B_Init()
        self.last_init_ms = time.ticks_diff(time.ticks_ms(), started)

        # The vendor clear starts a full waveform.  On this unit ReadBusy()
        # waits for it; only add the fixed fallback if it returned immediately.
        clear_started = time.ticks_ms()
        self.EPD_4IN2B_Clear()
        clear_elapsed = time.ticks_diff(time.ticks_ms(), clear_started)
        if clear_elapsed < 2000:
            time.sleep_ms(clear_wait_ms)
            clear_elapsed += clear_wait_ms
        self.last_transfer_ms = 0
        self.last_busy_ms = clear_elapsed
        self.last_total_ms = clear_elapsed
        self.refresh_count = 1

    # ------------------------------------------------------------------ basics
    @property
    def revision(self):
        return "v2" if self.flag == 1 else "old"

    def digital_write(self, pin, value):
        pin.value(value)

    def digital_read(self, pin):
        return pin.value()

    def delay_ms(self, delaytime):
        utime.sleep(delaytime / 1000.0)

    def spi_writebyte(self, data):
        self.spi.write(bytearray(data))

    def gpio_init(self):
        self.spi.deinit()

    def spi_init(self):
        self.spi = SPI(
            1,
            baudrate=4_000_000,
            sck=Pin(SCK_PIN),
            mosi=Pin(DIN_PIN),
            polarity=0,
            phase=0,
        )
        self.dc_pin = Pin(DC_PIN, Pin.OUT)

    def reset(self):
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(200)
        self.digital_write(self.reset_pin, 0)
        self.delay_ms(2)
        self.digital_write(self.reset_pin, 1)
        self.delay_ms(200)

    def send_command(self, command):
        self.digital_write(self.dc_pin, 0)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([command])
        self.digital_write(self.cs_pin, 1)

    def send_data(self, data):
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        self.spi_writebyte([data])
        self.digital_write(self.cs_pin, 1)

    def send_data1(self, buf):
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        # buf is already bytes/bytearray in this driver; avoid a 15 KB copy.
        self.spi.write(buf)
        self.digital_write(self.cs_pin, 1)

    def send_read(self):
        j = 0x00
        self.sck_pin = Pin(SCK_PIN, Pin.OUT)
        self.din_pin = Pin(DIN_PIN, Pin.IN, Pin.PULL_UP)
        self.digital_write(self.dc_pin, 1)
        self.digital_write(self.cs_pin, 0)
        for _ in range(8):
            self.digital_write(self.sck_pin, 0)
            j = j << 1
            if self.digital_read(self.din_pin) == 1:
                j = j | 0x01
            else:
                j = j & 0xFE
            self.digital_write(self.sck_pin, 1)
        self.digital_write(self.cs_pin, 1)
        return j

    def ReadBusy(self):
        if self.flag == 1:
            while self.digital_read(self.busy_pin) == 1:
                self.delay_ms(100)
        else:
            while self.digital_read(self.busy_pin) == 0:
                self.delay_ms(100)

    def TurnOnDisplay(self):
        if self.flag == 1:
            self.send_command(0x22)
            self.send_data(0xF7)
            self.send_command(0x20)
            self.ReadBusy()
        else:
            self.send_command(0x12)
            self.delay_ms(100)
            self.ReadBusy()

    # --------------------------------------------------------------- sequences
    def EPD_4IN2B_Init(self):
        i = 0x00
        self.reset()
        self.send_command(0x2F)

        self.delay_ms(100)
        self.gpio_init()
        i = self.send_read()
        self.revision_raw = i
        self.spi_init()

        if i == 0x01:
            self.flag = 1
            self.ReadBusy()
            self.send_command(0x12)
            self.ReadBusy()

            self.send_command(0x3C)
            self.send_data(0x05)

            self.send_command(0x18)
            self.send_data(0x80)

            self.send_command(0x11)
            self.send_data(0x03)

            self.send_command(0x44)
            self.send_data(0x00)
            self.send_data(self.width // 8 - 1)

            self.send_command(0x45)
            self.send_data(0x00)
            self.send_data(0x00)
            self.send_data((self.height - 1) % 256)
            self.send_data((self.height - 1) // 256)

            self.send_command(0x4E)
            self.send_data(0x00)
            self.send_command(0x4F)
            self.send_data(0x00)
            self.send_data(0x00)
            self.ReadBusy()
        else:
            self.flag = 0
            self.send_command(0x04)  # POWER_ON
            self.ReadBusy()
            self.send_command(0x00)  # panel setting
            self.send_data(0x0F)

    def _send_fill(self, value):
        """Stream a full plane fill in small chunks.

        The vendor demo builds a 15 KB ``bytes`` object.  After Wi-Fi and the
        weather JSON are alive that allocation can fail with MemoryError, so
        the fill is streamed instead.  CS may rise between chunks; the
        controller's data write pointer continues.
        """
        block = bytes((value,)) * self.FILL_CHUNK
        remaining = self.PLANE_BYTES
        while remaining > 0:
            count = min(self.FILL_CHUNK, remaining)
            self.send_data1(block if count == self.FILL_CHUNK else block[:count])
            remaining -= count

    def EPD_4IN2B_Clear(self):
        if self.flag == 1:
            self.send_command(0x24)
            self._send_fill(0xFF)
            self.send_command(0x26)
            self._send_fill(0x00)
        else:
            self.send_command(0x10)
            self._send_fill(0xFF)
            self.send_command(0x13)
            self._send_fill(0x00)
        self.TurnOnDisplay()

    def EPD_4IN2B_Display(self, blackImage, redImage):
        high = self.height
        wide = self.width // 8
        if self.flag == 1:
            self.send_command(0x24)
            self.send_data1(blackImage)
            self.send_command(0x26)
            for j in range(0, high):
                for i in range(0, wide):
                    self.send_data(~redImage[i + j * wide])
        else:
            self.send_command(0x10)
            self.send_data1(blackImage)
            self.send_command(0x13)
            for j in range(0, high):
                for i in range(0, wide):
                    self.send_data(~redImage[i + j * wide])
        self.TurnOnDisplay()

    def Sleep(self):
        if self.flag == 1:
            self.send_command(0x10)
            self.send_data(0x03)
        else:
            self.send_command(0x50)
            self.send_data(0xF7)
            self.send_command(0x02)
            self.ReadBusy()
            self.send_command(0x07)
            self.send_data(0xA5)
        self.asleep = True

    # --------------------------------------------------------------- dashboard
    def init(self):
        started = time.ticks_ms()
        self.EPD_4IN2B_Init()
        self.last_init_ms = time.ticks_diff(time.ticks_ms(), started)
        self.asleep = False

    def display_block(self, black, red):
        """Fast path: both native planes are sent as blocks.

        The black block path is already used by the vendor.  The red block
        path is verified separately; if a particular unit shows artifacts,
        fall back to :meth:`display_safe`.
        """
        if len(black) != self.PLANE_BYTES or len(red) != self.PLANE_BYTES:
            raise ValueError("each plane must be exactly 15000 bytes")
        if self.asleep:
            self.init()

        started = time.ticks_us()
        if self.flag == 1:
            self.send_command(0x24)
            self.send_data1(black)
            self.send_command(0x26)
            self.send_data1(red)
        else:
            self.send_command(0x10)
            self.send_data1(black)
            self.send_command(0x13)
            self.send_data1(red)
        sent = time.ticks_us()
        busy_started = time.ticks_ms()
        self.TurnOnDisplay()
        busy_elapsed = time.ticks_diff(time.ticks_ms(), busy_started)
        if busy_elapsed < 2000:
            # BUSY returned immediately; use the known waveform fallback.
            time.sleep_ms(self.waveform_ms)
            busy_elapsed += self.waveform_ms
        finished = time.ticks_us()

        self.last_transfer_ms = time.ticks_diff(sent, started) // 1000
        self.last_busy_ms = busy_elapsed
        self.last_total_ms = time.ticks_diff(finished, started) // 1000
        self.refresh_count += 1

    def display(self, black, red):
        """Default display path (currently the fast block transfer)."""
        self.display_block(black, red)

    def clear(self):
        started = time.ticks_ms()
        self.EPD_4IN2B_Clear()
        elapsed = time.ticks_diff(time.ticks_ms(), started)
        if elapsed < 2000:
            time.sleep_ms(self.waveform_ms)
            elapsed += self.waveform_ms
        self.last_transfer_ms = 0
        self.last_busy_ms = elapsed
        self.last_total_ms = elapsed
        self.refresh_count += 1

    def sleep(self):
        if self.asleep:
            return
        self.Sleep()

    def close(self):
        self.spi.deinit()
        self.reset_pin.value(0)

    def timing_text(self):
        return "init {} ms, transfer {} ms, panel {} ms, total {} ms".format(
            self.last_init_ms,
            self.last_transfer_ms,
            self.last_busy_ms,
            self.last_total_ms,
        )
