import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

import timeutil as T  # noqa: E402


class YearStatsTests(unittest.TestCase):
    def test_start_of_year(self):
        now = (2026, 1, 1, 0, 0, 0, 3, 1)
        pct, yday, left, total = T.year_stats(now)
        self.assertAlmostEqual(pct, 0.0)
        self.assertEqual((yday, left, total), (1, 364, 365))

    def test_end_of_year(self):
        now = (2026, 12, 31, 23, 59, 59, 3, 365)
        pct, yday, left, total = T.year_stats(now)
        self.assertGreater(pct, 99.99)
        self.assertLess(pct, 100.0)
        self.assertEqual((yday, left, total), (365, 0, 365))

    def test_leap_year(self):
        now = (2024, 12, 31, 12, 0, 0, 1, 366)
        pct, yday, left, total = T.year_stats(now)
        self.assertEqual((yday, left, total), (366, 0, 366))
        self.assertTrue(T.is_leap(2024))
        self.assertFalse(T.is_leap(2026))
        self.assertFalse(T.is_leap(2100))
        self.assertTrue(T.is_leap(2000))


class DateAndOffsetTests(unittest.TestCase):
    def test_http_date(self):
        epoch = T.parse_http_date(b"Tue, 20 Oct 2026 12:00:00 GMT")
        self.assertEqual(epoch, T.epoch_from_utc(2026, 10, 20, 12, 0, 0))

    def test_polish_date(self):
        epoch = T.epoch_from_utc(2026, 10, 21, 4, 50, 0)
        now = T.local_tuple(epoch, 7200)
        self.assertEqual(T.format_date_pl(now), "środa, 21 października 2026")
        self.assertEqual(T.format_clock(now), "06:50")

    def test_eu_dst_boundaries(self):
        self.assertEqual(T.eu_offset(T.epoch_from_utc(2026, 3, 29, 0, 59, 0)), 3600)
        self.assertEqual(T.eu_offset(T.epoch_from_utc(2026, 3, 29, 1, 0, 0)), 7200)
        self.assertEqual(T.eu_offset(T.epoch_from_utc(2026, 10, 25, 0, 59, 0)), 7200)
        self.assertEqual(T.eu_offset(T.epoch_from_utc(2026, 10, 25, 1, 0, 0)), 3600)

    def test_next_hour(self):
        now = (2026, 10, 21, 6, 50, 0, 2, 294)
        self.assertEqual(T.seconds_to_next_hour(now), 600)
        now = (2026, 10, 21, 6, 0, 0, 2, 294)
        self.assertEqual(T.seconds_to_next_hour(now), 3600)

    def test_formatting(self):
        self.assertEqual(T.format_pct(80.36), "80,4%")
        self.assertEqual(T.format_temp(10.44), "10,4°C")
        self.assertEqual(T.format_duration(3 * 86400 + 4 * 3600 + 12 * 60), "3d 04:12")


if __name__ == "__main__":
    unittest.main()
