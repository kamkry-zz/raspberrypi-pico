"""Pure-Python date, year-progress and formatting helpers.

``now`` arguments are ``time.localtime``/``time.gmtime``-style tuples:
(year, month, day, hour, minute, second, weekday, yearday).
"""

import time

from strings_pl import MONTHS, WEEKDAYS, WEEKDAYS_SHORT


def is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def days_in_year(year):
    return 366 if is_leap(year) else 365


def days_in_month(year, month):
    if month == 2:
        return 29 if is_leap(year) else 28
    if month in (4, 6, 9, 11):
        return 30
    return 31


def year_stats(now):
    """Return (percent_elapsed, yearday, days_left, days_total)."""
    year = now[0]
    total = days_in_year(year)
    yday = now[7]
    seconds = now[3] * 3600 + now[4] * 60 + now[5]
    fraction = seconds / 86400.0
    percent = (yday - 1 + fraction) / total * 100.0
    return percent, yday, total - yday, total


def format_date_pl(now):
    try:
        weekday = WEEKDAYS[now[6]]
        month = MONTHS[now[1] - 1]
    except (IndexError, TypeError):
        return "---"
    return "%s, %d %s %d" % (weekday, now[2], month, now[0])


def format_date_short_pl(now):
    try:
        weekday = WEEKDAYS_SHORT[now[6]]
    except (IndexError, TypeError):
        return "---"
    return "%s, %02d.%02d.%04d" % (weekday, now[2], now[1], now[0])


def weekday_short(weekday):
    return WEEKDAYS_SHORT[weekday % 7]


def format_clock(now):
    return "%02d:%02d" % (now[3], now[4])


def format_duration(seconds):
    seconds = int(seconds)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    if days:
        return "%dd %02d:%02d" % (days, hours, minutes)
    return "%02d:%02d" % (hours, minutes)


def format_pct(value):
    return ("%.1f" % value).replace(".", ",") + "%"


def format_temp(value):
    return ("%.1f" % value).replace(".", ",") + "°C"


def format_temp_short(value):
    return "%d°" % int(round(value))


def format_decimal(value):
    return ("%.1f" % value).replace(".", ",")


def format_mb(value):
    return ("%.1f" % value).replace(".", ",")


def epoch_from_utc(year, month, day, hour, minute, second):
    """Convert a UTC calendar time to a Unix epoch without mktime/timezone."""
    # Howard Hinnant's days_from_civil algorithm.
    y = year - (1 if month <= 2 else 0)
    era = (y if y >= 0 else y - 399) // 400
    yoe = y - era * 400
    mp = month + (-3 if month > 2 else 9)
    doy = (153 * mp + 2) // 5 + day - 1
    doe = yoe * 365 + yoe // 4 - yoe // 100 + doy
    days = era * 146097 + doe - 719468
    return days * 86400 + hour * 3600 + minute * 60 + second


MONTHS_EN = (
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
)


def parse_http_date(value):
    """Parse an RFC 1123 Date header into a UTC epoch."""
    try:
        text = value.decode() if isinstance(value, bytes) else value
        parts = text.split()
        day = int(parts[1])
        month = MONTHS_EN.index(parts[2]) + 1
        year = int(parts[3])
        hour, minute, second = (int(part) for part in parts[4].split(":"))
        return epoch_from_utc(year, month, day, hour, minute, second)
    except (ValueError, IndexError, TypeError):
        return None


def last_sunday(year, month):
    last = days_in_month(year, month)
    weekday = time.gmtime(epoch_from_utc(year, month, last, 0, 0, 0))[6]
    return last - ((weekday - 6) % 7)


def eu_offset(epoch_utc):
    """European DST fallback: +2 h between the last Sundays of March/October."""
    year = time.gmtime(int(epoch_utc))[0]
    start = epoch_from_utc(year, 3, last_sunday(year, 3), 1, 0, 0)
    end = epoch_from_utc(year, 10, last_sunday(year, 10), 1, 0, 0)
    return 7200 if start <= int(epoch_utc) < end else 3600


def local_tuple(epoch_utc, offset_seconds):
    return time.gmtime(int(epoch_utc) + int(offset_seconds))


def seconds_to_next_hour(now):
    remaining = 3600 - (now[4] * 60 + now[5])
    if remaining <= 0:
        remaining = 3600
    return remaining


def parse_iso_date(value):
    """Parse 'YYYY-MM-DD' or 'YYYY-MM-DDTHH:MM' into a tuple."""
    try:
        date_part = value[:10]
        year = int(date_part[0:4])
        month = int(date_part[5:7])
        day = int(date_part[8:10])
        hour = 0
        minute = 0
        if len(value) >= 16 and value[10] == "T":
            hour = int(value[11:13])
            minute = int(value[14:16])
        return (year, month, day, hour, minute)
    except (ValueError, IndexError):
        return None
