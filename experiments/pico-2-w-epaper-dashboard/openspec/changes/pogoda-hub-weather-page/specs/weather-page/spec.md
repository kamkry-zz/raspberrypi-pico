## ADDED Requirements

### Requirement: Weather page is the default page
The dashboard SHALL show the Pogoda page first at boot, followed by the
synoptic map page, the KRYSDOM overview, network, capabilities and about.

#### Scenario: Power-up
- **WHEN** the board boots the dashboard
- **THEN** the first frame is the Pogoda page

### Requirement: Weather from pogoda-hub with fallback
The dashboard SHALL fetch weather from `http://pogoda-hub.k3s/v1/weather` and
SHALL fall back to Open-Meteo when the hub cannot be reached.

#### Scenario: Hub down
- **WHEN** the hub request fails
- **THEN** the page is drawn from Open-Meteo data without wind blocks,
  warnings or synop, and the footer credits Open-Meteo only

### Requirement: Weather page content
The Pogoda page SHALL show the current temperature and feels-like, the sun's
progress between today's sunrise and sunset (time to sunrise at night), mean
wind in six 4-hour blocks with direction and the gust maximum, the next 8
hours, IMGW warnings for Łódź (or "no warnings"), the IMGW Łódź synop, and the
next 4 days.

#### Scenario: Active IMGW warning
- **WHEN** the hub reports a warning for TERYT 1061
- **THEN** the info band is red with the event, level, time window and
  probability

### Requirement: Synoptic map page
The dashboard SHALL cache the hub's `/v1/map.bin` on flash, re-download it only
when its ETag changes, and draw it with a Łódź marker, the analysis time and
age, a legend and the IMGW-PIB "dane przetworzone" attribution.

#### Scenario: Map unchanged
- **WHEN** the hourly check sends the cached ETag
- **THEN** the hub answers 304 and the cached file is kept

#### Scenario: No map yet
- **WHEN** no valid map is cached
- **THEN** the page shows "Brak mapy" instead of failing the refresh
