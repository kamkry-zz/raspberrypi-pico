"""Standalone capability demo for the Pico-ePaper-4.2-B.

Run without Wi-Fi or a configured secrets.py:

    .venv/bin/mpremote mount . run demo.py

It shows three frames in sequence: the bring-up pattern, a 16-level
red/white and black/white dither chart, and the capabilities page.  All
patterns reuse one 30 KB canvas to stay inside the RP2040 heap.
"""

import gc
import sys
import time

sys.path.append("lib")

import config
import metrics
from epd42b import EPD42B


def draw_gradient(canvas):
    canvas.clear(1)
    canvas.fill_rect(0, 0, 400, 30, 0)
    canvas.fill_rect(0, 27, 400, 3, 2)
    canvas.text(10, 5, "RASTROWANIE · 16 POZIOMÓW", 1, _medium())
    canvas.text(390, 6, "400×300", 1, _small(), anchor="right")

    for index in range(16):
        x = 12 + index * 23
        canvas.dither_rect(x, 44, 22, 70, 2, 1, index + 1)
        canvas.rect(x, 44, 22, 70, 0)
        canvas.dither_rect(x, 132, 22, 70, 0, 1, index + 1)
        canvas.rect(x, 132, 22, 70, 0)

    for value in (0, 4, 8, 12, 16):
        canvas.text(12 + value * 23, 208, str(value), 0, _small())

    canvas.text(12, 228, "Czerwień / biel", 0, _small())
    canvas.text(12, 244, "Czerń / biel", 0, _small())
    canvas.fill_rect(0, 278, 400, 1, 0)
    canvas.text(10, 282, "3 KOLORY · DITHERING · PEŁNE ODŚWIEŻANIE", 0, _small())


def _small():
    from font_small import FONT

    return FONT


def _medium():
    from font_medium import FONT

    return FONT


def run():
    gc.collect()
    from canvas import Canvas
    from pages import PAGES
    import testpattern

    gc.collect()
    canvas = Canvas(config.WIDTH, config.HEIGHT)
    gc.collect()
    panel = EPD42B()
    print("panel", panel.revision, "clear", panel.last_total_ms)

    capability_data = {
        "now": None,
        "time_synced": False,
        "offline": True,
        "page": 3,
        "pages": len(PAGES),
        "weather": None,
        "net": {},
        "metrics": metrics.gather(panel),
    }

    frames = (
        ("bring-up", lambda: testpattern.draw(canvas)),
        ("dither", lambda: draw_gradient(canvas)),
        ("capabilities", lambda: PAGES[3](canvas, capability_data)),
    )

    for name, draw in frames:
        print("showing", name)
        draw()
        gc.collect()
        panel.display(canvas.black, canvas.red)
        print("  panel", panel.last_total_ms, "ms")
        time.sleep(5)

    print("demo done; panel keeps the last frame")


run()
