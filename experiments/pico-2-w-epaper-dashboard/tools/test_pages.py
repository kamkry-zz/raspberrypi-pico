import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "tools"))

import fixtures  # noqa: E402
import pages  # noqa: E402
from canvas import Canvas  # noqa: E402


class PageRenderTests(unittest.TestCase):
    def test_all_pages_with_fixtures(self):
        for name, factory in (
            ("sunny", fixtures.sunny),
            ("rainy", fixtures.rainy),
            ("offline", fixtures.offline),
        ):
            for index in range(len(pages.PAGES)):
                with self.subTest(fixture=name, page=index + 1):
                    data = factory()
                    data["page"] = index
                    canvas = Canvas(400, 300)
                    pages.PAGES[index](canvas, data)
                    self.assertEqual(len(canvas.black), 15000)
                    self.assertEqual(len(canvas.red), 15000)
                    self.assertTrue(
                        any(value != 0xFF for value in canvas.black)
                        or any(value != 0xFF for value in canvas.red)
                    )

    def test_dashboard_without_time(self):
        data = fixtures.offline()
        data["now"] = None
        data["time_synced"] = False
        canvas = Canvas(400, 300)
        pages.render_dashboard(canvas, data)
        self.assertTrue(any(value != 0xFF for value in canvas.black))

    def test_long_dns_name_is_used(self):
        data = fixtures.offline()
        data["net"]["dns_name"] = "raspberry-pi-pico-w-01.iot"
        data["net"]["dns_ok"] = True
        data["net"]["hostname"] = "pico-dash"
        canvas = Canvas(400, 300)
        pages.render_network(canvas, data)
        self.assertTrue(any(value != 0xFF for value in canvas.black))

    def _assert_button_markers(self, canvas):
        from canvas import BLACK, RED

        for y in (181, 260):
            self.assertEqual(canvas.get_color(0, y), BLACK)
            self.assertEqual(canvas.get_color(11, y), BLACK)
            red_pixels = [
                (x, yy)
                for yy in range(y + 1, y + 15)
                for x in range(1, 11)
                if canvas.get_color(x, yy) == RED
            ]
            self.assertTrue(red_pixels, "no red glyph in marker at y=%d" % y)

    def test_button_markers_on_dashboard_and_other_pages(self):
        data = fixtures.sunny()
        data["page"] = 0
        canvas = Canvas(400, 300)
        pages.render_dashboard(canvas, data)
        self._assert_button_markers(canvas)

        data["page"] = 1
        canvas = Canvas(400, 300)
        pages.render_weather(canvas, data)
        self._assert_button_markers(canvas)


if __name__ == "__main__":
    unittest.main()
