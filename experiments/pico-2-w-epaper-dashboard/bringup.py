"""One-frame hardware bring-up for the Pico-ePaper-4.2-B.

Run without writing to the board:

    .venv/bin/mpremote mount . run bringup.py

The frame is deliberately simple: three full-width colour bands, Polish text,
fine geometry and dither patches.  The measured refresh timing is printed to
the serial console; the panel is put back to sleep afterwards.
"""

import sys
import time

sys.path.append("lib")

import config
import testpattern
from canvas import Canvas
from epd42b import EPD42B


def main():
    canvas = Canvas(config.WIDTH, config.HEIGHT)
    testpattern.draw(canvas)

    print("EPD bring-up: init + vendor clear (this takes one waveform)...")
    panel = EPD42B()
    print("Panel revision:", panel.revision, "raw 0x2F:", panel.revision_raw)
    print("Init:", panel.last_init_ms, "ms")
    print("Sending frame...")
    panel.display(canvas.black, canvas.red)
    print("Frame timing:", panel.timing_text())
    print("Refresh count:", panel.refresh_count)
    print("Panel left awake, matching the working legacy program.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
    except Exception as exc:  # noqa: BLE001 - serial is the only debug channel
        print("ERROR:", repr(exc))
        raise
    finally:
        time.sleep_ms(10)
