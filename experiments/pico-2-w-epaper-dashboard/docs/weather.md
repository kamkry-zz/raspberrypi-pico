# Weather data

Source: [Open-Meteo](https://open-meteo.com/), free non-commercial API, no key.

## Request

```text
https://api.open-meteo.com/v1/forecast
  ?latitude=51.7592&longitude=19.4560
  &current=temperature_2m,relative_humidity_2m,apparent_temperature,
           precipitation,weather_code,wind_speed_10m,is_day
  &daily=weather_code,temperature_2m_max,temperature_2m_min,
         precipitation_probability_max
  &hourly=temperature_2m,precipitation_probability,weather_code
  &timezone=Europe/Warsaw&forecast_days=3&wind_speed_unit=kmh
```

The request is built in `lib/weather.py`. `timezone=auto` is not used because
the experiment is permanently configured for Łódź; the response still contains
`utc_offset_seconds`, which is authoritative for the clock.

## Fields used

| Field | Use |
| --- | --- |
| `current.temperature_2m` | large current temperature |
| `current.apparent_temperature` | “Odczuwalna” |
| `current.relative_humidity_2m` | “Wilgotność” |
| `current.wind_speed_10m` | “Wiatr” (km/h) |
| `current.precipitation` | “Opad” (mm) |
| `current.weather_code` | icon + Polish description |
| `current.is_day` | sun/moon icon selection |
| `daily.time/code/max/min/precipitation_probability_max` | 3-day rows |
| `hourly.time/temperature_2m/precipitation_probability/weather_code` | 12-hour chart |
| `utc_offset_seconds` | local clock offset including DST |

Daily labels are `Dziś`, `Jutro`, then the Polish weekday abbreviation. The
hourly slice starts at the current local hour (matching the `current.time`
prefix) and contains up to 12 entries.

## WMO codes

`lib/strings_pl.py` maps the WMO 4677 codes to Polish descriptions. The most
common ones:

| Code | Meaning | Code | Meaning |
| --- | --- | --- | --- |
| 0 | Bezchmurnie | 61/63/65 | Deszcz (light/moderate/heavy) |
| 1 | Głównie słonecznie | 66/67 | Marznący deszcz |
| 2 | Częściowe zachmurzenie | 71/73/75 | Śnieg |
| 3 | Zachmurzenie | 80/81/82 | Przelotny deszcz |
| 45/48 | Mgła | 85/86 | Przelotny śnieg |
| 51/53/55 | Mżawka | 95/96/99 | Burza / burza z gradem |

## Caching and failures

- Parsed data is cached in RAM for 10 minutes.
- The hourly refresh forces a new request; button refreshes may reuse the cache.
- A failed request marks the cached data `stale` and the weather panel shows
  `nieaktualne` in red.
- With no cache the panel shows `Brak danych` / `OFFLINE`.
- HTTPS is attempted first; if the MicroPython TLS handshake fails the client
  retries the same URL over HTTP. Weather data is public; certificate pinning is
  out of scope.

## Time fallback

If NTP is unavailable, the HTTP `Date` response header supplies a UTC epoch.
Open-Meteo's `utc_offset_seconds` then gives local time. This also handles the
March/October DST changes.

## Attribution

Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0). The
dashboard footer and the About page include the attribution.
