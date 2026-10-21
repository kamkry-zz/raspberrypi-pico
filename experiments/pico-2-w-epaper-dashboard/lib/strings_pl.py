"""Polish UI strings for the dashboard."""

TITLE = "KRYSDOM"

WEEKDAYS = (
    "poniedziałek",
    "wtorek",
    "środa",
    "czwartek",
    "piątek",
    "sobota",
    "niedziela",
)
WEEKDAYS_SHORT = ("pon.", "wt.", "śr.", "czw.", "pt.", "sob.", "niedz.")

MONTHS = (
    "stycznia",
    "lutego",
    "marca",
    "kwietnia",
    "maja",
    "czerwca",
    "lipca",
    "sierpnia",
    "września",
    "października",
    "listopada",
    "grudnia",
)

# WMO 4677 weather codes used by Open-Meteo.
WMO = {
    0: "Bezchmurnie",
    1: "Głównie słonecznie",
    2: "Częściowe zachmurzenie",
    3: "Zachmurzenie",
    45: "Mgła",
    48: "Mgła osadzająca szadź",
    51: "Lekka mżawka",
    53: "Mżawka",
    55: "Gęsta mżawka",
    56: "Marznąca mżawka",
    57: "Gęsta marznąca mżawka",
    61: "Lekki deszcz",
    63: "Deszcz",
    65: "Silny deszcz",
    66: "Marznący deszcz",
    67: "Silny marznący deszcz",
    71: "Lekki śnieg",
    73: "Śnieg",
    75: "Silny śnieg",
    77: "Ziarna śniegu",
    80: "Przelotny deszcz",
    81: "Przelotne opady",
    82: "Gwałtowne opady",
    85: "Przelotny śnieg",
    86: "Silne opady śniegu",
    95: "Burza",
    96: "Burza z gradem",
    99: "Silna burza z gradem",
}

# Short labels used in tight rows.
WMO_SHORT = {
    0: "Jasno",
    1: "Słonecznie",
    2: "Częściowo",
    3: "Chmurno",
    45: "Mgła",
    48: "Mgła",
    51: "Mżawka",
    53: "Mżawka",
    55: "Mżawka",
    56: "Mżawka",
    57: "Mżawka",
    61: "Deszcz",
    63: "Deszcz",
    65: "Deszcz",
    66: "Deszcz",
    67: "Deszcz",
    71: "Śnieg",
    73: "Śnieg",
    75: "Śnieg",
    77: "Śnieg",
    80: "Przelotny",
    81: "Przelotny",
    82: "Przelotny",
    85: "Śnieg",
    86: "Śnieg",
    95: "Burza",
    96: "Burza",
    99: "Burza",
}

YEAR = "ROK"
DAY = "Dzień"
OF = "z"
LEFT = "pozostało"
DAYS = "dni"
LEAP = "rok przestępny"

NETWORK = "SIEĆ"
SYSTEM = "SYSTEM"
HOST = "Host"
IP = "IP"
WIFI = "WiFi"
MAC = "MAC"
DHCP = "DHCP"
DNS = "DNS"
GATEWAY = "Brama"
DNS_SERVER = "Serwer DNS"
DNS_SOURCE = "Źródło"
UPTIME = "Czas"
RAM = "RAM"
FLASH = "Flash"
TEMP = "Temp"
ACTIVE = "Aktywny"

WEATHER = "POGODA"
TODAY = "Dziś"
TOMORROW = "Jutro"
FEELS = "Odczuwalna"
HUMIDITY = "Wilgotność"
WIND = "Wiatr"
PRECIP = "Opad"
RAIN_CHANCE = "deszcz"

UPDATED = "Akt."
NEXT = "nast."
PAGE = "Strona"
STALE = "nieaktualne"
OFFLINE = "OFFLINE"
NO_DATA = "Brak danych"
NO_TIME = "Czas niezsynchronizowany"
CONNECTING = "Łączenie z WiFi..."
CONNECTED = "Połączono"
WEAK = "słaby"
GOOD = "dobry"

PAGE_TITLES = (
    "KRYSDOM",
    "POGODA · ŁÓDŹ",
    "SIEĆ · krys_dom_IoT",
    "MOŻLIWOŚCI PANELU",
    "O PROGRAMIE",
)

CAPABILITIES = "MOŻLIWOŚCI"
COLORS = "KOLORY"
DITHER = "RASTROWANIE"
FONTS = "FONTY"
GEOMETRY = "GEOMETRIA"
REFRESH = "ODŚWIEŻANIE"
TRANSFER = "Transfer"
PANEL = "Panel"
TOTAL = "Razem"
FULL_REFRESH = "Tylko pełne odświeżanie"
NO_GREY = "Brak szarości: 3 kolory + dithering"
SPEC = "spec 15 s"

ABOUT = (
    "Pico W + Pico-ePaper-4.2-B",
    "400×300 · czarny / biały / czerwony",
    "Sterownik: stara rewizja (0x2F = 0xFF)",
    "Odświeżanie: co godzinę + przyciski",
    "GP15 wstecz · GP17 dalej (lewa krawędź)",
    "Naciśnij: zmiana strony + odświeżenie",
    "WiFi: krys_dom_IoT (tylko 2,4 GHz)",
    "Dane pogodowe: Open-Meteo",
    "Dokumentacja: docs/ w repozytorium",
    "Wersja: 0.1.0",
)
