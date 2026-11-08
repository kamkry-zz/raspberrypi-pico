## ADDED Requirements

### Requirement: Prometheus metrics endpoint
The board SHALL serve Prometheus text metrics on `:9100/metrics`, including
uptime, heap, flash, CPU temperature and activity, Wi-Fi state and RSSI,
boot facts (reset cause, crash count, versions) and refresh counters and
durations.

#### Scenario: Scrape during a panel refresh
- **WHEN** a scrape arrives while the panel is refreshing
- **THEN** it is answered from the panel wait loop

### Requirement: Health check
The board SHALL serve `/healthz`, returning 200 while a frame was displayed
within `HEALTH_MAX_FRAME_AGE_S` (or during the first 5 minutes of boot) and
503 otherwise.

#### Scenario: Stale display
- **WHEN** no frame has been displayed for more than two hours
- **THEN** `/healthz` returns 503 with `"status": "stale"`

### Requirement: Optional OTLP export
When `OTLP_ENABLED` is set, the board SHALL push OTLP/HTTP JSON metrics, logs
and refresh traces to `https://otel.k3s` with certificate verification against
the krysdom CA, with `service.name=pico-epaper-dashboard`.

#### Scenario: Export failure
- **WHEN** an export fails
- **THEN** the dashboard keeps running and the export backs off up to 10 min
