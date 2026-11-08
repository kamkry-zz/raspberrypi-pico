# Freeze manifest: MicroPython v1.23.0 for RPI_PICO_W plus the dashboard's
# lib/ modules compiled into flash.  Frozen bytecode and its constants (fonts,
# tables) are executed from flash, giving back ~89 KB of GC heap.
#
# config.py, secrets.py, certs/ and the main.py shim stay on the filesystem so
# configuration can change without a reflash.  sys.path is
# ['', '.frozen', '/lib'], so frozen modules win over /lib copies.

include("$(PORT_DIR)/boards/RPI_PICO_W/manifest.py")

for name in (
    "app",
    "buttons",
    "canvas",
    "clock",
    "epd42b",
    "font_large",
    "font_medium",
    "font_small",
    "http_client",
    "icons",
    "metrics",
    "net",
    "pages",
    "store",
    "strings_pl",
    "supervisor",
    "telemetry",
    "timeutil",
    "weather",
):
    module(name + ".py", base_path="/src/lib")
