"""Minimal HTTP/HTTPS GET client for MicroPython.

HTTPS is attempted first; if the TLS handshake fails the request is retried
over HTTP.  Open-Meteo serves public weather data, so certificate pinning is
out of scope for this experiment.
"""

import gc
import socket
import ssl

import config


def _parse_url(url):
    if url.startswith("https://"):
        scheme = "https"
        rest = url[8:]
    elif url.startswith("http://"):
        scheme = "http"
        rest = url[7:]
    else:
        raise ValueError("only http/https URLs are supported")

    slash = rest.find("/")
    if slash < 0:
        host = rest
        path = "/"
    else:
        host = rest[:slash]
        path = rest[slash:]

    port = 443 if scheme == "https" else 80
    if ":" in host:
        host, port_text = host.split(":", 1)
        port = int(port_text)
    return scheme, host, port, path


def _decode_chunked(body):
    out = bytearray()
    index = 0
    while True:
        end = body.find(b"\r\n", index)
        if end < 0:
            break
        size_text = body[index:end].split(b";")[0]
        try:
            size = int(size_text, 16)
        except ValueError:
            break
        if size == 0:
            break
        start = end + 2
        out += body[start:start + size]
        index = start + size + 2
    return bytes(out)


def _request(scheme, host, port, path, timeout, max_bytes):
    address = socket.getaddrinfo(host, port)[0][-1]
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect(address)
        tls = scheme == "https"
        if tls:
            sock = ssl.wrap_socket(sock, server_hostname=host)

        def send(data):
            if tls:
                sock.write(data)
            else:
                sock.send(data)

        def recv(size):
            if tls:
                return sock.read(size)
            return sock.recv(size)

        request = (
            "GET %s HTTP/1.0\r\n"
            "Host: %s\r\n"
            "User-Agent: %s\r\n"
            "Connection: close\r\n"
            "\r\n" % (path, host, config.USER_AGENT)
        )
        send(request.encode())

        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = recv(512)
            if not chunk:
                break
            data += chunk
            if len(data) > 8192:
                break

        # Header parsing must use hashable bytes keys, not bytearrays.
        head, _, body = bytes(data).partition(b"\r\n\r\n")
        lines = head.split(b"\r\n")
        status = 0
        if lines and len(lines[0].split()) >= 2:
            status = int(lines[0].split()[1])

        headers = {}
        for line in lines[1:]:
            if b":" in line:
                key, value = line.split(b":", 1)
                headers[key.strip().lower()] = value.strip()

        body = bytearray(body)
        if headers.get(b"transfer-encoding", b"").lower() == b"chunked":
            while True:
                chunk = recv(1024)
                if not chunk:
                    break
                body += chunk
                if len(body) > max_bytes:
                    break
            body = _decode_chunked(bytes(body))
        else:
            length = headers.get(b"content-length")
            if length:
                remaining = int(length) - len(body)
                while remaining > 0:
                    chunk = recv(min(1024, remaining))
                    if not chunk:
                        break
                    body += chunk
                    remaining -= len(chunk)
            else:
                while len(body) < max_bytes:
                    chunk = recv(1024)
                    if not chunk:
                        break
                    body += chunk

        return status, headers, bytes(body)
    finally:
        try:
            sock.close()
        except Exception:
            pass
        gc.collect()


def get_to_file(url, path, etag=None, timeout=12, max_bytes=32768):
    """Plain-HTTP GET streamed to ``path`` in 1 KB chunks (no large heap block).

    Sends ``If-None-Match`` when ``etag`` is given.  Returns (status, etag):
    200 = new body written to ``path``; 304 = unchanged, ``path`` untouched.
    Only ``http://`` is supported (the LAN pogoda-hub device API).
    """
    scheme, host, port, req_path = _parse_url(url)
    if scheme != "http":
        raise ValueError("get_to_file supports http:// only")
    gc.collect()
    address = socket.getaddrinfo(host, port)[0][-1]
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect(address)
        extra = "If-None-Match: %s\r\n" % etag if etag else ""
        sock.send(
            (
                "GET %s HTTP/1.0\r\nHost: %s\r\nUser-Agent: %s\r\n%sConnection: close\r\n\r\n"
                % (req_path, host, config.USER_AGENT, extra)
            ).encode()
        )
        data = bytearray()
        while b"\r\n\r\n" not in data:
            chunk = sock.recv(512)
            if not chunk:
                break
            data += chunk
            if len(data) > 8192:
                raise OSError("header too large")
        head, _, rest = bytes(data).partition(b"\r\n\r\n")
        lines = head.split(b"\r\n")
        status = int(lines[0].split()[1]) if lines and len(lines[0].split()) >= 2 else 0
        new_etag = None
        length = None
        for line in lines[1:]:
            key, _, value = line.partition(b":")
            key = key.strip().lower()
            if key == b"etag":
                new_etag = value.strip().decode()
            elif key == b"content-length":
                length = int(value.strip())
        if status != 200:
            return status, new_etag or etag
        if length is None or length > max_bytes:
            raise OSError("bad content-length %r" % (length,))
        written = 0
        with open(path, "wb") as handle:
            if rest:
                handle.write(rest)
                written = len(rest)
            while written < length:
                chunk = sock.recv(min(1024, length - written))
                if not chunk:
                    break
                handle.write(chunk)
                written += len(chunk)
        if written != length:
            raise OSError("short body %d/%d" % (written, length))
        return status, new_etag
    finally:
        try:
            sock.close()
        except Exception:
            pass
        gc.collect()


def get(url, timeout=12, max_bytes=24000):
    scheme, host, port, path = _parse_url(url)
    gc.collect()
    try:
        return _request(scheme, host, port, path, timeout, max_bytes)
    except Exception as exc:
        if scheme == "https":
            print("HTTPS failed (%s); retrying over HTTP" % exc)
            gc.collect()
            return _request("http", host, 80, path, timeout, max_bytes)
        raise
