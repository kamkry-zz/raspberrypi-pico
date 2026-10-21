"""Pico W e-paper dashboard entry point.

Run without writing to the board:

    .venv/bin/mpremote mount . run main.py

The panel stays awake between updates (matching the working legacy program).
Every full refresh takes about 23 s on this older 4.2-B unit.
"""

import gc
import sys
import time

sys.path.append("lib")

import config
import metrics
import net
import timeutil as T
import weather
from buttons import Buttons
from clock import Clock
from epd42b import EPD42B


def build_data(panel, clock, force_weather, timeout_ms, page_count):
    gc.collect()
    started = time.ticks_ms()
    wifi_ok = net.ensure(timeout_ms)
    info = net.info()

    if wifi_ok and info.get("ip") not in (None, "—", "0.0.0.0"):
        name, verified, source = net.resolve_dns_name(info["ip"], config.DNS_NAME)
    else:
        name, verified, source = None, False, None
    info["dns_name"] = name
    info["dns_ok"] = verified
    info["dns_source"] = source

    http_started = time.ticks_ms()
    if wifi_ok:
        current_weather = weather.fetch(force=force_weather)
    else:
        current_weather = weather.cached()
        if current_weather is not None:
            current_weather["stale"] = True
    info["http_ms"] = time.ticks_diff(time.ticks_ms(), http_started)

    if wifi_ok and not clock.synced():
        epoch = net.ntp_sync()
        if epoch:
            clock.set(epoch, T.eu_offset(epoch))

    if current_weather and current_weather.get("date_epoch"):
        if force_weather or not clock.synced():
            clock.set(current_weather["date_epoch"], current_weather.get("offset_s"))
        else:
            clock.set_offset(current_weather.get("offset_s"))

    now = clock.now()
    data = {
        "now": now,
        "now_epoch": clock.epoch(),
        "time_synced": clock.synced(),
        "offline": (not wifi_ok) or (current_weather is None),
        "page": 0,
        "pages": page_count,
        "weather": current_weather,
        "net": info,
        "metrics": metrics.gather(panel),
    }
    return data, time.ticks_diff(time.ticks_ms(), started)


def render(panel, canvas, page, data, pages):
    data["page"] = page
    started = time.ticks_ms()
    pages[page](canvas, data)
    render_ms = time.ticks_diff(time.ticks_ms(), started)
    gc.collect()
    panel.display(canvas.black, canvas.red)
    return render_ms


def schedule_next(clock):
    now = clock.now()
    if config.REFRESH_AT_TOP_OF_HOUR and now:
        return time.ticks_ms() + T.seconds_to_next_hour(now) * 1000 + 5000
    return time.ticks_ms() + config.REFRESH_MINUTES * 60 * 1000


def main():
    print("Pico W e-paper dashboard")

    # Allocate the two contiguous 15 KB canvas planes before the panel clear
    # and the network stack fragment the heap.  The clear only needs a 15 KB
    # temporary buffer and the canvas is then guaranteed to survive.
    gc.collect()
    from canvas import Canvas
    from pages import PAGES

    gc.collect()
    page_count = len(PAGES)
    canvas = Canvas(config.WIDTH, config.HEIGHT)
    gc.collect()

    print("Panel init + vendor clear (about 24 s)...")
    panel = EPD42B()
    print(
        "Panel:",
        panel.revision,
        "init",
        panel.last_init_ms,
        "clear",
        panel.last_total_ms,
    )

    buttons = Buttons(
        (config.PIN_KEY_PREV, config.PIN_KEY_NEXT),
        config.BUTTON_DEBOUNCE_MS,
        config.BUTTON_LONG_PRESS_MS,
    )
    clock = Clock()
    page = 0

    print("Gathering first data...")
    data, fetch_ms = build_data(panel, clock, True, 20000, page_count)
    render_ms = render(panel, canvas, page, data, PAGES)
    metrics.mark_active(fetch_ms + render_ms + panel.last_total_ms)
    metrics.reset_interval()
    print(
        "First frame: fetch %d ms, render %d ms, panel %d ms"
        % (fetch_ms, render_ms, panel.last_total_ms)
    )
    if config.RUN_ONCE:
        print("RUN_ONCE: first frame displayed; panel keeps the image")
        return

    next_refresh = schedule_next(clock)
    cleared_day = None

    while True:
        try:
            event = buttons.poll()
            if event:
                kind, index = event
                # Both short and long presses navigate.  This avoids the
                # ambiguity of a press held through a 16-23 s panel refresh
                # being treated as "refresh the same page".
                if index == 0:
                    page = (page - 1) % page_count
                else:
                    page = (page + 1) % page_count
                print("Button:", kind, index, "-> page", page + 1)
                data, fetch_ms = build_data(panel, clock, False, 8000, page_count)
                render_ms = render(panel, canvas, page, data, PAGES)
                metrics.mark_active(fetch_ms + render_ms + panel.last_total_ms)
                print(
                    "Refresh: fetch %d ms, render %d ms, panel %d ms"
                    % (fetch_ms, render_ms, panel.last_total_ms)
                )
                next_refresh = schedule_next(clock)

            if time.ticks_diff(time.ticks_ms(), next_refresh) >= 0:
                now = clock.now()
                if (
                    config.NIGHTLY_CLEAR
                    and now
                    and now[3] == config.NIGHTLY_CLEAR_HOUR
                    and now[4] == 0
                    and cleared_day != (now[0], now[1], now[2])
                ):
                    cleared_day = (now[0], now[1], now[2])
                    print("Nightly clear")
                    panel.clear()
                    metrics.mark_active(panel.last_total_ms)

                data, fetch_ms = build_data(panel, clock, True, 20000, page_count)
                render_ms = render(panel, canvas, page, data, PAGES)
                metrics.mark_active(fetch_ms + render_ms + panel.last_total_ms)
                print(
                    "Hourly: fetch %d ms, render %d ms, panel %d ms"
                    % (fetch_ms, render_ms, panel.last_total_ms)
                )
                next_refresh = schedule_next(clock)

            time.sleep_ms(100)
        except KeyboardInterrupt:
            print("Stopped by user; panel keeps the last frame")
            return
        except Exception as exc:
            print("Refresh error:", repr(exc))
            next_refresh = time.ticks_ms() + 60000
            time.sleep_ms(1000)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
    except Exception as exc:
        print("FATAL:", repr(exc))
        raise
