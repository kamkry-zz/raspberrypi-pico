# Pico-ePaper-4.2-B dashboard configuration.
# This file is safe to commit. The Wi-Fi password lives in secrets.py.

# --- Wi-Fi -----------------------------------------------------------------
# Dedicated IoT WLAN. The Pico W is 2.4 GHz only; this SSID must be 2.4 GHz
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
WEATHER_DAYS = 3
WEATHER_HOURS = 12
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
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
USER_AGENT = "pico-epaper-dashboard/0.1"
