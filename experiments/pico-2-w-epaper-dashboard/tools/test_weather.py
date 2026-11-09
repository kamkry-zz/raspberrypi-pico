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


HUB_PAYLOAD = {
    "now": "2026-11-09T17:12:33",
    "location": {"name": "Łódź"},
    "current": {"time": "2026-11-09T17:00", "temp": 5.0, "feels": 1.1, "code": 0,
                "is_day": False, "wind": 11, "wind_dir": 142, "gust": 20,
                "humidity": 78, "pressure": 1023},
    "sun": {"sunrise": "06:50", "sunset": "16:00", "next_sunrise": "06:52"},
    "hourly": [{"hour": "%02d" % (18 + k), "temp": 4.0 - 0.3 * k, "code": 0,
                "is_day": False, "rain_prob": 5 * k, "wind": 11} for k in range(6)],
    "wind_blocks": [{"start": "16", "end": "20", "mean": 11, "dir": 142, "gust": 20,
                     "current": True}],
    "daily": [{"date": "2026-11-%02d" % (9 + k), "weekday": k, "code": 73, "tmax": 3.1,
               "tmin": 0.5, "rain_prob": 100, "rain_sum": 8.5} for k in range(5)],
    "warnings": [],
    "synop": {"hour_utc": 15, "temp": 5.1, "humidity": 75.7, "pressure": 1023.2},
    "stale": False,
}


class HubParseTests(unittest.TestCase):
    UTC_EPOCH = 1794240753  # 2026-11-09 16:12:33 UTC

    def test_maps_onto_the_dashboard_structure(self):
        result = weather.parse_hub(HUB_PAYLOAD, self.UTC_EPOCH)
        self.assertEqual(result["source"], "hub")
        self.assertEqual(result["current"]["temp"], 5.0)
        self.assertEqual(result["current"]["is_day"], 0)
        self.assertEqual(result["current"]["gust"], 20)
        self.assertEqual([d["label"] for d in result["daily"][:3]], ["Dziś", "Jutro", "śr."])
        self.assertEqual(result["daily"][1]["rain"], 100)
        self.assertEqual(result["daily"][1]["rain_sum"], 8.5)
        self.assertEqual(result["hourly"][0]["hour"], "18")
        self.assertEqual(result["hourly"][1]["rain"], 5)
        self.assertEqual(result["wind_blocks"][0]["mean"], 11)
        self.assertEqual(result["warnings"], [])
        self.assertEqual(result["synop"]["temp"], 5.1)

    def test_offset_from_local_time_and_http_date(self):
        result = weather.parse_hub(HUB_PAYLOAD, self.UTC_EPOCH)
        self.assertEqual(result["offset_s"], 3600)
        self.assertEqual(result["date_epoch"], self.UTC_EPOCH)

    def test_offset_falls_back_without_date(self):
        result = weather.parse_hub(HUB_PAYLOAD, None)
        self.assertEqual(result["offset_s"], weather.config.UTC_OFFSET_FALLBACK_S)

    def test_missing_fields(self):
        result = weather.parse_hub({}, None)
        self.assertEqual(result["daily"], [])
        self.assertEqual(result["hourly"], [])
        self.assertEqual(result["current"]["code"], 3)

    def test_open_meteo_fallback_has_no_imgw_data(self):
        result = weather.parse(payload())
        self.assertEqual(result["source"], "open-meteo")
        self.assertIsNone(result["warnings"])
        self.assertEqual(result["wind_blocks"], [])


if __name__ == "__main__":
    unittest.main()
