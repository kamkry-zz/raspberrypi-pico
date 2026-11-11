"""Dashboard application: boot supervisor wiring, refresh loop, telemetry.

Entry point is :func:`boot`, called by the tiny ``main.py`` shim so that this
module can be shipped precompiled (``.mpy``) and spare the heap.
"""

import gc
import sys
import time

import config
import supervisor


def _boot_facts():
    import os

    import metrics

    return {
        "reset_cause": metrics.reset_cause(),
        "crash_count": supervisor.crash_count(),
        "firmware": os.uname().release,
        "version": config.VERSION,
        # "1" when lib/ is compiled into the firmware (firmware/build.sh).
        # Frozen modules report a bare name ("app.py"); files have a path.
        "frozen": "0" if "/" in __file__ else "1",
    }


def main():
    print("Pico e-paper dashboard", config.VERSION)
    # Allocate the two contiguous 15 KB canvas planes FIRST: compiling the
    # other modules, the panel clear and the network stack fragment the heap.
    gc.collect()
    from canvas import Canvas

    canvas = Canvas(config.WIDTH, config.HEIGHT)
    gc.collect()
    # Next, a contiguous block kept free for TLS/HTTP (see supervisor).
    supervisor.reserve(config.HEAP_RESERVE)

    import metrics
    import net
    import telemetry
    import timeutil as T
    import weather
    from buttons import Buttons
    from clock import Clock
    from epd42b import EPD42B
    from pages import PAGES

    gc.collect()
    page_count = len(PAGES)
    facts = _boot_facts()
    print("Heap free after imports:", gc.mem_free(), "reserve held:", supervisor.reserve())

    clock = Clock()
    state = {
        "page": 0,
        "last_frame_ticks": None,
        "last_frame_epoch": None,
        "last_result": "boot",
        "retry_index": 0,
        "consecutive_errors": 0,
    }
    panel_ref = [None]
    info_cache = [{}]

    # ---------------------------------------------------------------- telemetry
    def collect_gauges():
        m = metrics.gather(panel_ref[0])
        info = net.info()
        info_cache[0] = info
        telemetry.gauge("pico.uptime", m["uptime_s"])
        telemetry.gauge("pico.heap.used", m["heap_used"])
        telemetry.gauge("pico.heap.free", m["heap_total"] - m["heap_used"])
        telemetry.gauge("pico.flash.used", m["flash_used"])
        telemetry.gauge("pico.flash.total", m["flash_total"])
        telemetry.gauge("pico.cpu.temperature", round(m["temp_c"], 1))
        telemetry.gauge("pico.cpu.active", round(m["active_pct"] / 100.0, 4))
        telemetry.gauge("pico.cpu.frequency", m["freq_mhz"] * 1000000)
        telemetry.gauge("pico.wifi.connected", 1 if info.get("connected") else 0)
        if info.get("rssi") is not None:
            telemetry.gauge("pico.wifi.rssi", info["rssi"])
        telemetry.gauge("pico.boot.info", 1, facts)
        telemetry.gauge("dashboard.page", state["page"] + 1)
        if state["last_frame_epoch"]:
            telemetry.gauge("dashboard.last_refresh.time", state["last_frame_epoch"])
        current = weather.cached()
        now = clock.epoch()
        if current and current.get("fetched") and now:
            telemetry.gauge("dashboard.weather.age", max(0, now - current["fetched"]))

    def health():
        age = None
        if state["last_frame_ticks"] is not None:
            age = time.ticks_diff(time.ticks_ms(), state["last_frame_ticks"]) // 1000
        uptime = metrics.uptime_s()
        fresh = age is not None and age < config.HEALTH_MAX_FRAME_AGE_S
        booting = age is None and uptime < 300
        healthy = fresh or booting
        return healthy, {
            "status": "ok" if healthy else "stale",
            "version": config.VERSION,
            "uptime_s": uptime,
            "frame_age_s": age,
            "last_result": state["last_result"],
            "wifi": net.is_connected(),
            "time_synced": clock.synced(),
            "reset_cause": facts["reset_cause"],
        }

    def idle():
        supervisor.beat()
        telemetry.poll()

    def fetch_weather(force):
        # Hand the contiguous reserve to the HTTP body/JSON parse, then
        # take it back so later allocations cannot fragment it.
        supervisor.release()
        try:
            return weather.fetch(force=force)
        finally:
            supervisor.reserve()

    telemetry.collector = collect_gauges
    telemetry.before_tls = supervisor.release
    telemetry.after_tls = supervisor.reserve
    telemetry.setup(
        {
            "service.name": config.OTEL_SERVICE_NAME,
            "service.instance.id": config.OTEL_INSTANCE,
            "service.version": config.VERSION,
            "host.name": config.OTEL_INSTANCE,
            "device.id": net.mac_address(),
            "device.model.name": sys.implementation._machine.split(" with ")[0],
            "pico.firmware.version": facts["firmware"],
        },
        clock.epoch,
        health,
    )
    telemetry.log(
        "Boot %s: reset=%s crashes=%d fw=%s"
        % (config.VERSION, facts["reset_cause"], facts["crash_count"], facts["firmware"]),
        "WARN" if facts["reset_cause"] == "WDT" or facts["crash_count"] else "INFO",
        {"event": "boot", "reset_cause": facts["reset_cause"]},
    )

    # Last good weather from flash: shown (as stale) if the network is down.
    weather.load_persisted()
    # Associate in the background while the panel clears.
    net.begin()

    print("Panel init + vendor clear (about 24 s)...")
    panel = EPD42B(idle=idle)
    panel_ref[0] = panel
    print("Panel:", panel.revision, "init", panel.last_init_ms, "clear", panel.last_total_ms)
    supervisor.beat()

    buttons = Buttons(
        (config.PIN_KEY_PREV, config.PIN_KEY_NEXT),
        config.BUTTON_DEBOUNCE_MS,
        config.BUTTON_LONG_PRESS_MS,
    )

    # ---------------------------------------------------------------- refresh
    def build_data(force_weather, timeout_ms):
        gc.collect()
        wifi_ok = net.ensure(timeout_ms)
        supervisor.beat()
        info = net.info()
        if wifi_ok and info.get("ip") not in (None, "—", "0.0.0.0"):
            name, verified, source = net.resolve_dns_name(info["ip"], config.DNS_NAME)
        else:
            name, verified, source = None, False, None
        info["dns_name"] = name
        info["dns_ok"] = verified
        info["dns_source"] = source

        http_started = time.ticks_ms()
        if wifi_ok:
            current_weather = fetch_weather(force_weather)
        else:
            current_weather = weather.cached()
            if current_weather is not None:
                current_weather["stale"] = True
        if wifi_ok:
            # Synoptic map: streamed to flash, at most every MAP_CHECK_MINUTES,
            # usually a 304.  Never fatal for the frame.
            try:
                import synmap

                synmap.fetch(force=force_weather)
            except Exception as exc:
                telemetry.log("Map refresh error: %r" % (exc,), "WARN")
        info["http_ms"] = time.ticks_diff(time.ticks_ms(), http_started)
        supervisor.beat()

        if wifi_ok and not clock.synced():
            epoch = net.ntp_sync()
            if epoch:
                clock.set(epoch, T.eu_offset(epoch))

        if current_weather and current_weather.get("date_epoch") and not current_weather.get("stale"):
            if force_weather or not clock.synced():
                clock.set(current_weather["date_epoch"], current_weather.get("offset_s"))
                if not net.ntp_ok:
                    # TLS certificate checks use the RTC: keep it right even
                    # when NTP is blocked or down.
                    net.set_rtc(current_weather["date_epoch"])
            else:
                clock.set_offset(current_weather.get("offset_s"))

        return {
            "now": clock.now(),
            "now_epoch": clock.epoch(),
            "time_synced": clock.synced(),
            "offline": (not wifi_ok) or (current_weather is None),
            "page": 0,
            "pages": page_count,
            "weather": current_weather,
            "net": info,
            "metrics": metrics.gather(panel),
        }, wifi_ok

    def refresh(trigger, force_weather, timeout_ms):
        t0 = time.ticks_ms()
        data, wifi_ok = build_data(force_weather, timeout_ms)
        t1 = time.ticks_ms()
        data["page"] = state["page"]
        PAGES[state["page"]](canvas, data)
        t2 = time.ticks_ms()
        gc.collect()
        supervisor.beat()
        panel.display(canvas.black, canvas.red)
        t3 = time.ticks_ms()
        supervisor.beat()

        current = data["weather"]
        if data["offline"]:
            result = "offline"
        elif (current and current.get("stale")) or not data["time_synced"]:
            result = "degraded"
        else:
            result = "ok"
        state["last_result"] = result
        state["last_frame_ticks"] = t3
        state["last_frame_epoch"] = clock.epoch()

        fetch_ms = time.ticks_diff(t1, t0)
        render_ms = time.ticks_diff(t2, t1)
        panel_ms = time.ticks_diff(t3, t2)
        metrics.mark_active(fetch_ms + render_ms + panel_ms)
        telemetry.inc("dashboard.refreshes", {"trigger": trigger, "result": result})
        telemetry.gauge("dashboard.refresh.duration", fetch_ms, {"stage": "fetch"})
        telemetry.gauge("dashboard.refresh.duration", render_ms, {"stage": "render"})
        telemetry.gauge("dashboard.refresh.duration", panel_ms, {"stage": "panel"})
        root = telemetry.span(
            "dashboard.refresh",
            t0,
            t3,
            {"trigger": trigger, "result": result, "page": state["page"] + 1},
            None if result == "ok" else result,
        )
        telemetry.span("dashboard.fetch", t0, t1, {"wifi.connected": wifi_ok}, None, root)
        telemetry.span("dashboard.render", t1, t2, None, None, root)
        telemetry.span("epaper.display", t2, t3, {"epaper.revision": panel.revision}, None, root)
        telemetry.log(
            "Refresh %s/%s page %d: fetch %d ms, render %d ms, panel %d ms"
            % (trigger, result, state["page"] + 1, fetch_ms, render_ms, panel_ms),
            "INFO" if result == "ok" else "WARN",
            {"event": "refresh", "trigger": trigger, "result": result},
        )
        return result

    def schedule_next():
        now = clock.now()
        if config.REFRESH_AT_TOP_OF_HOUR and now:
            return time.ticks_add(time.ticks_ms(), T.seconds_to_next_hour(now) * 1000 + 5000)
        return time.ticks_add(time.ticks_ms(), config.REFRESH_MINUTES * 60 * 1000)

    def schedule_retry(result):
        if result == "ok":
            state["retry_index"] = 0
            return None
        delays = config.RETRY_BACKOFF_S
        delay = delays[min(state["retry_index"], len(delays) - 1)]
        state["retry_index"] += 1
        print("Not fully online (%s); network retry in %d s" % (result, delay))
        return time.ticks_add(time.ticks_ms(), delay * 1000)

    # ---------------------------------------------------------------- first frame
    print("Gathering first data...")
    result = refresh("boot", True, 30000)
    metrics.reset_interval()
    supervisor.clear_crashes()  # a frame made it to the panel
    telemetry.export(force=True)
    if config.RUN_ONCE:
        print("RUN_ONCE: first frame displayed; panel keeps the image")
        return

    next_refresh = schedule_next()
    next_retry = schedule_retry(result)
    cleared_day = None

    while True:
        supervisor.beat()
        try:
            event = buttons.poll()
            if event:
                kind, index = event
                state["page"] = (state["page"] + (-1 if index == 0 else 1)) % page_count
                telemetry.inc("dashboard.button.presses", {"key": "KEY%d" % index})
                print("Button:", kind, index, "-> page", state["page"] + 1)
                result = refresh("button", False, 8000)
                next_refresh = schedule_next()
                if result != "ok" and next_retry is None:
                    next_retry = schedule_retry(result)

            if next_retry is not None and time.ticks_diff(time.ticks_ms(), next_retry) >= 0:
                # Probe the network first; only redraw once data improves, so an
                # outage does not cost a 23 s full refresh every few minutes.
                fresh = False
                if net.ensure(15000):
                    fresh = (fetch_weather(True) or {}).get("stale") is False
                if fresh:
                    result = refresh("retry", False, 8000)
                    next_refresh = schedule_next()
                    next_retry = schedule_retry(result)
                else:
                    next_retry = schedule_retry("offline")
                    if net.fails >= config.WIFI_REBOOT_AFTER_FAILS:
                        telemetry.log("WiFi down after %d attempts; rebooting" % net.fails, "ERROR")
                        supervisor.reset("WIFI")

            if time.ticks_diff(time.ticks_ms(), next_refresh) >= 0:
                now = clock.now()
                if (
                    config.NIGHTLY_CLEAR
                    and now
                    and now[3] == config.NIGHTLY_CLEAR_HOUR
                    and now[4] == 0
                    and cleared_day != (now[0], now[1], now[2])
                ):
                    cleared_day = (now[0], now[1], now[2])
                    print("Nightly clear")
                    panel.clear()
                    metrics.mark_active(panel.last_total_ms)

                result = refresh("hourly", True, 20000)
                next_refresh = schedule_next()
                next_retry = schedule_retry(result)

            if telemetry.export_due() and info_cache[0].get("connected", True):
                telemetry.export()

            telemetry.poll()
            state["consecutive_errors"] = 0
            time.sleep_ms(100)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            state["consecutive_errors"] += 1
            telemetry.log("Refresh error: %r" % (exc,), "ERROR", {"event": "error"})
            if state["consecutive_errors"] >= 5:
                raise
            next_refresh = time.ticks_add(time.ticks_ms(), 60000)
            time.sleep_ms(1000)


def boot():
    supervisor.take_reset_tag()
    reason = supervisor.maintenance_requested(config.PIN_KEY_PREV)
    if reason:
        print("Maintenance mode (%s): dashboard not started, no watchdog." % reason)
        print("REPL is free for mpremote. Reset or power-cycle to resume.")
        return
    if config.WATCHDOG_ENABLED and not config.RUN_ONCE:
        supervisor.start(config.WATCHDOG_STALL_S * 1000)
    try:
        main()
    except KeyboardInterrupt:
        if supervisor.armed():
            # The armed watchdog would reset an idle REPL; reboot cleanly
            # into one maintenance boot instead.
            supervisor.enter_maintenance()
        print("Interrupted")
    except Exception as exc:
        sys.print_exception(exc)
        try:
            import telemetry

            telemetry.log("FATAL: %r" % (exc,), "FATAL", {"event": "fatal"})
            telemetry.export(force=True)
        except Exception:
            pass
        try:
            supervisor.crash_reset(repr(exc))
        except KeyboardInterrupt:
            supervisor.enter_maintenance()

