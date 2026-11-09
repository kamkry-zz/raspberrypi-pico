#!/usr/bin/env python3
"""Render dashboard frames on the host, using the same code as the Pico.

No hardware and no third-party packages required:

    python3 tools/preview.py --frame dashboard
    python3 tools/preview.py --frame all --scale 2
"""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT))  # config.py (map page)
sys.path.insert(0, str(ROOT / "tools"))

import fixtures  # noqa: E402
import pages  # noqa: E402
from canvas import Canvas  # noqa: E402
from png import write_canvas  # noqa: E402


def render_bringup(canvas):
    import testpattern

    testpattern.draw(canvas)


def render_dashboard(canvas):
    pages.render_dashboard(canvas, fixtures.sunny())


def render_dashboard_rain(canvas):
    pages.render_dashboard(canvas, fixtures.rainy())


def render_dashboard_offline(canvas):
    pages.render_dashboard(canvas, fixtures.offline())


def _page(index):
    data = fixtures.sunny()
    data["page"] = index
    return data


def render_weather(canvas):
    pages.render_weather(canvas, _page(0))


def render_weather_hub(canvas):
    data = fixtures.hub_day()
    data["page"] = 0
    pages.render_weather(canvas, data)


def render_weather_hub_night(canvas):
    data = fixtures.hub()
    data["page"] = 0
    pages.render_weather(canvas, data)


def render_weather_hub_warning(canvas):
    data = fixtures.hub_warning()
    data["page"] = 0
    pages.render_weather(canvas, data)


def render_map(canvas):
    """Synthetic map unless MAP_BIN points at a real /v1/map.bin download."""
    import os
    import tempfile

    import config

    path = os.environ.get("MAP_BIN")
    if not path:
        path = fixtures.make_map_bin(os.path.join(tempfile.mkdtemp(), "map.bin"))
    config.MAP_CACHE_FILE = path
    data = fixtures.hub_day()
    data["page"] = 1
    pages.render_map(canvas, data)


def render_network(canvas):
    pages.render_network(canvas, _page(3))


def render_capabilities(canvas):
    pages.render_capabilities(canvas, _page(4))


def render_about(canvas):
    pages.render_about(canvas, _page(5))


FRAMES = {
    "bringup": render_bringup,
    "dashboard": render_dashboard,
    "dashboard_rain": render_dashboard_rain,
    "dashboard_offline": render_dashboard_offline,
    "weather": render_weather,
    "weather_hub": render_weather_hub,
    "weather_hub_night": render_weather_hub_night,
    "weather_hub_warning": render_weather_hub_warning,
    "map": render_map,
    "network": render_network,
    "capabilities": render_capabilities,
    "about": render_about,
}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", default="all", choices=sorted(FRAMES) + ["all"])
    parser.add_argument("--out", default=str(ROOT / "docs" / "images"))
    parser.add_argument("--scale", type=int, default=1)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    names = sorted(FRAMES) if args.frame == "all" else [args.frame]
    for name in names:
        canvas = Canvas(400, 300)
        FRAMES[name](canvas)
        path = out_dir / ("%s.png" % name)
        write_canvas(path, canvas, scale=args.scale)
        print("wrote", path)


if __name__ == "__main__":
    main()
