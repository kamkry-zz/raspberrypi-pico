"""Wi-Fi, status, DNS PTR discovery and NTP helpers."""

import gc
import socket
import time

import network

import config

try:
    from secrets import WIFI_PASSWORD
except ImportError:
    WIFI_PASSWORD = None

_wlan = None


def _ensure_wlan():
    global _wlan
    if _wlan is None:
        _wlan = network.WLAN(network.STA_IF)
        _wlan.active(True)
    return _wlan


def _status_name(status):
    for name, label in (
        ("STAT_IDLE", "bezczynny"),
        ("STAT_CONNECTING", "łączenie"),
        ("STAT_WRONG_PASSWORD", "błędne hasło"),
        ("STAT_NO_AP_FOUND", "brak sieci"),
        ("STAT_CONNECT_FAIL", "błąd połączenia"),
        ("STAT_GOT_IP", "połączono"),
    ):
        value = getattr(network, name, None)
        if value is not None and status == value:
            return label
    return str(status)


def status_name():
    if _wlan is None:
        return "brak"
    try:
        return _status_name(_wlan.status())
    except Exception:
        return "?"


def mac_address():
    wlan = _ensure_wlan()
    try:
        mac = wlan.config("mac")
        return ":".join("%02x" % value for value in mac)
    except Exception:
        return "—"


def connect(timeout_ms=20000):
    global _wlan
    if not WIFI_PASSWORD or WIFI_PASSWORD == "CHANGE_ME":
        print("WiFi: secrets.py is missing or still contains CHANGE_ME")
        return False

    try:
        network.country(config.WIFI_COUNTRY)
    except Exception:
        pass
    try:
        network.hostname(config.HOSTNAME)
    except Exception as exc:
        print("WiFi hostname:", exc)

    _wlan = network.WLAN(network.STA_IF)
    _wlan.active(True)
    try:
        _wlan.config(pm=0)  # disable power save
    except Exception:
        pass

    if not _wlan.isconnected():
        print("WiFi: connecting to", config.WIFI_SSID)
        try:
            _wlan.connect(config.WIFI_SSID, WIFI_PASSWORD)
        except Exception as exc:
            print("WiFi connect error:", exc)
            return False
        started = time.ticks_ms()
        while not _wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), started) > timeout_ms:
                print("WiFi: timeout, status", status_name())
                return False
            time.sleep_ms(200)

    print("WiFi: connected", _wlan.ifconfig()[0])
    return True


def ensure(timeout_ms=20000):
    if _wlan is not None and _wlan.isconnected():
        return True
    return connect(timeout_ms)


def info():
    wlan = _ensure_wlan()
    try:
        connected = wlan.isconnected()
    except Exception:
        connected = False
    try:
        cfg = wlan.ifconfig()
    except Exception:
        cfg = ("0.0.0.0", "0.0.0.0", "0.0.0.0", "0.0.0.0")

    ssid = config.WIFI_SSID
    rssi = None
    channel = "—"
    bssid = "—"
    if connected:
        try:
            value = wlan.config("essid")
            ssid = value.decode() if isinstance(value, bytes) else value
        except Exception:
            pass
        try:
            rssi = wlan.status("rssi")
        except Exception:
            pass
        try:
            channel = wlan.config("channel")
        except Exception:
            pass
        try:
            raw = wlan.config("bssid")
            bssid = ":".join("%02x" % value for value in raw)
        except Exception:
            pass

    try:
        hostname = network.hostname()
    except Exception:
        hostname = config.HOSTNAME

    return {
        "connected": connected,
        "ip": cfg[0],
        "netmask": cfg[1],
        "gateway": cfg[2],
        "dns_server": cfg[3],
        "ssid": ssid,
        "rssi": rssi,
        "mac": mac_address(),
        "hostname": hostname,
        "status": status_name(),
        "channel": channel,
        "bssid": bssid,
    }


# ------------------------------------------------------------------ DNS PTR
def _encode_name(name):
    out = bytearray()
    for label in name.split("."):
        out.append(len(label))
        out += label.encode()
    out.append(0)
    return bytes(out)


def _read_name(data, offset):
    labels = []
    jumped = False
    next_offset = offset
    guard = 0
    while True:
        guard += 1
        if guard > 32 or offset >= len(data):
            return ".".join(labels), next_offset
        length = data[offset]
        if length & 0xC0 == 0xC0:
            if not jumped:
                next_offset = offset + 2
            offset = ((length & 0x3F) << 8) | data[offset + 1]
            jumped = True
            continue
        if length == 0:
            if not jumped:
                next_offset = offset + 1
            break
        start = offset + 1
        labels.append(data[start:start + length].decode())
        offset = start + length
    return ".".join(labels), next_offset


def dns_ptr(ip, server=None, timeout=2):
    """Look up the PTR record for an IPv4 address using the DHCP DNS server."""
    if not ip or ip == "0.0.0.0":
        return None
    if server is None or server == "0.0.0.0":
        server = info().get("gateway")
    if not server or server == "0.0.0.0":
        return None

    labels = ip.split(".")
    if len(labels) != 4:
        return None
    query_name = ".".join(reversed(labels)) + ".in-addr.arpa"
    query = (
        b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00"
        + _encode_name(query_name)
        + b"\x00\x0c\x00\x01"
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(timeout)
    try:
        sock.sendto(query, (server, 53))
        data, _ = sock.recvfrom(512)
    except Exception as exc:
        print("DNS PTR:", exc)
        return None
    finally:
        sock.close()

    if len(data) < 12:
        return None
    if data[3] & 0x0F:
        return None
    answers = (data[6] << 8) | data[7]
    offset = 12
    _, offset = _read_name(data, offset)
    offset += 4  # QTYPE + QCLASS

    for _ in range(answers):
        _, offset = _read_name(data, offset)
        if offset + 10 > len(data):
            break
        rtype = (data[offset] << 8) | data[offset + 1]
        rdlength = (data[offset + 8] << 8) | data[offset + 9]
        rdata = offset + 10
        if rtype == 12:
            name, _ = _read_name(data, rdata)
            return name.rstrip(".")
        offset = rdata + rdlength
    return None


def verify_name(name, ip):
    if not name or not ip or ip == "0.0.0.0":
        return False
    try:
        results = socket.getaddrinfo(name, 80)
    except Exception:
        return False
    for result in results:
        try:
            if result[-1][0] == ip:
                return True
        except Exception:
            pass
    return False


def resolve_dns_name(ip, configured=""):
    """Return (name, verified, source)."""
    if configured:
        return configured, verify_name(configured, ip), "config"
    if ip and ip != "0.0.0.0":
        ptr = dns_ptr(ip)
        if ptr:
            return ptr, verify_name(ptr, ip), "PTR"
    try:
        hostname = network.hostname()
    except Exception:
        hostname = None
    if hostname:
        return hostname, verify_name(hostname, ip), "DHCP"
    return None, False, None


# ------------------------------------------------------------------ NTP
def ntp_sync():
    try:
        import ntptime

        ntptime.settime()
        epoch = int(time.time())
        print("NTP: synced", epoch)
        return epoch
    except Exception as exc:
        print("NTP failed:", exc)
        return None


def now_epoch():
    return int(time.time())
