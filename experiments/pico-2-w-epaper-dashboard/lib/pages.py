"""Dashboard pages rendered with the portable canvas."""

import math
import time

import icons
import strings_pl as S
import timeutil as T
from canvas import BLACK, RED, WHITE
from font_large import FONT as LARGE
from font_medium import FONT as MEDIUM
from font_small import FONT as SMALL
from font_xlarge import FONT as XLARGE

PAGE_COUNT = 6


def button_marker(canvas, y, glyph):
    """Small key hint in the 12 px left margin.

    The box is white with a 1 px black outline; the glyph is red.  The right
    border sits at x=11 so the dashboard's year-grid border (x=11) can touch
    the previous-page marker, and the stats labels start at x=12.
    """
    canvas.fill_rect(1, y + 1, 10, 14, WHITE)
    canvas.rect(0, y, 12, 16, BLACK)
    canvas.text(2, y, glyph, RED, SMALL)


def button_markers(canvas):
    # Fixed physical key heights: KEY0/GP15 at the bottom of the year grid,
    # KEY1/GP17 at the MAC row.  Drawn on every page via header().
    button_marker(canvas, 181, "<")
    button_marker(canvas, 260, ">")


def header(canvas, title, now):
    canvas.fill_rect(0, 0, 400, 30, BLACK)
    canvas.fill_rect(0, 27, 400, 3, RED)
    canvas.text(10, 5, title, WHITE, MEDIUM)
    if now:
        canvas.text(390, 6, T.format_date_pl(now), WHITE, SMALL, anchor="right")
    button_markers(canvas)


def footer(canvas, data, right="Open-Meteo", compact=False):
    canvas.fill_rect(0, 281, 400, 1, BLACK)
    now = data.get("now")
    metrics = data.get("metrics") or {}
    page = data.get("page", 0) + 1
    pages = data.get("pages", PAGE_COUNT)
    total_s = metrics.get("total_ms", 0) / 1000.0
    if data.get("time_synced") and now:
        clock = T.format_clock(now)
        next_hour = (now[3] + 1) % 24
        if compact:
            left = "%s %s · %s %02d:00 · %d/%d" % (S.UPDATED, clock, S.NEXT, next_hour, page, pages)
        else:
            left = "%s %s · %s s · %s %02d:00 · %d/%d" % (
                S.UPDATED,
                clock,
                T.format_decimal(total_s),
                S.NEXT,
                next_hour,
                page,
                pages,
            )
    else:
        left = "%s — · %s s · %d/%d" % (
            S.UPDATED,
            T.format_decimal(total_s),
            page,
            pages,
        )
    canvas.text(10, 283, left, BLACK, SMALL)
    canvas.text(390, 283, right, BLACK, SMALL, anchor="right")


def year_grid(canvas, now, x, y):
    year, month, day = now[0], now[1], now[2]
    for m in range(1, 13):
        limit = T.days_in_month(year, m)
        for d in range(1, 32):
            if d > limit:
                continue
            cx = x + (m - 1) * 5
            cy = y + (d - 1) * 5
            if (m, d) == (month, day):
                canvas.fill_rect(cx, cy, 4, 4, RED)
            elif (m, d) < (month, day):
                canvas.fill_rect(cx, cy, 4, 4, BLACK)
            # Future days stay white; the surrounding border shows the grid.
    canvas.rect(x - 1, y - 1, 12 * 5, 31 * 5, BLACK)
    canvas.fill_rect(x + (month - 1) * 5, y - 3, 4, 2, RED)


def stat(canvas, x, y, label, value, label_width=46, colour=BLACK):
    canvas.text(x, y, label, BLACK, SMALL)
    canvas.text(x + label_width, y, value, colour, SMALL)


def draw_stats(canvas, data):
    net = data.get("net") or {}
    metrics = data.get("metrics") or {}
    y = 200

    ssid = net.get("ssid") or "—"
    rssi = net.get("rssi")
    wifi = ssid if rssi is None else "%s %d" % (ssid, rssi)
    host_value = net.get("hostname") or net.get("dns_name") or "—"
    left_rows = (
        (S.HOST, host_value),
        (S.DNS, net.get("dns_source") or "—"),
        (S.IP, net.get("ip") or "—"),
        (S.WIFI, wifi),
        (S.MAC, net.get("mac") or "—"),
    )
    for index, (label, value) in enumerate(left_rows):
        stat(canvas, 12, y + index * 15, label, value, label_width=32)

    if net.get("dns_name"):
        check_x = 44 + len(host_value) * SMALL.advance + 4
        if check_x < 196:
            if net.get("dns_ok"):
                icons.check(canvas, check_x, y + 2)
            else:
                icons.cross(canvas, check_x, y + 2)

    right_rows = (
        (S.UPTIME, T.format_duration(metrics.get("uptime_s", 0))),
        (
            S.RAM,
            "%d/%d KB"
            % (metrics.get("heap_used", 0) // 1024, metrics.get("heap_total", 0) // 1024),
        ),
        (
            S.FLASH,
            "%s/%s MB"
            % (
                T.format_mb(metrics.get("flash_used", 0) / 1048576.0),
                T.format_mb(metrics.get("flash_total", 0) / 1048576.0),
            ),
        ),
        (S.TEMP, T.format_temp(metrics.get("temp_c", 0))),
        (S.ACTIVE, T.format_pct(metrics.get("active_pct", 0))),
    )
    for index, (label, value) in enumerate(right_rows):
        stat(canvas, 210, y + index * 15, label, value, label_width=56)


def draw_weather_summary(canvas, data, x, y):
    weather = data.get("weather")
    place = (weather or {}).get("place", "Łódź")
    canvas.text(x, y + 4, "%s · %s" % (S.WEATHER, place.upper()), BLACK, SMALL)
    canvas.fill_rect(x, y + 19, 178, 1, RED)

    if not weather:
        canvas.text(x + 2, y + 32, S.NO_DATA, RED, SMALL)
        canvas.text(x + 2, y + 50, S.OFFLINE, RED, SMALL)
        return

    current = weather.get("current") or {}
    colour = RED if weather.get("stale") else BLACK
    if weather.get("stale"):
        canvas.text(x + 176, y + 4, S.STALE, colour, SMALL, anchor="right")

    icons.weather_icon(
        canvas,
        x + 2,
        y + 24,
        36,
        current.get("code", 3),
        current.get("is_day", 1),
    )
    canvas.text(x + 44, y + 22, T.format_temp(current.get("temp", 0)), BLACK, LARGE)
    canvas.text(
        x + 2,
        y + 64,
        S.WMO_SHORT.get(current.get("code", 3), "?"),
        BLACK,
        SMALL,
    )

    daily = weather.get("daily") or []
    for index, day in enumerate(daily[:3]):
        yy = y + 86 + index * 22
        canvas.text(x + 2, yy, day.get("label", ""), BLACK, SMALL)
        icons.weather_icon(canvas, x + 40, yy - 2, 18, day.get("code", 3), True)
        canvas.text(
            x + 66,
            yy,
            "%d/%d" % (day.get("tmax", 0), day.get("tmin", 0)),
            BLACK,
            SMALL,
        )
        rain = day.get("rain", 0)
        canvas.text(
            x + 176,
            yy,
            "%d%%" % rain,
            RED if rain >= 50 else BLACK,
            SMALL,
            anchor="right",
        )


def render_dashboard(canvas, data):
    canvas.clear(WHITE)
    now = data.get("now")
    header(canvas, S.PAGE_TITLES[0], now)

    if now:
        year_grid(canvas, now, 12, 42)
        pct, yday, left, total = T.year_stats(now)
        pct_text = T.format_pct(pct)
        canvas.text(82, 42, "%s %d" % (S.YEAR, now[0]), BLACK, SMALL)
        canvas.text(82, 58, pct_text[:-1], BLACK, LARGE)
        canvas.text(82 + (len(pct_text) - 1) * LARGE.advance, 58, "%", RED, LARGE)
        canvas.text(82, 96, "%s %d %s %d" % (S.DAY, yday, S.OF, total), BLACK, SMALL)
        canvas.text(82, 112, "%s %d %s" % (S.LEFT, left, S.DAYS), BLACK, SMALL)
        if T.is_leap(now[0]):
            canvas.text(82, 128, S.LEAP, BLACK, SMALL)

    canvas.fill_rect(205, 36, 2, 160, RED)
    draw_weather_summary(canvas, data, 210, 36)
    canvas.fill_rect(0, 197, 400, 1, BLACK)
    draw_stats(canvas, data)
    footer(canvas, data)


# ------------------------------------------------------------ weather page
# Layout: design canvas "e-Paper · Pogoda" (2026-11-09), device pixels.
ARC_CX = 221
ARC_CY = 88
ARC_R = 40


def header_slim(canvas, title, now):
    canvas.fill_rect(0, 0, 400, 20, BLACK)
    canvas.fill_rect(0, 20, 400, 2, RED)
    canvas.text(8, 2, title, WHITE, SMALL)
    if now:
        right = "%s · %s" % (T.format_date_pl(now), T.format_clock(now))
        if (len(title) + len(right) + 2) * SMALL.advance > 384:
            right = "%s · %s" % (T.format_date_short_pl(now), T.format_clock(now))
        canvas.text(392, 2, right, WHITE, SMALL, anchor="right")
    # The key markers are drawn last by each page (icons may reach x < 12).


def _minutes(hhmm):
    try:
        return int(hhmm[0:2]) * 60 + int(hhmm[3:5])
    except (TypeError, ValueError, IndexError):
        return None


def _deg(value):
    try:
        return "%d°" % int(math.floor(float(value) + 0.5))
    except (TypeError, ValueError):
        return "--"


def big_temp(value):
    """XL temperature: one decimal only for 0 <= t < 9.95 (width budget 66..174)."""
    if value is None:
        return "--"
    if 0 <= value < 9.95:
        return ("%.1f°" % value).replace(".", ",")
    return _deg(value)


def _arc_point(fraction, radius=ARC_R):
    angle = math.pi * (1 - fraction)
    return (
        int(round(ARC_CX + radius * math.cos(angle))),
        int(round(ARC_CY - radius * math.sin(angle))),
    )


def draw_sun_arc(canvas, sun, now):
    canvas.hline(174, ARC_CY, 95, BLACK)
    canvas.vline(ARC_CX, ARC_CY - ARC_R - 2, 5, BLACK)
    for step in range(0, 181, 3):
        x, y = _arc_point(step / 180.0)
        canvas.pixel(x, y, BLACK)
    rise = _minutes((sun or {}).get("sunrise"))
    set_ = _minutes((sun or {}).get("sunset"))
    current = now[3] * 60 + now[4] if now else None
    title = None
    if rise is not None and set_ is not None and current is not None and set_ > rise:
        if rise <= current <= set_:
            progress = (current - rise) / (set_ - rise)
            steps = int(progress * 180)
            for step in range(steps + 1):
                for radius in (ARC_R - 1, ARC_R, ARC_R + 1):
                    x, y = _arc_point(step / 180.0, radius)
                    canvas.pixel(x, y, RED)
            x, y = _arc_point(progress)
            canvas.circle(x, y, 6, WHITE, fill=True)
            canvas.circle(x, y, 4, RED, fill=True)
            title = "%s %d%%" % (S.DAY_PROGRESS, int(progress * 100 + 0.5))
        else:
            for step in range(181):
                x, y = _arc_point(step / 180.0)
                canvas.pixel(x, y, BLACK)
            icons.moon(canvas, ARC_CX, ARC_CY + 10, 5)
            nxt = _minutes((sun or {}).get("next_sunrise")) or rise
            wait = nxt - current if current < nxt else 1440 - current + nxt
            title = "%s %d:%02d" % (S.SUNRISE_IN, wait // 60, wait % 60)
    if title:
        # x 218: "wschód za 13:40" (105 px) must clear the column divider at x 272
        canvas.text(ARC_CX - 3, 26, title, BLACK, SMALL, anchor="center")
    canvas.text(176, 92, (sun or {}).get("sunrise") or "--:--", BLACK, SMALL)
    canvas.text(266, 92, (sun or {}).get("sunset") or "--:--", BLACK, SMALL, anchor="right")


def draw_wind_arrow(canvas, cx, cy, from_deg, colour=BLACK):
    """Arrow pointing where the wind blows to (meteorological 'from' + 180)."""
    if from_deg is None:
        return
    angle = math.radians((float(from_deg) + 180) % 360)
    dx, dy = math.sin(angle), -math.cos(angle)
    tip = (int(round(cx + 6 * dx)), int(round(cy + 6 * dy)))
    tail = (int(round(cx - 6 * dx)), int(round(cy - 6 * dy)))
    canvas.line(tail[0], tail[1], tip[0], tip[1], colour)
    canvas.line(tail[0] + 1, tail[1], tip[0] + 1, tip[1], colour)
    for side in (2.5, -2.5):
        wing = angle + math.pi + side * 0.25
        canvas.line(tip[0], tip[1], int(round(tip[0] + 4 * math.sin(wing))), int(round(tip[1] - 4 * math.cos(wing))), colour)


def draw_wind_blocks(canvas, blocks):
    gusts = [b.get("gust") for b in blocks if b.get("gust") is not None]
    caption = S.WIND_CAPTION
    if gusts:
        caption += " · %s %d" % (S.GUSTS_UP_TO, max(gusts))
    canvas.text(16, 105, caption, BLACK, SMALL)
    for index, block in enumerate(blocks[:6]):
        x0 = 8 + 43 * index
        cx = x0 + 21
        label = "%s-%s" % (block.get("start", "--"), block.get("end", "--"))
        first = bool(block.get("current"))
        canvas.text(cx, 120, label, RED if first else BLACK, SMALL, anchor="center")
        if first:
            canvas.fill_rect(x0, 136, 41, 2, RED)
        mean = block.get("mean")
        canvas.text(cx + 2, 135, "--" if mean is None else str(mean), BLACK, MEDIUM, anchor="right")
        draw_wind_arrow(canvas, cx + 12, 144, block.get("dir"))


def draw_hours(canvas, hourly):
    for index, hour in enumerate((hourly or [])[:8]):
        cx = 24 + 33 * index
        canvas.text(cx, 158, hour.get("hour", ""), BLACK, SMALL, anchor="center")
        icons.weather_icon(canvas, cx - 9, 175, 18, hour.get("code", 3), hour.get("is_day", 1))
        canvas.text(cx, 194, _deg(hour.get("temp")), BLACK, MEDIUM, anchor="center")
        height = 18 * min(100, max(0, hour.get("rain", 0))) // 100
        if height:
            canvas.fill_rect(cx - 3, 236 - height, 6, height, RED)
    canvas.hline(14, 237, 252, BLACK)


def _warning_lines(warning):
    level = warning.get("level")
    event = (warning.get("event") or "").lower()
    line1 = "%s %s° · %s" % (S.WARNING_SHORT, level if level is not None else "?", event)
    start = warning.get("from") or ""
    end = warning.get("to") or ""
    line2 = "%s.%s %s–%s" % (start[8:10], start[5:7], start[11:16], end[11:16])
    if warning.get("probability") is not None:
        line2 += " · %d%%" % warning["probability"]
    return line1[:32], line2[:32]


def draw_info_band(canvas, weather):
    if weather.get("stale"):
        fetched = weather.get("fetched")
        when = "--:--"
        if fetched:
            local = T.local_tuple(fetched, weather.get("offset_s") or 0)
            when = "%02d:%02d" % (local[3], local[4])
        canvas.text(16, 246, "%s %s" % (S.STALE, when), RED, SMALL)
    warnings = weather.get("warnings")
    if warnings and not weather.get("stale"):
        canvas.fill_rect(14, 242, 252, 36, RED)
        for row in range(16):
            half = row * 9 // 16
            canvas.hline(26 - half, 246 + row, 2 * half + 1, WHITE)
        canvas.fill_rect(25, 251, 2, 6, RED)
        canvas.fill_rect(25, 259, 2, 2, RED)
        line1, line2 = _warning_lines(warnings[0])
        canvas.text(40, 244, line1, WHITE, SMALL)
        canvas.text(40, 260, line2, WHITE, SMALL)
        return
    if not weather.get("stale"):
        canvas.text(16, 246, S.NO_IMGW if warnings is None else S.NO_WARNINGS, BLACK, SMALL)
    synop = weather.get("synop")
    if synop and synop.get("temp") is not None:
        parts = ["%s %02d UTC %s°" % (S.SYNOP, synop.get("hour_utc") or 0, T.format_decimal(synop["temp"]))]
        if synop.get("humidity") is not None:
            parts.append("%d%%" % int(synop["humidity"] + 0.5))
        if synop.get("pressure") is not None:
            parts.append("%d hPa" % int(synop["pressure"] + 0.5))
        canvas.text(16, 262, " · ".join(parts), BLACK, SMALL)


def draw_days(canvas, daily):
    canvas.fill_rect(272, 26, 2, 250, RED)
    for index, day in enumerate((daily or [])[1:5]):
        y0 = 24 + 64 * index
        if index:
            for x in range(278, 396, 3):
                canvas.pixel(x, y0, BLACK)
        weekday = day.get("weekday")
        name = T.weekday_short(weekday) if weekday is not None else day.get("label", "")
        canvas.text(280, y0 + 2, name, BLACK, MEDIUM)
        date = day.get("date") or ""
        if len(date) >= 10:
            canvas.text(394, y0 + 4, "%s.%s" % (date[8:10], date[5:7]), BLACK, SMALL, anchor="right")
        icons.weather_icon(canvas, 280, y0 + 24, 26, day.get("code", 3), True)
        canvas.text(312, y0 + 23, "%d°/%d°" % (day.get("tmax", 0), day.get("tmin", 0)), BLACK, MEDIUM)
        rain = day.get("rain", 0)
        text = "%d%%" % rain
        if day.get("rain_sum"):
            text += " %smm" % T.format_decimal(day["rain_sum"])
        canvas.text(312, y0 + 43, text, RED if rain >= 50 else BLACK, SMALL)


def render_weather(canvas, data):
    canvas.clear(WHITE)
    now = data.get("now")
    header_slim(canvas, S.PAGE_TITLES[1], now)
    weather = data.get("weather")
    if not weather:
        canvas.text(16, 60, S.NO_DATA, RED, MEDIUM)
        canvas.text(16, 92, S.OFFLINE, RED, SMALL)
        footer(canvas, data, S.SOURCES_FALLBACK, compact=True)
        button_markers(canvas)
        return
    current = weather.get("current") or {}
    icons.weather_icon(canvas, 8, 30, 52, current.get("code", 3), current.get("is_day", 1))
    canvas.text(66, 26, big_temp(current.get("temp")), BLACK, XLARGE)
    canvas.text(66, 66, S.WMO.get(current.get("code", 3), "?"), BLACK, SMALL)
    canvas.text(66, 83, "%s %s" % (S.FEELS_LOWER, _deg(current.get("feels"))), BLACK, SMALL)
    draw_sun_arc(canvas, weather.get("sun"), now)
    canvas.hline(8, 103, 258, BLACK)
    blocks = weather.get("wind_blocks") or []
    if blocks:
        draw_wind_blocks(canvas, blocks)
    else:
        canvas.text(16, 105, "%s %s km/h" % (S.WIND, current.get("wind", 0)), BLACK, MEDIUM)
        if current.get("gust") is not None:
            canvas.text(16, 128, "%s %d km/h" % (S.GUSTS_UP_TO, current["gust"]), BLACK, SMALL)
        draw_wind_arrow(canvas, 150, 115, current.get("wind_dir"))
    canvas.hline(8, 155, 258, BLACK)
    draw_hours(canvas, weather.get("hourly"))
    draw_info_band(canvas, weather)
    draw_days(canvas, weather.get("daily"))
    footer(
        canvas,
        data,
        S.SOURCES_HUB if weather.get("source") == "hub" else S.SOURCES_FALLBACK,
        compact=True,
    )
    button_markers(canvas)


# ------------------------------------------------------------ synoptic map page
MAP_TOP = 22


def _map_legend(canvas):
    canvas.fill_rect(14, 234, 240, 42, WHITE)
    canvas.rect(14, 234, 240, 42, BLACK)
    for x in range(20, 46):
        canvas.pixel(x, 245 + int(round(2 * math.sin((x - 20) / 4.0))), BLACK)
    canvas.text(50, 238, S.MAP_ISOBARS, BLACK, SMALL)
    canvas.hline(126, 247, 24, BLACK)
    for x in (130, 140):
        for row in range(5):
            canvas.hline(x + row // 2, 242 + row, 5 - (row // 2) * 2, BLACK)
    canvas.text(156, 238, S.MAP_COLD, BLACK, SMALL)
    canvas.hline(20, 266, 26, RED)
    for x in (26, 38):
        canvas.circle(x, 266, 3, RED, fill=True)
        canvas.hline(x - 3, 267, 7, WHITE)
        canvas.hline(x - 3, 268, 7, WHITE)
        canvas.hline(20, 266, 26, RED)
    canvas.text(50, 258, S.MAP_WARM, BLACK, SMALL)
    canvas.text(126, 258, S.MAP_CENTRES, BLACK, SMALL)


def render_map(canvas, data):
    canvas.clear(WHITE)
    now = data.get("now")
    header_slim(canvas, S.MAP_TITLE, now)
    import synmap  # needs config; only the map page pays for it

    meta = synmap.info()
    if meta is None or not synmap.blit(canvas, MAP_TOP):
        canvas.text(200, 120, S.MAP_NONE, RED, MEDIUM, anchor="center")
        canvas.text(200, 146, S.MAP_NONE_HINT, BLACK, SMALL, anchor="center")
    else:
        x, y = 231, MAP_TOP + 137
        canvas.circle(x, y, 6, RED)
        canvas.circle(x, y, 5, RED)
        canvas.circle(x, y, 2, RED, fill=True)
        canvas.fill_rect(238, y - 8, 31, 15, WHITE)
        canvas.text(239, y - 8, S.MAP_LODZ, RED, SMALL)
        analysis = meta["analysis"]
        utc = time.gmtime(analysis)
        canvas.fill_rect(262, 24, 136, 34, WHITE)
        canvas.rect(262, 24, 136, 34, BLACK)
        canvas.text(266, 25, "%s %02d UTC" % (S.MAP_ANALYSIS, utc[3]), BLACK, SMALL)
        line = "%02d.%02d" % (utc[2], utc[1])
        now_epoch = data.get("now_epoch")
        if now_epoch:
            line += " · %d h %s" % (max(0, now_epoch - analysis) // 3600, S.MAP_AGO)
        canvas.text(266, 41, line, RED if meta["stale"] else BLACK, SMALL)
        _map_legend(canvas)
    canvas.fill_rect(0, 281, 400, 1, BLACK)
    left = "%d/%d" % (data.get("page", 0) + 1, data.get("pages", PAGE_COUNT))
    if data.get("time_synced") and now:
        left += " · %s %02d:00" % (S.NEXT, (now[3] + 1) % 24)
    canvas.text(10, 283, left, BLACK, SMALL)
    canvas.text(390, 283, S.MAP_SOURCE, BLACK, SMALL, anchor="right")
    button_markers(canvas)


def kv(canvas, x, y, label, value, label_width=72, colour=BLACK, value_font=SMALL):
    canvas.text(x, y, label, BLACK, SMALL)
    canvas.text(x + label_width, y, value, colour, value_font)


def render_network(canvas, data):
    canvas.clear(WHITE)
    header(canvas, S.PAGE_TITLES[2], data.get("now"))
    net = data.get("net") or {}
    metrics = data.get("metrics") or {}
    line = 18

    host_value = net.get("dns_name") or "—"
    canvas.text(16, 40, S.HOST, BLACK, SMALL)
    canvas.text(86, 40, host_value, BLACK, SMALL)
    if net.get("dns_name"):
        check_x = 86 + len(host_value) * SMALL.advance + 4
        if check_x < 380:
            if net.get("dns_ok"):
                icons.check(canvas, check_x, 42)
            else:
                icons.cross(canvas, check_x, 42)

    left_rows = (
        (
            S.DNS_SOURCE,
            (net.get("dns_source") or "—") + (" · OK" if net.get("dns_ok") else " · brak"),
        ),
        (S.DHCP, net.get("hostname") or "—"),
        (S.IP, net.get("ip") or "—"),
        ("Maska", net.get("netmask") or "—"),
        (S.GATEWAY, net.get("gateway") or "—"),
        (S.DNS_SERVER, net.get("dns_server") or "—"),
    )
    for index, (label, value) in enumerate(left_rows):
        colour = RED if label == S.DNS_SOURCE and not net.get("dns_ok") else BLACK
        kv(canvas, 16, 62 + index * line, label, value, 76, colour)

    right_rows = (
        (S.MAC, net.get("mac") or "—"),
        ("SSID", net.get("ssid") or "—"),
        ("Kanał", str(net.get("channel", "—"))),
        ("Status", net.get("status") or "—"),
        ("HTTP", ("%d ms" % net["http_ms"]) if net.get("http_ms") else "—"),
        ("Reset", metrics.get("reset_cause") or "—"),
        ("Firm.", metrics.get("firmware") or "—"),
    )
    for index, (label, value) in enumerate(right_rows):
        colour = RED if label == "Status" and data.get("offline") else BLACK
        kv(canvas, 210, 62 + index * line, label, value, 58, colour)

    canvas.rect(12, 190, 376, 76, BLACK)
    canvas.text(24, 198, "JAKOŚĆ SYGNAŁU", BLACK, SMALL)
    rssi = net.get("rssi")
    icons.wifi_bars(canvas, 26, 220, rssi)
    canvas.text(64, 206, ("%d dBm" % rssi) if rssi is not None else "—", BLACK, MEDIUM)
    level = 1
    if rssi is not None:
        if rssi >= -55:
            level = 4
        elif rssi >= -65:
            level = 3
        elif rssi >= -75:
            level = 2
    canvas.text(64, 232, S.GOOD if level >= 3 else S.WEAK, BLACK, SMALL)

    canvas.rect(200, 220, 180, 12, BLACK)
    for index in range(4):
        if index < level:
            canvas.fill_rect(202 + index * 44, 222, 42, 8, BLACK if level > 1 else RED)
    canvas.text(
        200,
        236,
        "kanał %s · %s" % (net.get("channel", "—"), net.get("ssid", "—")),
        BLACK,
        SMALL,
    )
    footer(canvas, data)


def render_capabilities(canvas, data):
    canvas.clear(WHITE)
    header(canvas, S.PAGE_TITLES[3], data.get("now"))

    canvas.text(16, 31, "KOLORY", BLACK, SMALL)
    boxes = (
        (16, BLACK, "CZARNY", None),
        (78, RED, "CZERWONY", None),
        (140, WHITE, "BIAŁY", None),
        (202, None, "50% R", 8),
        (264, None, "25% R", 4),
    )
    for x, colour, label, dither in boxes:
        if dither is not None:
            canvas.dither_rect(x, 49, 56, 30, RED, WHITE, dither)
        else:
            canvas.fill_rect(x, 49, 56, 30, colour)
        canvas.rect(x, 49, 56, 30, BLACK)
        canvas.text(x, 83, label, BLACK, SMALL)

    canvas.text(16, 101, S.DITHER, BLACK, SMALL)
    for index, (label, level) in enumerate((("25%", 4), ("50%", 8), ("75%", 12))):
        x = 16 + index * 48
        canvas.dither_rect(x, 119, 40, 26, RED, WHITE, level)
        canvas.rect(x, 119, 40, 26, BLACK)
        canvas.text(x, 149, label, BLACK, SMALL)
    canvas.dither_rect(160, 119, 40, 26, BLACK, WHITE, 8)
    canvas.rect(160, 119, 40, 26, BLACK)
    canvas.text(160, 149, "B 50%", BLACK, SMALL)

    canvas.text(224, 101, "GEOMETRIA", BLACK, SMALL)
    canvas.circle(244, 134, 17, RED)
    for yy in range(0, 22):
        for xx in range(0, 22):
            if (xx + yy) & 1:
                canvas.pixel(282 + xx, 121 + yy, BLACK)
    for step in range(6):
        canvas.line(322, 150, 348 + step * 6, 119, BLACK)

    canvas.text(16, 168, "FONTY", BLACK, SMALL)
    canvas.text(16, 187, "Zażółć gęślą jaźń", BLACK, SMALL)
    canvas.text(16, 206, "PICO 4.2-B", BLACK, MEDIUM)
    canvas.text(16, 229, "400×300", BLACK, LARGE)

    canvas.text(224, 168, "ODŚWIEŻANIE", BLACK, SMALL)
    metrics = data.get("metrics") or {}
    canvas.text(224, 187, "Transfer %s s" % T.format_decimal(metrics.get("transfer_ms", 0) / 1000.0), BLACK, SMALL)
    canvas.text(224, 203, "Panel %s s" % T.format_decimal(metrics.get("busy_ms", 0) / 1000.0), BLACK, SMALL)
    canvas.text(224, 219, "Razem %s s" % T.format_decimal(metrics.get("total_ms", 0) / 1000.0), BLACK, SMALL)

    bar_x = 224
    bar_y = 236
    bar_w = 160
    canvas.rect(bar_x, bar_y, bar_w, 10, BLACK)
    measured = metrics.get("total_ms", 0) / 1000.0
    fill = min(bar_w - 2, int(measured * (bar_w - 2) / 25.0))
    canvas.fill_rect(bar_x + 1, bar_y + 1, fill, 8, BLACK)
    spec_x = bar_x + 1 + int(15 * (bar_w - 2) / 25.0)
    canvas.fill_rect(spec_x, bar_y - 2, 2, 14, RED)
    canvas.text(224, 248, "spec 15 s", BLACK, SMALL)
    canvas.text(224, 264, "pełne odświeżanie", BLACK, SMALL)
    canvas.text(16, 258, "3 kolory + rastrowanie", BLACK, SMALL)

    footer(canvas, data)


def render_about(canvas, data):
    canvas.clear(WHITE)
    header(canvas, S.PAGE_TITLES[4], data.get("now"))
    canvas.text(16, 42, S.ABOUT[0], BLACK, MEDIUM)
    canvas.fill_rect(16, 66, 260, 1, RED)
    for index, line in enumerate(S.ABOUT[1:]):
        canvas.text(16, 76 + index * 19, line, BLACK, MEDIUM)

    net = data.get("net") or {}
    host = net.get("dns_name") or net.get("hostname") or "—"
    ip = net.get("ip") or "—"
    canvas.text(16, 252, "Host: %s · IP: %s" % (host, ip), BLACK, SMALL)
    footer(canvas, data)


# Pogoda is the default page (index 0, shown at boot); 2026-11-09 user decision.
PAGES = (
    render_weather,
    render_map,
    render_dashboard,
    render_network,
    render_capabilities,
    render_about,
)
