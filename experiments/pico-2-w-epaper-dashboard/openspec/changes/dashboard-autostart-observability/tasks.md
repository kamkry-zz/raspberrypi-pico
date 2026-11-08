## 1. Autostart and resilience

- [x] 1.1 Add `lib/supervisor.py` (heartbeat-gated WDT, maintenance mode, crash backoff, reset tags).
- [x] 1.2 Move the app into `lib/app.py`; make `main.py` a shim.
- [x] 1.3 Start Wi-Fi during the panel clear; radio re-init and reboot thresholds; offline retry with backoff without redraws.
- [x] 1.4 Persist last good weather atomically; show it stale at boot when offline.
- [x] 1.5 RTC from HTTP `Date` when NTP fails; e-paper BUSY timeout.
- [x] 1.6 Verify on hardware: watchdog trip resets a stalled app (reset cause WDT).
- [x] 1.7 Verify on hardware: Ctrl-C reboots into one maintenance boot.
- [ ] 1.8 Verify on hardware: physical power cycle resumes with a fresh frame (user unplugs/replugs).

## 2. Build and deploy

- [x] 2.1 `tools/build.py` precompiles `lib/` with mpy-cross 1.23.0 into `build/`.
- [x] 2.2 `tools/deploy.sh`: maintenance entry, verified `:main.py` backup, copy, tagged reset.
- [x] 2.3 Back up and remove unused board `/lib` packages (flash was full).
- [x] 2.4 Install on the board; dashboard boots from flash (`reset_cause=DEPLOY`, first frame ~36 s).

## 3. Observability

- [x] 3.1 `/metrics` (Prometheus text) and `/healthz` on :9100, served during panel waits.
- [x] 3.2 OTLP/HTTP JSON exporter (metrics, logs, traces), CA-verified; host tests.
- [x] 3.3 Measure TLS heap on hardware; disable OTLP by default (fragmentation, see design).
- [ ] 3.4 Deliver the `pico-epaper-dashboard` scrape job in krysdom-api/observability (PR #1928, checks green); verify `up` = 1 after merge.
- [x] 3.5 Frozen-module firmware (`firmware/`): built in Docker, flashed; heap free 60 KB → 113 KB.
- [x] 3.6 Fix the OTLP keep-alive response reader; trial run delivers metrics, logs and traces; series visible in Prometheus.
- [ ] 3.7 Enable OTLP (deferred by the user); retire the scrape job at the same time.
