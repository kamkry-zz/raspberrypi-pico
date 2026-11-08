"""OpenTelemetry (OTLP/HTTP JSON) export and a local Prometheus endpoint.

There is no OpenTelemetry SDK for MicroPython, so this module speaks the
OTLP/HTTP JSON wire format directly, following the observatory.k3s contract
for external appliances (same as the HUB75 dashboard):

* push to ``https://otel.k3s`` (``/v1/metrics``, ``/v1/logs``, ``/v1/traces``)
  over one CA-verified TLS connection with HTTP/1.1 keep-alive;
* ``service.name`` becomes the Prometheus ``job`` and the Loki
  ``service_name`` label; ``service.instance.id`` becomes ``instance``;
* metrics are cumulative Sums (counters) and Gauges.

The same metric set is served locally as Prometheus text on
``http://<pico>:9100/metrics`` and a health check on ``/healthz``.

Everything here is best effort: an export failure never raises into the
dashboard loop; queues are bounded and drop the oldest entries.
"""

import gc
import json
import os
import socket
import time

import config

try:
    import ssl
except ImportError:  # pragma: no cover - host tests
    ssl = None

# name -> (unit, kind, description); kind is "gauge" or "sum".
META = {
    "pico.uptime": ("s", "gauge", "Time since boot"),
    "pico.heap.free": ("By", "gauge", "Free MicroPython heap after gc"),
    "pico.heap.used": ("By", "gauge", "Allocated MicroPython heap after gc"),
    "pico.flash.used": ("By", "gauge", "Used LittleFS bytes"),
    "pico.flash.total": ("By", "gauge", "LittleFS size"),
    "pico.cpu.temperature": ("Cel", "gauge", "RP2040 die temperature"),
    "pico.cpu.active": ("1", "gauge", "Share of wall time spent busy (fetch, render, panel)"),
    "pico.cpu.frequency": ("Hz", "gauge", "CPU clock"),
    "pico.wifi.connected": ("1", "gauge", "1 while associated with the WLAN"),
    "pico.wifi.rssi": ("dBm", "gauge", "Received signal strength"),
    "pico.wifi.connects": ("1", "sum", "WLAN connection attempts by result"),
    "pico.boot.info": ("1", "gauge", "Constant 1; boot facts as attributes"),
    "pico.otlp.exports": ("1", "sum", "OTLP export attempts by result"),
    "dashboard.refreshes": ("1", "sum", "Panel refreshes by trigger and result"),
    "dashboard.refresh.duration": ("ms", "gauge", "Last refresh duration by stage"),
    "dashboard.last_refresh.time": ("s", "gauge", "Unix time of the last displayed frame"),
    "dashboard.weather.fetches": ("1", "sum", "Open-Meteo fetches by result"),
    "dashboard.weather.age": ("s", "gauge", "Age of the displayed weather data"),
    "dashboard.page": ("1", "gauge", "Currently displayed page (1-based)"),
    "dashboard.button.presses": ("1", "sum", "Side switch presses by key"),
}

_PROM_UNITS = {
    "s": "seconds",
    "ms": "milliseconds",
    "By": "bytes",
    "Cel": "celsius",
    "Hz": "hertz",
    "dBm": "dBm",
}

MAX_LOGS = 25
MAX_SPANS = 16

_counters = {}  # (name, attrs tuple) -> int
_gauges = {}  # (name, attrs tuple) -> number
_logs = []  # (ticks_ms, severity, text, attrs)
_spans = []  # dicts with ticks-based times
_resource = None
_ca = None
_epoch_fn = None
_start_ms = None  # unix ms of the boot, for cumulative sum start times
_next_export = 0
_backoff_s = 0
_last_export_ok = None
_last_export_error = ""
_server = None
_health_fn = None
collector = None  # callable that refreshes gauges right before use
before_tls = None  # callable: free the heap reserve for the TLS session
after_tls = None  # callable: take the heap reserve back


def _collect():
    if collector is not None:
        try:
            collector()
        except Exception as exc:
            print("telemetry collector:", repr(exc))


# ------------------------------------------------------------------ recording
def _key(name, attrs):
    if not attrs:
        return (name, ())
    return (name, tuple(sorted(attrs.items())))


def inc(name, attrs=None, amount=1):
    key = _key(name, attrs)
    _counters[key] = _counters.get(key, 0) + amount


def gauge(name, value, attrs=None):
    if value is None:
        return
    _gauges[_key(name, attrs)] = value


def log(text, severity="INFO", attrs=None):
    """Print and queue a log record for Loki."""
    print(text)
    if not config.OTLP_ENABLED:
        return
    if len(_logs) >= MAX_LOGS:
        _logs.pop(0)
    _logs.append((time.ticks_ms(), severity, text, attrs))


def _rand_hex(size):
    return "".join("%02x" % b for b in os.urandom(size))


def span(name, start_ticks, end_ticks, attrs=None, error=None, parent=None):
    """Queue a finished span; returns (trace_id, span_id) for children."""
    if not config.OTLP_ENABLED:
        return None
    if parent:
        trace_id = parent[0]
    else:
        trace_id = _rand_hex(16)
    span_id = _rand_hex(8)
    if len(_spans) >= MAX_SPANS:
        _spans.pop(0)
    _spans.append(
        {
            "trace": trace_id,
            "id": span_id,
            "parent": parent[1] if parent else "",
            "name": name,
            "start": start_ticks,
            "end": end_ticks,
            "attrs": attrs,
            "error": error,
        }
    )
    return trace_id, span_id


# ------------------------------------------------------------------ setup
def setup(resource_attrs, epoch_fn, health_fn=None):
    """Load the CA, remember the clock and start the local HTTP endpoint."""
    global _resource, _ca, _epoch_fn, _health_fn
    _resource = resource_attrs
    _epoch_fn = epoch_fn
    _health_fn = health_fn
    if config.OTLP_ENABLED:
        try:
            with open(config.OTLP_CA_FILE, "rb") as handle:
                _ca = handle.read()
        except OSError as exc:
            print("OTLP disabled: CA %s missing (%r)" % (config.OTLP_CA_FILE, exc))
    if config.METRICS_PORT:
        start_server(config.METRICS_PORT)


def _now_ms():
    """Wall-clock unix ms, or None until NTP/HTTP Date set the clock."""
    epoch = _epoch_fn() if _epoch_fn else None
    if epoch is None:
        return None
    return epoch * 1000 + time.ticks_ms() % 1000


def _ticks_to_ms(ticks, now_ms, now_ticks):
    return now_ms - time.ticks_diff(now_ticks, ticks)


def _ns(ms):
    return "%d000000" % ms


# ------------------------------------------------------------------ OTLP JSON
# Payloads are written as JSON text directly: building nested dicts first
# costs ~3x the heap, and the heap is the scarce resource on the Pico W.
_q = json.dumps  # JSON string quoting/escaping


def _value(value):
    if isinstance(value, bool):
        return '{"boolValue":%s}' % ("true" if value else "false")
    if isinstance(value, int):
        return '{"intValue":"%d"}' % value
    if isinstance(value, float):
        return '{"doubleValue":%s}' % _q(value)
    return '{"stringValue":%s}' % _q(str(value))


def _attrs(items):
    if not items:
        return "[]"
    if isinstance(items, dict):
        items = items.items()
    return "[" + ",".join('{"key":%s,"value":%s}' % (_q(k), _value(v)) for k, v in items) + "]"


def _resource_json():
    return '{"attributes":%s}' % _attrs(_resource or {})


def _scope():
    return '{"name":"pico-epaper-dashboard","version":%s}' % _q(config.VERSION)


def _point(attrs, value, now_ms, start_ms=None):
    if isinstance(value, float):
        number = '"asDouble":%s' % _q(value)
    else:
        number = '"asInt":"%d"' % int(value)
    start = ',"startTimeUnixNano":"%s"' % _ns(start_ms) if start_ms is not None else ""
    return '{"timeUnixNano":"%s"%s,"attributes":%s,%s}' % (_ns(now_ms), start, _attrs(attrs), number)


def _grouped():
    """Return {name: [(attrs tuple, value), ...]} for counters and gauges."""
    grouped = {}
    for store in (_gauges, _counters):
        for (name, attrs), value in store.items():
            grouped.setdefault(name, []).append((attrs, value))
    return grouped


def metrics_payload(now_ms, start_ms):
    parts = []
    for name, points in _grouped().items():
        unit, kind, description = META.get(name, ("1", "gauge", ""))
        if kind == "sum":
            data = '"sum":{"aggregationTemporality":2,"isMonotonic":true,"dataPoints":[%s]}' % ",".join(
                _point(a, v, now_ms, start_ms) for a, v in points
            )
        else:
            data = '"gauge":{"dataPoints":[%s]}' % ",".join(_point(a, v, now_ms) for a, v in points)
        parts.append('{"name":%s,"unit":%s,"description":%s,%s}' % (_q(name), _q(unit), _q(description), data))
    return '{"resourceMetrics":[{"resource":%s,"scopeMetrics":[{"scope":%s,"metrics":[%s]}]}]}' % (
        _resource_json(),
        _scope(),
        ",".join(parts),
    )


_SEVERITY = {"DEBUG": 5, "INFO": 9, "WARN": 13, "ERROR": 17, "FATAL": 21}


def logs_payload(records, now_ms, now_ticks):
    parts = []
    for ticks, severity, text, attrs in records:
        stamp = _ns(_ticks_to_ms(ticks, now_ms, now_ticks))
        parts.append(
            '{"timeUnixNano":"%s","observedTimeUnixNano":"%s","severityNumber":%d,'
            '"severityText":%s,"body":{"stringValue":%s},"attributes":%s}'
            % (stamp, stamp, _SEVERITY.get(severity, 9), _q(severity), _q(text), _attrs(attrs))
        )
    return '{"resourceLogs":[{"resource":%s,"scopeLogs":[{"scope":%s,"logRecords":[%s]}]}]}' % (
        _resource_json(),
        _scope(),
        ",".join(parts),
    )


def traces_payload(spans, now_ms, now_ticks):
    parts = []
    for item in spans:
        if item["error"]:
            status = '{"code":2,"message":%s}' % _q(item["error"])
        else:
            status = '{"code":1}'
        parent = ',"parentSpanId":"%s"' % item["parent"] if item["parent"] else ""
        parts.append(
            '{"traceId":"%s","spanId":"%s"%s,"name":%s,"kind":1,"startTimeUnixNano":"%s",'
            '"endTimeUnixNano":"%s","attributes":%s,"status":%s}'
            % (
                item["trace"],
                item["id"],
                parent,
                _q(item["name"]),
                _ns(_ticks_to_ms(item["start"], now_ms, now_ticks)),
                _ns(_ticks_to_ms(item["end"], now_ms, now_ticks)),
                _attrs(item["attrs"]),
                status,
            )
        )
    return '{"resourceSpans":[{"resource":%s,"scopeSpans":[{"scope":%s,"spans":[%s]}]}]}' % (
        _resource_json(),
        _scope(),
        ",".join(parts),
    )


# ------------------------------------------------------------------ transport
def _read_response(sock):
    """Read one HTTP/1.1 response without reading past it (keep-alive).

    MicroPython stream ``read(n)`` blocks until all n bytes arrive, so the
    header is read line by line and the body by exact Content-Length.
    """
    status_line = sock.readline()
    if not status_line:
        raise OSError("connection closed")
    status = int(status_line.split()[1])
    length = 0
    close = False
    for _ in range(64):
        line = sock.readline()
        if not line or line == b"\r\n":
            break
        lower = line.lower()
        if lower.startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1])
        elif lower.startswith(b"connection:") and b"close" in lower:
            close = True
    while length > 0:
        chunk = sock.read(min(512, length))
        if not chunk:
            break
        length -= len(chunk)
    return status, close


def _post_all(requests):
    """POST every (path, body) over one TLS connection.  Returns ok count."""
    host = config.OTLP_HOST
    gc.collect()
    address = socket.getaddrinfo(host, 443)[0][-1]
    raw = socket.socket()
    raw.settimeout(config.OTLP_TIMEOUT_S)
    sock = raw
    sent = 0
    try:
        raw.connect(address)
        gc.collect()
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.load_verify_locations(cadata=_ca)
        sock = ctx.wrap_socket(raw, server_hostname=host)
        for index, (path, body) in enumerate(requests):
            last = index == len(requests) - 1
            sock.write(
                b"POST %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: %s\r\n"
                b"Content-Type: application/json\r\nContent-Length: %d\r\n"
                b"Connection: %s\r\n\r\n"
                % (
                    path,
                    host.encode(),
                    config.USER_AGENT.encode(),
                    len(body),
                    b"close" if last else b"keep-alive",
                )
            )
            sock.write(body)
            status, close = _read_response(sock)
            if status // 100 != 2:
                raise OSError("HTTP %d on %s" % (status, path.decode()))
            sent += 1
            if close and not last:
                raise OSError("server closed keep-alive")
        return sent
    finally:
        try:
            sock.close()
        except Exception:
            pass
        gc.collect()


def export_due():
    return (
        config.OTLP_ENABLED
        and _ca is not None
        and time.ticks_diff(time.ticks_ms(), _next_export) >= 0
    )


def export(force=False):
    """Push metrics, then queued logs and spans.  Never raises."""
    global _next_export, _backoff_s, _last_export_ok, _last_export_error, _start_ms
    if not config.OTLP_ENABLED or _ca is None or ssl is None:
        return False
    if not force and time.ticks_diff(time.ticks_ms(), _next_export) < 0:
        return False
    now_ms = _now_ms()
    if now_ms is None:
        # No wall clock yet: retry soon, keep the queues.
        _next_export = time.ticks_add(time.ticks_ms(), 30000)
        return False
    if _start_ms is None:
        _start_ms = now_ms  # start of the cumulative counters

    _collect()
    now_ticks = time.ticks_ms()
    logs = _logs[:]
    spans = _spans[:]
    started = time.ticks_ms()
    # Borrow the big heap block for payload building *and* the TLS session.
    if before_tls:
        before_tls()
    try:
        gc.collect()
        heap_lent = gc.mem_free()
        try:
            requests = [(b"/v1/metrics", metrics_payload(now_ms, _start_ms).encode())]
            if logs:
                requests.append((b"/v1/logs", logs_payload(logs, now_ms, now_ticks).encode()))
            if spans:
                requests.append(
                    (b"/v1/traces", traces_payload(spans, now_ms, now_ticks).encode())
                )
            count = len(requests)
            sent = _post_all(requests)
        finally:
            requests = None
            if after_tls:
                after_tls()
        # Drop only what was delivered; new records may have arrived meanwhile.
        if sent >= 2 and logs:
            del _logs[: len(logs)]
        if sent >= count and spans:
            del _spans[: len(spans)]
        inc("pico.otlp.exports", {"result": "ok"})
        _backoff_s = 0
        _last_export_ok = now_ms // 1000
        _last_export_error = ""
        _next_export = time.ticks_add(time.ticks_ms(), config.OTLP_INTERVAL_S * 1000)
        print("OTLP: %d request(s) in %d ms" % (sent, time.ticks_diff(time.ticks_ms(), started)))
        return True
    except Exception as exc:
        inc("pico.otlp.exports", {"result": "error"})
        _backoff_s = min(max(_backoff_s * 2, config.OTLP_INTERVAL_S), 600)
        _last_export_error = repr(exc)
        _next_export = time.ticks_add(time.ticks_ms(), _backoff_s * 1000)
        print("OTLP export failed (%r); retry in %d s" % (exc, _backoff_s))
        try:
            print("  heap free when lent: %d" % heap_lent)
        except NameError:
            pass
        return False
    finally:
        gc.collect()


def status():
    return {
        "otlp_enabled": bool(config.OTLP_ENABLED and _ca is not None),
        "last_export_ok": _last_export_ok,
        "last_export_error": _last_export_error,
        "queued_logs": len(_logs),
        "queued_spans": len(_spans),
    }


# ------------------------------------------------------------------ Prometheus
def prom_name(name, unit, kind):
    base = name.replace(".", "_")
    suffix = _PROM_UNITS.get(unit)
    if suffix and not base.endswith("_" + suffix):
        base += "_" + suffix
    elif unit == "1" and kind == "gauge" and name in ("pico.cpu.active",):
        base += "_ratio"
    if kind == "sum":
        base += "_total"
    return base


def _escape(value):
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def prometheus_text():
    lines = []
    for name, points in sorted(_grouped().items()):
        unit, kind, description = META.get(name, ("1", "gauge", ""))
        metric = prom_name(name, unit, kind)
        lines.append("# HELP %s %s" % (metric, description))
        lines.append("# TYPE %s %s" % (metric, "counter" if kind == "sum" else "gauge"))
        for attrs, value in points:
            labels = ",".join('%s="%s"' % (k.replace(".", "_"), _escape(v)) for k, v in attrs)
            lines.append("%s%s %s" % (metric, "{%s}" % labels if labels else "", value))
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ local HTTP
def start_server(port):
    global _server
    try:
        server = socket.socket()
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(socket.getaddrinfo("0.0.0.0", port)[0][-1])
        server.listen(2)
        server.setblocking(False)
        _server = server
        print("Metrics endpoint on :%d (/metrics, /healthz)" % port)
    except Exception as exc:
        print("Metrics endpoint failed:", repr(exc))
        _server = None


def poll():
    """Serve at most one pending HTTP request without blocking."""
    if _server is None:
        return
    try:
        client, _ = _server.accept()
    except OSError:
        return
    try:
        client.settimeout(2)
        request = client.recv(512)
        path = b"/"
        parts = request.split(b" ", 2)
        if len(parts) >= 2:
            path = parts[1]
        if path.startswith(b"/metrics"):
            _collect()
            code, ctype, body = 200, "text/plain; version=0.0.4", prometheus_text()
        elif path.startswith(b"/healthz"):
            healthy, detail = _health_fn() if _health_fn else (True, {})
            detail.update(status())
            code = 200 if healthy else 503
            ctype, body = "application/json", json.dumps(detail)
        else:
            code, ctype, body = 404, "text/plain", "not found\n"
        body = body.encode()
        client.send(
            b"HTTP/1.0 %d %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
            b"Connection: close\r\n\r\n"
            % (code, b"OK" if code == 200 else b"ERR", ctype.encode(), len(body))
        )
        view = memoryview(body)
        while view:
            written = client.send(view[:1024])
            view = view[written:]
    except Exception as exc:
        print("HTTP serve:", repr(exc))
    finally:
        client.close()
