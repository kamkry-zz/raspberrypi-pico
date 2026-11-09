"""Weather for the dashboard: pogoda-hub first, Open-Meteo as the fallback.

Both sources are converted to one dict; the pogoda-hub payload adds the sun
path, 4-hour wind blocks, IMGW warnings and the IMGW synop.
"""

import json
import time

import config
import http_client
import store
import telemetry
import timeutil as T
from strings_pl import TODAY, TOMORROW

_CACHE = None
_CACHE_TICKS = None
_CACHE_MS = 10 * 60 * 1000


def _url():
    return (
        "%s?latitude=%.4f&longitude=%.4f"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        "precipitation,weather_code,wind_speed_10m,wind_direction_10m,wind_gusts_10m,is_day"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,"
        "precipitation_probability_max,precipitation_sum,sunrise,sunset"
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
        "wind_dir": current_raw.get("wind_direction_10m"),
        "gust": _round_or_none(current_raw.get("wind_gusts_10m")),
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

    sunrise = (daily_raw.get("sunrise") or [""])[0]
    sunset = (daily_raw.get("sunset") or [""])[0]
    return {
        "source": "open-meteo",
        "sun": {"sunrise": sunrise[11:16] or None, "sunset": sunset[11:16] or None},
        "wind_blocks": [],
        "warnings": None,
        "synop": None,
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


def _round_or_none(value):
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _day_label(index, weekday):
    if index == 0:
        return TODAY
    if index == 1:
        return TOMORROW
    return T.weekday_short(weekday or 0)


def _offset_from_local(local_iso, utc_epoch):
    """UTC offset (s, 15-min steps) from the hub's local ISO time and the HTTP Date."""
    try:
        local = T.epoch_from_utc(
            int(local_iso[0:4]), int(local_iso[5:7]), int(local_iso[8:10]),
            int(local_iso[11:13]), int(local_iso[14:16]), int(local_iso[17:19] or 0),
        )
    except (TypeError, ValueError, IndexError):
        return None
    if not utc_epoch:
        return None
    return int(round((local - utc_epoch) / 900.0)) * 900


def parse_hub(payload, utc_epoch=None):
    """Convert a pogoda-hub /v1/weather payload into the dashboard weather dict."""
    cur = payload.get("current") or {}
    current = {
        "temp": _number(cur.get("temp")),
        "feels": _number(cur.get("feels")),
        "humidity": int(_number(cur.get("humidity"))),
        "wind": int(_number(cur.get("wind"))),
        "precip": 0.0,
        "code": int(_number(cur.get("code"), 3)),
        "is_day": 1 if cur.get("is_day") else 0,
        "time": cur.get("time") or "",
        "wind_dir": cur.get("wind_dir"),
        "gust": cur.get("gust"),
        "pressure": cur.get("pressure"),
    }
    daily = []
    for index, day in enumerate((payload.get("daily") or [])[: config.WEATHER_DAYS]):
        daily.append(
            {
                "label": _day_label(index, day.get("weekday")),
                "date": day.get("date") or "",
                "weekday": day.get("weekday"),
                "code": int(_number(day.get("code"), 3)),
                "tmax": int(round(_number(day.get("tmax")))),
                "tmin": int(round(_number(day.get("tmin")))),
                "rain": int(_number(day.get("rain_prob"))),
                "rain_sum": _number(day.get("rain_sum")),
            }
        )
    hourly = []
    for hour in (payload.get("hourly") or [])[: config.WEATHER_HOURS]:
        hourly.append(
            {
                "hour": hour.get("hour") or "",
                "temp": _number(hour.get("temp")),
                "rain": int(_number(hour.get("rain_prob"))),
                "code": int(_number(hour.get("code"), 3)),
                "is_day": 1 if hour.get("is_day") else 0,
                "wind": hour.get("wind"),
            }
        )
    offset = _offset_from_local(payload.get("now"), utc_epoch)
    return {
        "source": "hub",
        "place": (payload.get("location") or {}).get("name") or config.LOCATION_NAME,
        "offset_s": offset if offset is not None else config.UTC_OFFSET_FALLBACK_S,
        "timezone": config.TIMEZONE,
        "current": current,
        "daily": daily,
        "hourly": hourly,
        "sun": payload.get("sun") or {},
        "wind_blocks": payload.get("wind_blocks") or [],
        "warnings": payload.get("warnings") or [],
        "synop": payload.get("synop"),
        "fetched": 0,
        "date_epoch": utc_epoch,
        "stale": bool(payload.get("stale")),
    }


def _fetch_hub():
    status, headers, body = http_client.get(config.HUB_WEATHER_URL, timeout=config.HTTP_TIMEOUT_S)
    if status != 200:
        raise OSError("hub HTTP %d" % status)
    date_epoch = T.parse_http_date(headers.get(b"date"))
    return parse_hub(json.loads(body.decode()), date_epoch), date_epoch


def _fetch_open_meteo():
    status, headers, body = http_client.get(_url(), timeout=config.HTTP_TIMEOUT_S)
    if status != 200:
        raise OSError("HTTP %d" % status)
    result = parse(json.loads(body.decode()))
    result["date_epoch"] = T.parse_http_date(headers.get(b"date"))
    return result, result["date_epoch"]


def cached():
    return _CACHE


def load_persisted():
    """Load the last good weather from flash (marked stale) at boot."""
    global _CACHE
    value = store.load(config.WEATHER_CACHE_FILE)
    if isinstance(value, dict) and value.get("current") and value.get("daily") is not None:
        value["stale"] = True
        _CACHE = value
        print("Weather: loaded cached data from", value.get("fetched"))
        return value
    return None


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
        try:
            result, date_epoch = _fetch_hub()
        except Exception as exc:
            telemetry.log("pogoda-hub failed (%r); using Open-Meteo" % (exc,), "WARN")
            telemetry.inc("dashboard.weather.fetches", {"result": "hub_fail"})
            result, date_epoch = _fetch_open_meteo()
        # time.time() is meaningless before NTP; prefer the server's Date.
        result["fetched"] = date_epoch or int(time.time())
        _CACHE = result
        _CACHE_TICKS = time.ticks_ms()
        telemetry.inc("dashboard.weather.fetches", {"result": "ok"})
        store.save(config.WEATHER_CACHE_FILE, result)
        print(
            "Weather (%s): %.1f C, code %d, %d daily, %d hourly"
            % (
                result["source"],
                result["current"]["temp"],
                result["current"]["code"],
                len(result["daily"]),
                len(result["hourly"]),
            )
        )
        return result
    except Exception as exc:
        telemetry.inc("dashboard.weather.fetches", {"result": "fail"})
        telemetry.log("Weather fetch failed: %r" % (exc,), "WARN")
        if _CACHE is not None:
            _CACHE["stale"] = True
            return _CACHE
        return None
