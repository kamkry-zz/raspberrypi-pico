## Purpose

Render a Polish, Pico-only home dashboard on the 4.2-B panel with year
progress, local weather, network identity and system metrics, refreshed
hourly and on demand without a live clock.

## ADDED Requirements

### Requirement: Pico-only system metrics
The dashboard SHALL show the Pico W's own hostname, IP, gateway, SSID, RSSI,
MAC, uptime, heap, flash, die temperature and activity figure.

#### Scenario: Load average is unavailable
- **WHEN** the dashboard renders the system panel
- **THEN** it shows an interval-based “Aktywny” percentage and refresh timings,
  and does not claim a Linux load average

#### Scenario: Memory reporting
- **WHEN** the dashboard gathers metrics
- **THEN** it calls `gc.collect()` and reports allocated/free heap and
  flash used/total

### Requirement: DNS name self-discovery
The dashboard SHALL discover the full DNS name with a PTR query of its DHCP
address, verify the name forward, and fall back to configured or DHCP names.

#### Scenario: Verified PTR
- **WHEN** the PTR returns a name that resolves to the Pico's IP
- **THEN** the Network page shows the full name and a check mark

#### Scenario: No PTR
- **WHEN** the PTR lookup fails
- **THEN** `config.DNS_NAME` is used if set, otherwise the DHCP hostname

#### Scenario: Long DNS name
- **WHEN** the full DNS name does not fit the compact dashboard row
- **THEN** the dashboard shows the short DHCP name and the full name remains
  visible on the Network and About pages

### Requirement: Local weather
The dashboard SHALL fetch Open-Meteo data for Łódź (`51.7592, 19.4560`,
`Europe/Warsaw`) and show current conditions, three daily rows and a 12-hour
chart, in Polish, with attribution.

#### Scenario: Normal fetch
- **WHEN** the hourly refresh runs
- **THEN** current, daily and hourly fields are parsed and the Weather page
  chart starts at the current local hour

#### Scenario: Fetch failure
- **WHEN** the weather request fails but a cache exists
- **THEN** the cached data is shown and marked `nieaktualne`

#### Scenario: No data
- **WHEN** there is no cache and no connection
- **THEN** the weather panel shows `Brak danych` and `OFFLINE` in red

### Requirement: Year progress
The dashboard SHALL show elapsed-year percentage and a 12 × 31 year grid with
past days black, today red and future days white.

#### Scenario: Leap year
- **WHEN** the current year is a leap year
- **THEN** the percentage uses 366 days and the February column includes day 29

### Requirement: No live clock; hourly refresh
The dashboard SHALL NOT display a running clock. It SHALL refresh at the top
of each hour (+5 s) and on a button press.

#### Scenario: Hourly schedule
- **WHEN** the local clock reaches the next hour
- **THEN** the dashboard fetches data and performs one full refresh

#### Scenario: Button refresh
- **WHEN** any button press is detected
- **THEN** the page changes and refreshes; the hourly refresh handles the
  current page

### Requirement: Time synchronisation
The dashboard SHALL set its clock from NTP or the weather HTTP `Date` header
and apply the Open-Meteo UTC offset; it SHALL show a no-time state if neither
is available.

#### Scenario: NTP blocked
- **WHEN** NTP times out but the weather request succeeds
- **THEN** the `Date` header anchors the clock and the local date is rendered

### Requirement: On-screen button hints
Every page SHALL show red `<` and `>` glyphs in black-outlined white boxes on
the left edge at the physical KEY0/GP15 and KEY1/GP17 heights.

#### Scenario: Previous hint
- **WHEN** any page is rendered
- **THEN** a `<` hint is drawn at `(0, 181)`–`(11, 196)`, at the bottom of the
  year grid on the dashboard

#### Scenario: Next hint
- **WHEN** any page is rendered
- **THEN** a `>` hint is drawn at `(0, 260)`–`(11, 275)`, at the MAC-row height

#### Scenario: Hint style
- **WHEN** the hints are drawn
- **THEN** the box has a white fill and a 1 px black outline, and the glyph is
  red

#### Scenario: Hints are not touch controls
- **WHEN** the panel is tapped at a hint
- **THEN** no page change occurs; the panel has no touch controller and the
  input is the side switches

### Requirement: No residual year caption
The dashboard SHALL NOT draw the former `3 kolory + raster` / `co godzinę`
caption or its red rule below the year statistics.

#### Scenario: Dashboard composition
- **WHEN** the dashboard is rendered
- **THEN** the area below the day/days-left lines contains no caption text

### Requirement: Polish UI
All on-screen labels, dates and weather descriptions SHALL be Polish and SHALL
render Polish diacritics.

#### Scenario: Font coverage
- **WHEN** the text `Zażółć gęślą jaźń` is rendered on the capabilities page
- **THEN** all glyphs are present and legible
