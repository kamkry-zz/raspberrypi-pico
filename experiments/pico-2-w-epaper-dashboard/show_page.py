"""Show one dashboard page without using the physical buttons.

Edit PAGE below (0 = dashboard, 1 = weather, 2 = network, 3 = capabilities,
4 = about) and run:

    .venv/bin/mpremote mount . run show_page.py

This fetches fresh network/weather data and then performs one full refresh.
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
from clock import Clock
from epd42b import EPD42B

PAGE = 0


def run():
    gc.collect()
    from canvas import Canvas
    from pages import PAGES

    gc.collect()
    canvas = Canvas(config.WIDTH, config.HEIGHT)
    gc.collect()
    panel = EPD42B()
    print("panel", panel.revision, "clear", panel.last_total_ms)

    clock = Clock()
    wifi_ok = net.ensure(20000)
    info = net.info()
    if wifi_ok and info.get("ip") not in (None, "—", "0.0.0.0"):
        name, verified, source = net.resolve_dns_name(info["ip"], config.DNS_NAME)
    else:
        name, verified, source = None, False, None
    info["dns_name"] = name
    info["dns_ok"] = verified
    info["dns_source"] = source

    started = time.ticks_ms()
    current_weather = weather.fetch(force=True) if wifi_ok else None
    info["http_ms"] = time.ticks_diff(time.ticks_ms(), started)

    if wifi_ok and not clock.synced():
        epoch = net.ntp_sync()
        if epoch:
            clock.set(epoch, T.eu_offset(epoch))
    if current_weather and current_weather.get("date_epoch"):
        clock.set(current_weather["date_epoch"], current_weather.get("offset_s"))

    data = {
        "now": clock.now(),
        "time_synced": clock.synced(),
        "offline": (not wifi_ok) or (current_weather is None),
        "page": PAGE,
        "pages": len(PAGES),
        "weather": current_weather,
        "net": info,
        "metrics": metrics.gather(panel),
    }

    index = PAGE if 0 <= PAGE < len(PAGES) else 0
    PAGES[index](canvas, data)
    gc.collect()
    panel.display(canvas.black, canvas.red)
    print("page", index + 1, "panel", panel.last_total_ms, "ms")
    print("done; panel keeps the page")


run()
