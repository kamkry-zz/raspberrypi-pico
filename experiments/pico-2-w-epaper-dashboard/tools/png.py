"""Minimal PNG writer (stdlib only) for host-side canvas previews."""

import struct
import zlib


def _chunk(tag, data):
    return (
        struct.pack(">I", len(data))
        + tag
        + data
        + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    )


def write_rgb(path, width, height, rows):
    """Write an 8-bit RGB PNG.  ``rows`` is a sequence of RGB byte strings."""
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _chunk(b"IDAT", zlib.compress(raw, 9))
        + _chunk(b"IEND", b"")
    )
    with open(path, "wb") as handle:
        handle.write(png)


def canvas_palette(red=(190, 45, 35)):
    # Indexed by canvas colour constant: BLACK=0, WHITE=1, RED=2.
    return ((0, 0, 0), (255, 255, 255), red)


def write_canvas(path, canvas, scale=1, red=(190, 45, 35)):
    palette = canvas_palette(red)
    rows = []
    for y in range(canvas.height):
        row = bytearray()
        for x in range(canvas.width):
            row.extend(palette[canvas.get_color(x, y)] * scale)
        for _ in range(scale):
            rows.append(bytes(row))
    write_rgb(path, canvas.width * scale, canvas.height * scale, rows)
