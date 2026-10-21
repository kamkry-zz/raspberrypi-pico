"""Deterministic data fixtures for host previews and layout tests."""

import timeutil as T


def _now(hour=6, minute=50, month=10, day=21, year=2026):
    # Local time in Europe/Warsaw is UTC+2 in October.
    epoch = T.epoch_from_utc(year, month, day, hour - 2, minute, 0)
    return T.local_tuple(epoch, 7200), epoch


def _base(hour=6, minute=50):
    now, epoch = _now(hour, minute)
    weather = {
        "place": "Łódź",
        "offset_s": 7200,
        "fetched": epoch,
        "date_epoch": epoch + 1,
        "stale": False,
        "current": {
            "temp": 10.4,
            "feels": 7.1,
            "humidity": 89,
            "wind": 20,
            "precip": 0.0,
            "code": 3,
            "is_day": 0,
            "time": "2026-10-21T06:45",
        },
        "daily": [
            {"label": "Dziś", "code": 3, "tmax": 18, "tmin": 10, "rain": 0},
            {"label": "Jutro", "code": 63, "tmax": 14, "tmin": 8, "rain": 100},
            {"label": "pt.", "code": 3, "tmax": 12, "tmin": 7, "rain": 58},
        ],
        "hourly": [
            {"hour": "%02d" % ((hour + index) % 24), "temp": temp, "rain": rain, "code": code}
            for index, (temp, rain, code) in enumerate(
                (
                    (10.3, 0, 2),
                    (10.4, 0, 3),
                    (10.5, 0, 3),
                    (11.0, 5, 3),
                    (12.0, 10, 61),
                    (13.0, 15, 61),
                    (14.0, 20, 61),
                    (15.0, 30, 61),
                    (15.0, 40, 3),
                    (14.0, 35, 3),
                    (13.0, 25, 3),
                    (12.0, 15, 3),
                )
            )
        ],
    }
    return {
        "now": now,
        "now_epoch": epoch + 1,
        "time_synced": True,
        "offline": False,
        "wifi_status": "połączono",
        "page": 0,
        "pages": 5,
        "weather": weather,
        "net": {
            "hostname": "pico-dash",
            "dns_name": "raspberry-pi-pico-w-01.iot",
            "dns_source": "PTR",
            "dns_ok": True,
            "ip": "192.168.4.51",
            "netmask": "255.255.255.0",
            "gateway": "192.168.4.1",
            "dns_server": "192.168.4.1",
            "ssid": "krys_dom_IoT",
            "bssid": "—",
            "rssi": -51,
            "channel": 6,
            "mac": "28:cd:c1:0d:34:f0",
            "status": "połączono",
            "http_ms": 1240,
        },
        "metrics": {
            "uptime_s": 3 * 86400 + 4 * 3600 + 12 * 60,
            "heap_used": 142 * 1024,
            "heap_total": 222 * 1024,
            "flash_used": 1.8 * 1048576,
            "flash_total": 2.0 * 1048576,
            "temp_c": 38.2,
            "active_pct": 0.3,
            "transfer_ms": 88,
            "busy_ms": 23123,
            "total_ms": 23211,
            "refresh_count": 42,
            "reset_cause": "PWRON",
            "firmware": "1.23.0",
        },
    }


def sunny():
    return _base(6, 50)


def rainy():
    data = _base(20, 45)
    data["weather"]["current"] = {
        "temp": 9.6,
        "feels": 7.8,
        "humidity": 88,
        "wind": 18,
        "precip": 1.2,
        "code": 63,
        "is_day": 0,
        "time": "2026-10-21T20:45",
    }
    data["weather"]["stale"] = False
    return data


def offline():
    data = _base(20, 45)
    data["weather"] = None
    data["offline"] = True
    data["wifi_status"] = "brak połączenia"
    data["net"]["rssi"] = None
    data["net"]["ip"] = "—"
    data["net"]["dns_ok"] = False
    data["net"]["dns_name"] = None
    return data


def stale():
    data = _base(20, 45)
    data["weather"]["stale"] = True
    data["offline"] = True
    return data
