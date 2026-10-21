import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))

import weather  # noqa: E402


def payload():
    hours = ["2026-10-21T%02d:00" % hour for hour in range(5, 18)]
    return {
        "current": {
            "time": "2026-10-21T06:45",
            "temperature_2m": 10.4,
            "relative_humidity_2m": 89,
            "apparent_temperature": 7.1,
            "precipitation": 0.0,
            "weather_code": 3,
            "wind_speed_10m": 20.0,
            "is_day": 0,
        },
        "daily": {
            "time": ["2026-10-21", "2026-10-22", "2026-10-23"],
            "weather_code": [3, 63, 3],
            "temperature_2m_max": [18, 14, 12],
            "temperature_2m_min": [10, 8, 7],
            "precipitation_probability_max": [0, 100, 58],
        },
        "hourly": {
            "time": hours,
            "temperature_2m": [10.0 + index * 0.5 for index in range(len(hours))],
            "precipitation_probability": [index * 5 for index in range(len(hours))],
            "weather_code": [3 for _ in hours],
        },
        "utc_offset_seconds": 7200,
        "timezone": "Europe/Warsaw",
    }


class WeatherParseTests(unittest.TestCase):
    def test_current_and_daily(self):
        result = weather.parse(payload())
        self.assertEqual(result["place"], "Łódź")
        self.assertEqual(result["offset_s"], 7200)
        self.assertEqual(result["current"]["temp"], 10.4)
        self.assertEqual(result["current"]["code"], 3)
        self.assertEqual(len(result["daily"]), 3)
        self.assertEqual([day["label"] for day in result["daily"]], ["Dziś", "Jutro", "pt."])
        self.assertEqual(result["daily"][1]["rain"], 100)

    def test_hourly_starts_at_current_hour(self):
        result = weather.parse(payload())
        self.assertEqual(len(result["hourly"]), 12)
        self.assertEqual(result["hourly"][0]["hour"], "06")
        self.assertEqual(result["hourly"][-1]["hour"], "17")

    def test_missing_fields(self):
        result = weather.parse({})
        self.assertEqual(result["current"]["temp"], 0.0)
        self.assertEqual(result["daily"], [])
        self.assertEqual(result["hourly"], [])
        self.assertEqual(result["offset_s"], 3600)


if __name__ == "__main__":
    unittest.main()
