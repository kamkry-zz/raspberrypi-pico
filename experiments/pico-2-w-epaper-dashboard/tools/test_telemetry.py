import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "lib"))

import store  # noqa: E402
import telemetry  # noqa: E402


class _HostTime:
    """MicroPython's ticks API on CPython (no wrap-around needed in tests)."""

    def __getattr__(self, name):
        import time

        return getattr(time, name)

    @staticmethod
    def ticks_diff(a, b):
        return a - b


telemetry.time = _HostTime()


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "weather.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_round_trip_and_atomic_replace(self):
        self.assertTrue(store.save(self.path, {"a": 1}))
        self.assertTrue(store.save(self.path, {"a": 2, "s": "Dziś"}))
        self.assertEqual(store.load(self.path), {"a": 2, "s": "Dziś"})
        self.assertFalse(os.path.exists(self.path + ".tmp"))

    def test_missing_returns_default(self):
        self.assertEqual(store.load(self.path, "x"), "x")

    def test_truncated_file_is_removed(self):
        with open(self.path, "w") as handle:
            handle.write('{"current": {"temp": 1')  # power cut mid-write
        self.assertIsNone(store.load(self.path))
        self.assertFalse(os.path.exists(self.path))

    def test_recovers_tmp_after_cut_between_remove_and_rename(self):
        with open(self.path + ".tmp", "w") as handle:
            json.dump({"ok": True}, handle)
        self.assertEqual(store.load(self.path), {"ok": True})
        self.assertTrue(os.path.exists(self.path))


class TelemetryTest(unittest.TestCase):
    def setUp(self):
        telemetry._counters.clear()
        telemetry._gauges.clear()
        telemetry._resource = {"service.name": "pico-epaper-dashboard"}

    def test_metrics_payload_shapes(self):
        telemetry.inc("dashboard.refreshes", {"trigger": "boot", "result": "ok"})
        telemetry.inc("dashboard.refreshes", {"trigger": "boot", "result": "ok"})
        telemetry.gauge("pico.heap.free", 1234)
        telemetry.gauge("pico.cpu.temperature", 21.5)
        body = json.loads(telemetry.metrics_payload(1794143358123, 1794140000000))
        rm = body["resourceMetrics"][0]
        self.assertEqual(
            rm["resource"]["attributes"][0],
            {"key": "service.name", "value": {"stringValue": "pico-epaper-dashboard"}},
        )
        metrics = {m["name"]: m for m in rm["scopeMetrics"][0]["metrics"]}
        refresh = metrics["dashboard.refreshes"]["sum"]
        self.assertTrue(refresh["isMonotonic"])
        self.assertEqual(refresh["aggregationTemporality"], 2)
        point = refresh["dataPoints"][0]
        self.assertEqual(point["asInt"], "2")
        self.assertEqual(point["timeUnixNano"], "1794143358123000000")
        self.assertEqual(point["startTimeUnixNano"], "1794140000000000000")
        temp = metrics["pico.cpu.temperature"]["gauge"]["dataPoints"][0]
        self.assertEqual(temp["asDouble"], 21.5)
        self.assertEqual(metrics["pico.heap.free"]["unit"], "By")

    def test_logs_and_traces_are_valid_json(self):
        logs = json.loads(
            telemetry.logs_payload([(1000, "WARN", 'quote " and Łódź', {"event": "boot"})], 5000000, 2000)
        )
        record = logs["resourceLogs"][0]["scopeLogs"][0]["logRecords"][0]
        self.assertEqual(record["timeUnixNano"], "4999000000000")  # 1 s before "now"
        self.assertEqual(record["body"]["stringValue"], 'quote " and Łódź')
        self.assertEqual(record["severityNumber"], 13)
        spans = [
            {"trace": "a" * 32, "id": "b" * 16, "parent": "", "name": "dashboard.refresh",
             "start": 0, "end": 1500, "attrs": {"result": "ok", "page": 1, "wifi": True}, "error": None},
            {"trace": "a" * 32, "id": "c" * 16, "parent": "b" * 16, "name": "epaper.display",
             "start": 100, "end": 1500, "attrs": None, "error": "offline"},
        ]
        traces = json.loads(telemetry.traces_payload(spans, 10000, 1500))
        out = traces["resourceSpans"][0]["scopeSpans"][0]["spans"]
        self.assertEqual(out[0]["endTimeUnixNano"], "10000000000")
        self.assertNotIn("parentSpanId", out[0])
        self.assertEqual(out[1]["parentSpanId"], "b" * 16)
        self.assertEqual(out[1]["status"], {"code": 2, "message": "offline"})
        self.assertEqual(out[0]["attributes"][2]["value"], {"boolValue": True})

    def test_read_response_stops_at_body_end(self):
        import io

        stream = io.BytesIO(
            b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 21\r\n\r\n"
            b'{"partialSuccess":{}}'
            b"HTTP/1.1 400 Bad Request\r\nConnection: close\r\nContent-Length: 2\r\n\r\nno"
        )
        self.assertEqual(telemetry._read_response(stream), (200, False))
        self.assertEqual(telemetry._read_response(stream), (400, True))
        self.assertEqual(stream.read(), b"")

    def test_prometheus_names(self):
        self.assertEqual(telemetry.prom_name("pico.heap.free", "By", "gauge"), "pico_heap_free_bytes")
        self.assertEqual(telemetry.prom_name("pico.uptime", "s", "gauge"), "pico_uptime_seconds")
        self.assertEqual(telemetry.prom_name("dashboard.refreshes", "1", "sum"), "dashboard_refreshes_total")
        self.assertEqual(telemetry.prom_name("pico.cpu.active", "1", "gauge"), "pico_cpu_active_ratio")

    def test_prometheus_text(self):
        telemetry.inc("pico.wifi.connects", {"result": "ok"})
        telemetry.gauge("pico.boot.info", 1, {"reset_cause": "WDT", "version": '0"2'})
        text = telemetry.prometheus_text()
        self.assertIn("# TYPE pico_wifi_connects_total counter", text)
        self.assertIn('pico_wifi_connects_total{result="ok"} 1', text)
        self.assertIn('reset_cause="WDT"', text)
        self.assertIn('version="0\\"2"', text)


if __name__ == "__main__":
    unittest.main()
