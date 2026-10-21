import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

from canvas import BLACK, RED, WHITE, Canvas, codepoints, text_width  # noqa: E402
from font_large import FONT as LARGE  # noqa: E402
from font_small import FONT as SMALL  # noqa: E402


class CanvasEncodingTests(unittest.TestCase):
    def test_native_plane_values(self):
        canvas = Canvas(16, 8)
        canvas.clear(WHITE)
        self.assertEqual(canvas.black, bytearray([0xFF] * 16))
        self.assertEqual(canvas.red, bytearray([0xFF] * 16))

        canvas.pixel(0, 0, BLACK)
        self.assertEqual(canvas.black[0], 0x7F)  # MSB first
        self.assertEqual(canvas.red[0], 0xFF)
        self.assertEqual(canvas.get_color(0, 0), BLACK)

        canvas.pixel(7, 1, RED)
        index = 1 * 2
        self.assertEqual(canvas.black[index], 0xFF)
        self.assertEqual(canvas.red[index], 0xFE)
        self.assertEqual(canvas.get_color(7, 1), RED)

    def test_full_clear_colours(self):
        canvas = Canvas(16, 8)
        canvas.clear(BLACK)
        self.assertEqual(canvas.black, bytearray([0x00] * 16))
        self.assertEqual(canvas.red, bytearray([0xFF] * 16))
        self.assertEqual(canvas.get_color(3, 3), BLACK)

        canvas.clear(RED)
        self.assertEqual(canvas.black, bytearray([0xFF] * 16))
        self.assertEqual(canvas.red, bytearray([0x00] * 16))
        self.assertEqual(canvas.get_color(3, 3), RED)

    def test_fill_rect_matches_pixel_reference(self):
        canvas = Canvas(40, 20)
        canvas.clear(WHITE)
        canvas.fill_rect(3, 2, 30, 10, BLACK)
        canvas.fill_rect(20, 5, 15, 5, RED)
        canvas.fill_rect(0, 15, 40, 3, BLACK)

        reference = Canvas(40, 20)
        reference.clear(WHITE)
        for y in range(2, 12):
            for x in range(3, 33):
                reference.pixel(x, y, BLACK)
        for y in range(5, 10):
            for x in range(20, 35):
                reference.pixel(x, y, RED)
        for y in range(15, 18):
            for x in range(40):
                reference.pixel(x, y, BLACK)

        self.assertEqual(bytes(canvas.black), bytes(reference.black))
        self.assertEqual(bytes(canvas.red), bytes(reference.red))

    def test_bayer_pattern(self):
        canvas = Canvas(8, 8)
        canvas.clear(WHITE)
        canvas.dither_rect(0, 0, 4, 4, RED, WHITE, 8)
        self.assertEqual(canvas.get_color(0, 0), RED)
        self.assertEqual(canvas.get_color(1, 0), WHITE)
        self.assertEqual(canvas.get_color(0, 1), WHITE)
        self.assertEqual(canvas.get_color(3, 3), RED)


class FontTests(unittest.TestCase):
    def test_polish_glyphs_exist(self):
        for char in "ąćęłńóśźżĄĆĘŁŃÓŚŹŻ°×":
            self.assertIn(ord(char), SMALL.glyphs, char)
        self.assertIn(ord("×"), LARGE.glyphs)
        self.assertNotIn(ord("A"), LARGE.glyphs)

    def test_text_width_and_pangram(self):
        self.assertEqual(text_width("Zażółć", SMALL), 6 * SMALL.advance)
        self.assertEqual(len(list(codepoints("Zażółć gęślą jaźń"))), 17)
        canvas = Canvas(140, 20)
        canvas.clear(WHITE)
        canvas.text(0, 0, "Łódź", BLACK, SMALL)
        self.assertTrue(any(value != 0xFF for value in canvas.black))


if __name__ == "__main__":
    unittest.main()
