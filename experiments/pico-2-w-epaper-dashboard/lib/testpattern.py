"""Hardware test frame: colour bands, Polish glyphs, geometry and dither."""

from canvas import BLACK, RED, WHITE
from font_medium import FONT as MEDIUM
from font_small import FONT as SMALL


def draw(canvas):
    canvas.clear(WHITE)

    # Header
    canvas.fill_rect(0, 0, 400, 40, BLACK)
    canvas.fill_rect(0, 36, 400, 4, RED)
    canvas.text(12, 10, "PICO 4.2-B · BRING-UP", WHITE, MEDIUM)
    canvas.text(388, 10, "400x300", WHITE, SMALL, anchor="right")

    # Black band
    canvas.fill_rect(0, 48, 400, 64, BLACK)
    canvas.text(12, 62, "CZARNY / BLACK", WHITE, MEDIUM)
    canvas.text(12, 84, "0x24 = 00 · 0x26 = FF", WHITE, SMALL)
    canvas.circle(338, 80, 22, WHITE)

    # Red band
    canvas.fill_rect(0, 116, 400, 64, RED)
    canvas.text(12, 130, "CZERWONY / RED", WHITE, MEDIUM)
    canvas.text(12, 152, "0x24 = FF · 0x26 = 00", WHITE, SMALL)
    canvas.fill_rect(316, 128, 64, 40, WHITE)
    canvas.text(348, 140, "RED", RED, SMALL, anchor="center")

    # White band: text, Polish glyphs, geometry and dither.
    canvas.fill_rect(0, 180, 400, 96, WHITE)
    canvas.text(12, 190, "BIAŁY / WHITE", BLACK, MEDIUM)
    canvas.text(12, 212, "Zażółć gęślą jaźń", BLACK, SMALL)
    canvas.text(12, 230, "ąćęłńóśźż ĄĆĘŁŃÓŚŹŻ", BLACK, SMALL)

    # 1 px line fan
    for step in range(0, 9):
        canvas.line(12, 268, 52 + step * 5, 246, BLACK)

    # Outlined red circle and a black/red checker patch.
    canvas.circle(150, 250, 17, RED)
    for yy in range(0, 24):
        for xx in range(0, 24):
            if (xx + yy) & 1:
                canvas.pixel(190 + xx, 238 + yy, RED)

    # Ordered dithers: red/white and black/white at 25, 50, 75 %.
    for index, level in enumerate((4, 8, 12)):
        x = 228 + index * 54
        canvas.text(x, 190, ("%d%%" % (level * 100 // 16)), BLACK, SMALL)
        canvas.dither_rect(x, 204, 46, 28, RED, WHITE, level)
        canvas.rect(x, 204, 46, 28, BLACK)
        canvas.dither_rect(x, 240, 46, 24, BLACK, WHITE, level)
        canvas.rect(x, 240, 46, 24, BLACK)

    # Footer
    canvas.fill_rect(0, 280, 400, 20, BLACK)
    canvas.text(12, 282, "CZASY NA SERIALU · PANEL ŚPI PO ODBIORZE", WHITE, SMALL)
