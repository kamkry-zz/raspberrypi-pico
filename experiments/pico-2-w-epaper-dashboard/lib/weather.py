"""Open-Meteo client and pure JSON parser for the dashboard."""

import json
import time

import config
import http_client
import timeutil as T
from strings_pl import TODAY, TOMORROW

_CACHE = None
_CACHE_TICKS = None
_CACHE_MS = 10 * 60 * 1000


def _url():
    return (
        "%s?latitude=%.4f&longitude=%.4f"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        "precipitation,weather_code,wind_speed_10m,is_day"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max"
        "&hourly=temperature_2m,precipitation_probability,weather_code"
        "&timezone=%s&forecast_days=%d&wind_speed_unit=kmh"
        % (
            config.WEATHER_URL,
            config.LATITUDE,
            config.LONGITUDE,
            config.TIMEZONE,
            config.WEATHER_DAYS,
        )
    )


def _number(value, default=0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse(payload):
    """Convert an Open-Meteo response into the dashboard weather dict."""
    current_raw = payload.get("current") or {}
    daily_raw = payload.get("daily") or {}
    hourly_raw = payload.get("hourly") or {}

    current = {
        "temp": _number(current_raw.get("temperature_2m")),
        "feels": _number(current_raw.get("apparent_temperature")),
        "humidity": int(_number(current_raw.get("relative_humidity_2m"))),
        "wind": int(round(_number(current_raw.get("wind_speed_10m")))),
        "precip": _number(current_raw.get("precipitation")),
        "code": int(_number(current_raw.get("weather_code"), 3)),
        "is_day": int(_number(current_raw.get("is_day"), 1)),
        "time": current_raw.get("time", ""),
    }

    daily = []
    times = daily_raw.get("time") or []
    codes = daily_raw.get("weather_code") or []
    highs = daily_raw.get("temperature_2m_max") or []
    lows = daily_raw.get("temperature_2m_min") or []
    rain = daily_raw.get("precipitation_probability_max") or []
    for index in range(min(config.WEATHER_DAYS, len(times))):
        date = times[index]
        try:
            weekday = time.gmtime(
                T.epoch_from_utc(
                    int(date[0:4]), int(date[5:7]), int(date[8:10]), 0, 0, 0
                )
            )[6]
        except (ValueError, IndexError):
            weekday = 0
        if index == 0:
            label = TODAY
        elif index == 1:
            label = TOMORROW
        else:
            label = T.weekday_short(weekday)
        daily.append(
            {
                "label": label,
                "date": date,
                "code": int(_number(codes[index] if index < len(codes) else 3, 3)),
                "tmax": int(round(_number(highs[index] if index < len(highs) else 0))),
                "tmin": int(round(_number(lows[index] if index < len(lows) else 0))),
                "rain": int(_number(rain[index] if index < len(rain) else 0)),
            }
        )

    hourly = []
    hourly_times = hourly_raw.get("time") or []
    hourly_temps = hourly_raw.get("temperature_2m") or []
    hourly_rain = hourly_raw.get("precipitation_probability") or []
    hourly_codes = hourly_raw.get("weather_code") or []
    start = 0
    current_time = current.get("time", "")
    if current_time:
        key = current_time[:13]
        for index, value in enumerate(hourly_times):
            if value[:13] >= key:
                start = index
                break
    for index in range(start, min(start + config.WEATHER_HOURS, len(hourly_times))):
        hourly.append(
            {
                "hour": hourly_times[index][11:13],
                "temp": _number(hourly_temps[index] if index < len(hourly_temps) else 0),
                "rain": int(_number(hourly_rain[index] if index < len(hourly_rain) else 0)),
                "code": int(_number(hourly_codes[index] if index < len(hourly_codes) else 3, 3)),
            }
        )

    return {
        "place": config.LOCATION_NAME,
        "offset_s": int(_number(payload.get("utc_offset_seconds"), config.UTC_OFFSET_FALLBACK_S)),
        "timezone": payload.get("timezone", config.TIMEZONE),
        "current": current,
        "daily": daily,
        "hourly": hourly,
        "fetched": 0,
        "date_epoch": None,
        "stale": False,
    }


def cached():
    return _CACHE


def fetch(force=True):
    """Fetch weather.  Returns None when there is no data and no cache."""
    global _CACHE, _CACHE_TICKS

    if (
        not force
        and _CACHE is not None
        and _CACHE_TICKS is not None
        and time.ticks_diff(time.ticks_ms(), _CACHE_TICKS) < _CACHE_MS
    ):
        return _CACHE

    try:
        status, headers, body = http_client.get(
            _url(), timeout=config.HTTP_TIMEOUT_S
        )
        if status != 200:
            raise OSError("HTTP %d" % status)
        result = parse(json.loads(body.decode()))
        result["fetched"] = int(time.time())
        result["date_epoch"] = T.parse_http_date(headers.get(b"date"))
        result["stale"] = False
        _CACHE = result
        _CACHE_TICKS = time.ticks_ms()
        print(
            "Weather: %.1f C, code %d, %d daily, %d hourly"
            % (
                result["current"]["temp"],
                result["current"]["code"],
                len(result["daily"]),
                len(result["hourly"]),
            )
        )
        return result
    except Exception as exc:
        print("Weather failed:", exc)
        if _CACHE is not None:
            _CACHE["stale"] = True
            return _CACHE
        return None
