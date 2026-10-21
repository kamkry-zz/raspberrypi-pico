"""Dashboard pages rendered with the portable canvas."""

import time

import icons
import strings_pl as S
import timeutil as T
from canvas import BLACK, RED, WHITE
from font_large import FONT as LARGE
from font_medium import FONT as MEDIUM
from font_small import FONT as SMALL

PAGE_COUNT = 5


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


def footer(canvas, data):
    canvas.fill_rect(0, 281, 400, 1, BLACK)
    now = data.get("now")
    metrics = data.get("metrics") or {}
    page = data.get("page", 0) + 1
    pages = data.get("pages", PAGE_COUNT)
    total_s = metrics.get("total_ms", 0) / 1000.0
    if data.get("time_synced") and now:
        clock = T.format_clock(now)
        next_hour = (now[3] + 1) % 24
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
    canvas.text(390, 283, "Open-Meteo", BLACK, SMALL, anchor="right")


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


def draw_hourly(canvas, hourly, x, y):
    canvas.text(x, y, "GODZINOWO · 12 H", BLACK, SMALL)
    points = (hourly or [])[:12]
    if len(points) < 2:
        return

    left = x
    right = x + 368
    top = y + 14
    bottom = y + 44
    base = y + 60
    step = (right - left) // (len(points) - 1)

    temperatures = [point.get("temp", 0) for point in points]
    low = min(temperatures)
    high = max(temperatures)
    if high == low:
        high = low + 1

    for index, point in enumerate(points):
        px = left + index * step
        height = int(point.get("rain", 0) * 16 / 100)
        if height > 0:
            canvas.fill_rect(px - 2, base - height, 5, height, RED)

    previous = None
    for index, point in enumerate(points):
        px = left + index * step
        py = bottom - int((point.get("temp", 0) - low) * (bottom - top) / (high - low))
        if previous:
            canvas.line(previous[0], previous[1], px, py, BLACK)
        canvas.fill_rect(px - 1, py - 1, 3, 3, RED)
        previous = (px, py)

    canvas.fill_rect(left, base, right - left, 1, BLACK)
    for index, point in enumerate(points):
        px = left + index * step
        canvas.text(px, base + 4, point.get("hour", ""), BLACK, SMALL, anchor="center")


def render_weather(canvas, data):
    canvas.clear(WHITE)
    header(canvas, S.PAGE_TITLES[1], data.get("now"))

    weather = data.get("weather")
    if not weather:
        canvas.text(16, 60, S.NO_DATA, RED, MEDIUM)
        canvas.text(16, 92, S.OFFLINE, RED, SMALL)
        footer(canvas, data)
        return

    current = weather.get("current") or {}
    icons.weather_icon(
        canvas, 16, 38, 48, current.get("code", 3), current.get("is_day", 1)
    )
    canvas.text(72, 38, T.format_temp(current.get("temp", 0)), BLACK, LARGE)
    canvas.text(16, 92, S.WMO.get(current.get("code", 3), "?"), BLACK, SMALL)

    kv(canvas, 16, 110, S.FEELS, T.format_temp(current.get("feels", 0)), 76, value_font=MEDIUM)
    kv(canvas, 16, 130, S.HUMIDITY, "%d%%" % current.get("humidity", 0), 76, value_font=MEDIUM)
    kv(canvas, 16, 150, S.WIND, "%d km/h" % current.get("wind", 0), 76, value_font=MEDIUM)
    kv(
        canvas,
        16,
        170,
        S.PRECIP,
        T.format_decimal(current.get("precip", 0)) + " mm",
        76,
        value_font=MEDIUM,
    )

    canvas.text(210, 38, "PROGNOZA", BLACK, SMALL)
    canvas.fill_rect(210, 52, 178, 1, RED)
    for index, day in enumerate((weather.get("daily") or [])[:3]):
        yy = 58 + index * 30
        canvas.text(210, yy, day.get("label", ""), BLACK, SMALL)
        icons.weather_icon(canvas, 250, yy - 4, 24, day.get("code", 3), True)
        canvas.text(
            280, yy, "%d/%d" % (day.get("tmax", 0), day.get("tmin", 0)), BLACK, SMALL
        )
        rain = day.get("rain", 0)
        canvas.text(
            384,
            yy,
            "%d%%" % rain,
            RED if rain >= 50 else BLACK,
            SMALL,
            anchor="right",
        )

    canvas.fill_rect(203, 36, 2, 160, RED)
    draw_hourly(canvas, weather.get("hourly"), 16, 198)
    footer(canvas, data)


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


PAGES = (
    render_dashboard,
    render_weather,
    render_network,
    render_capabilities,
    render_about,
)
