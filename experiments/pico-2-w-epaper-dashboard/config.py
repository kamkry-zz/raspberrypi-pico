# Pico-ePaper-4.2-B dashboard configuration.
# This file is safe to commit. The Wi-Fi password lives in secrets.py.

# --- Wi-Fi -----------------------------------------------------------------
# Dedicated IoT WLAN. The Pico 2 W (CYW43439) is 2.4 GHz only; this SSID must be 2.4 GHz
# and use WPA2-PSK. There is deliberately no fallback to another network.
WIFI_SSID = "krys_dom_IoT"
WIFI_COUNTRY = "PL"
HOSTNAME = "pico-dash"  # DHCP client name; not necessarily the DNS name

# Optional DNS name override. Leave empty to discover it with a reverse-DNS
# (PTR) lookup of the DHCP address. Example: "panel.example.lan".
DNS_NAME = ""

# --- Location --------------------------------------------------------------
# Lodz, Poland.
LOCATION_NAME = "Łódź"
LATITUDE = 51.7592
LONGITUDE = 19.4560
TIMEZONE = "Europe/Warsaw"
# Used only when neither the weather API nor NTP can provide an offset.
UTC_OFFSET_FALLBACK_S = 3600

# --- Weather ---------------------------------------------------------------
WEATHER_DAYS = 5
WEATHER_HOURS = 12
# Plain HTTP: a second TLS session does not fit the heap next to the OTLP
# export (see README "Memory"); the forecast is public data.
WEATHER_URL = "http://api.open-meteo.com/v1/forecast"
# Primary source: the krysdom-api pogoda-hub (LAN). Its /v1 device API is
# plain HTTP on purpose (no TLS heap); Open-Meteo above is the fallback.
HUB_WEATHER_URL = "http://pogoda-hub.k3s/v1/weather"
HUB_MAP_URL = "http://pogoda-hub.k3s/v1/map.bin"
# IMGW synoptic map (400x250 panel planes, ~25 KB) cached on flash.
MAP_CACHE_FILE = "/map.bin"
MAP_META_FILE = "/map.json"
MAP_CHECK_MINUTES = 30
HTTP_TIMEOUT_S = 12

# --- Refresh policy --------------------------------------------------------
# The 4.2-B does a full refresh only (~23 s on this older unit). No clock.
REFRESH_MINUTES = 60
REFRESH_AT_TOP_OF_HOUR = True
# Set True only for a first-frame hardware test; it exits after one display.
RUN_ONCE = False
# Optional white frame at night for stubborn ghosting. Off by default: the
# hourly full refresh already satisfies the panel's 24 h anti-ghosting advice.
NIGHTLY_CLEAR = False
NIGHTLY_CLEAR_HOUR = 3

# --- Display / pins --------------------------------------------------------
# The vendored driver in lib/epd42b.py currently hardcodes the same pins and
# 4 MHz SPI clock; keep these values in sync if you change the wiring.
WIDTH = 400
HEIGHT = 300

PIN_SCK = 10
PIN_MOSI = 11
PIN_CS = 9
PIN_DC = 8
PIN_RST = 12
PIN_BUSY = 13
PIN_KEY_PREV = 15
PIN_KEY_NEXT = 17

# --- Behaviour -------------------------------------------------------------
BUTTON_DEBOUNCE_MS = 300
BUTTON_LONG_PRESS_MS = 1200
VERSION = "0.4.0"
USER_AGENT = "pico-epaper-dashboard/" + VERSION

# --- Resilience (auto-start, power loss, network outages) --------------------
# Hardware watchdog fed only while the app makes progress; a Python-level
# stall longer than WATCHDOG_STALL_S resets the board.  Must exceed the
# longest legitimate blocking step (panel clear + refresh + network ~2 min).
WATCHDOG_ENABLED = True
WATCHDOG_STALL_S = 300
# Retry delays after an offline / failed refresh (seconds); the last value
# repeats.  A healthy board goes back to the top-of-hour schedule.
RETRY_BACKOFF_S = (60, 120, 300, 600, 900)
# Re-initialise the CYW43 radio after this many failed connects in a row and
# reboot the whole board after WIFI_REBOOT_AFTER_FAILS.
WIFI_REINIT_AFTER_FAILS = 2
WIFI_REBOOT_AFTER_FAILS = 12
# Last good weather, written atomically to flash and shown (as stale) when a
# boot has no network yet.
WEATHER_CACHE_FILE = "/weather.json"
# /healthz turns unhealthy when no frame was displayed for this long.
HEALTH_MAX_FRAME_AGE_S = 2 * 3600

# Contiguous heap block taken right after the canvas and released only for
# TLS/HTTP work, so the OTLP handshake (~26 KB) always finds room.
HEAP_RESERVE = 24 * 1024

# --- Observability (observatory.k3s) ---------------------------------------
# Primary path: the cluster collector scrapes http://<pico>:METRICS_PORT/metrics
# (prometheus/apps relay job).  No TLS on the Pico, so it always fits the heap.
#
# Optional OTLP/HTTP JSON push (metrics + logs + refresh traces) to the
# collector, CA-verified like the other external appliances.  Verified working
# on the frozen-module firmware (firmware/build.sh): ~130 KB heap free, 3
# requests in ~1.8 s.  OFF by default (deferred).  When enabling it, drop the
# pico-epaper-dashboard scrape job in krysdom-api, or the series duplicate.
# Source-only (non-frozen) installs do not have the heap for TLS.
OTLP_ENABLED = False
OTLP_HOST = "otel.k3s"
OTLP_CA_FILE = "certs/k3s-ca.der"  # krysdom my-selfsigned-ca, DER, public
OTLP_INTERVAL_S = 60
OTLP_TIMEOUT_S = 6
OTEL_SERVICE_NAME = "pico-epaper-dashboard"
OTEL_INSTANCE = "raspberry-pi-pico-2-wh-02.iot"
# Local Prometheus text endpoint (/metrics) and /healthz; 0 disables it.
METRICS_PORT = 9100

# --- Over-the-air updates (iot-registry; openspec/changes/ota-app-updates) ---
# Fully automatic: a newer release signed with secrets.OTA_KEY is installed on
# trial and committed after its first frame; 3 uncommitted boots roll back.
OTA_ENABLED = True
OTA_BASE_URL = "http://iot-registry.k3s/ota/v1"  # plain HTTP, LAN-only route
OTA_APP = "pico-epaper-dashboard"
OTA_CHECK_MINUTES = 60
