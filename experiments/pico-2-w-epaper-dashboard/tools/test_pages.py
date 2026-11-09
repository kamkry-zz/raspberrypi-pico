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


    def test_new_weather_page_variants(self):
        from canvas import RED

        for name in ("hub", "hub_day", "hub_warning", "hub_stale"):
            data = getattr(fixtures, name)()
            data["page"] = 1
            canvas = Canvas(400, 300)
            pages.render_weather(canvas, data)
            self._assert_button_markers(canvas)
            self.assertTrue(any(value != 0xFF for value in canvas.black), name)
        data = fixtures.hub_warning()
        canvas = Canvas(400, 300)
        pages.render_weather(canvas, data)
        self.assertEqual(canvas.get_color(200, 275), RED)  # warning band

    def test_new_weather_page_without_hub_extras(self):
        data = fixtures.sunny()  # Open-Meteo shaped data, no wind blocks/sun
        canvas = Canvas(400, 300)
        pages.render_weather(canvas, data)
        self.assertTrue(any(value != 0xFF for value in canvas.black))

    def test_map_page_blits_cached_planes(self):
        import os
        import tempfile

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        import config
        from canvas import BLACK, RED

        old = config.MAP_CACHE_FILE
        try:
            config.MAP_CACHE_FILE = os.path.join(tempfile.mkdtemp(), "map.bin")
            data = fixtures.hub_day()
            canvas = Canvas(400, 300)
            pages.render_map(canvas, data)
            self.assertTrue(any(canvas.get_color(x, y) == RED
                                for x in range(150, 250) for y in range(120, 139)))  # "Brak mapy"
            fixtures.make_map_bin(config.MAP_CACHE_FILE)
            canvas = Canvas(400, 300)
            pages.render_map(canvas, data)
            # synthetic isobar at map row 125 (+22 header) at x=0
            self.assertEqual(canvas.get_color(0, 22 + 125), BLACK)
            # synthetic front at row 60 + 20*cos(0) = 80 at x=0
            self.assertEqual(canvas.get_color(0, 22 + 80), RED)
            self._assert_button_markers(canvas)
        finally:
            config.MAP_CACHE_FILE = old

    def test_pogoda_is_the_default_page(self):
        # app.py starts at state["page"] = 0: the boot frame is the weather page.
        self.assertIs(pages.PAGES[0], pages.render_weather)
        self.assertIs(pages.PAGES[1], pages.render_map)
        self.assertEqual(len(pages.PAGES), pages.PAGE_COUNT)

    def test_big_temp_fits_before_the_sun_arc(self):
        for value in (5.0, 9.94, 9.96, -3.4, -12.5, 25.0, -28.0, None):
            self.assertLessEqual(66 + len(pages.big_temp(value)) * 24, 174, value)


if __name__ == "__main__":
    unittest.main()
