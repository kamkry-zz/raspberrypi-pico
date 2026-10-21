"""Small, portable 1-bit canvas for the 4.2-B panel.

This module is deliberately pure Python: the same layout code runs on the Pico
and on the host preview.  The two byte buffers use the panel's native encoding:

    colour   black plane   red plane
    black    0             1
    white    1             1
    red      1             0

The red plane is therefore active-low.  Do not assume "1 means red" here; that
is the Waveshare demo's framebuffer convention, not the wire format.

Within a byte, pixels are packed MSB-first, matching MicroPython's
``framebuf.MONO_HLSB`` output on the verified 1.23.0 firmware.  This was
confirmed byte-for-byte against a framebuf-built reference frame; the wiki's
MSB example is correct for this controller.
"""

BLACK = 0
WHITE = 1
RED = 2

# 4x4 ordered-dither matrix, values 0..15.
BAYER4 = (
    (0, 8, 2, 10),
    (12, 4, 14, 6),
    (3, 11, 1, 9),
    (15, 7, 13, 5),
)


def codepoints(text):
    """Yield Unicode code points from a MicroPython/CPython UTF-8 string."""
    data = text.encode("utf-8")
    i = 0
    n = len(data)
    while i < n:
        first = data[i]
        if first < 0x80:
            yield first
            i += 1
        elif first < 0xE0:
            yield ((first & 0x1F) << 6) | (data[i + 1] & 0x3F)
            i += 2
        elif first < 0xF0:
            yield (
                ((first & 0x0F) << 12)
                | ((data[i + 1] & 0x3F) << 6)
                | (data[i + 2] & 0x3F)
            )
            i += 3
        else:
            yield (
                ((first & 0x07) << 18)
                | ((data[i + 1] & 0x3F) << 12)
                | ((data[i + 2] & 0x3F) << 6)
                | (data[i + 3] & 0x3F)
            )
            i += 4


def text_width(text, font):
    return len(list(codepoints(text))) * font.advance


class Font:
    """Monospaced, bit-packed bitmap font.

    ``glyphs`` maps a Unicode code point to a row-major bitmap.  Each row uses
    ``bytes_per_row`` bytes, MSB first.  Missing glyphs fall back to '?'.
    """

    def __init__(self, width, height, advance, glyphs):
        self.width = width
        self.height = height
        self.advance = advance
        self.bytes_per_row = (width + 7) // 8
        self.glyphs = glyphs


class Canvas:
    CLEAR_CHUNK = 256

    def __init__(self, width=400, height=300, colour=WHITE):
        self.width = width
        self.height = height
        self.stride = (width + 7) // 8
        self.size = self.stride * height
        self.black = bytearray(self.size)
        self.red = bytearray(self.size)
        self.clear(colour)

    # --------------------------------------------------------------- filling
    def clear(self, colour=WHITE):
        black_value, red_value = self._plane_values(colour)
        chunk = self.CLEAR_CHUNK
        black_block = bytes((black_value,)) * chunk
        red_block = bytes((red_value,)) * chunk
        # Fill in small chunks: a 15 KB ``bytes`` temporary can fail with
        # MemoryError after the weather fetch fragments the heap.
        for offset in range(0, self.size, chunk):
            end = offset + chunk
            if end <= self.size:
                self.black[offset:end] = black_block
                self.red[offset:end] = red_block
            else:
                tail = self.size - offset
                self.black[offset:] = black_block[:tail]
                self.red[offset:] = red_block[:tail]

    @staticmethod
    def _plane_values(colour):
        # Native panel encoding.
        if colour == BLACK:
            return 0x00, 0xFF
        if colour == RED:
            return 0xFF, 0x00
        return 0xFF, 0xFF

    def pixel(self, x, y, colour):
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return
        index = y * self.stride + (x >> 3)
        mask = 0x80 >> (x & 7)
        if colour == BLACK:
            self.black[index] &= 0xFF - mask
            self.red[index] |= mask
        elif colour == RED:
            self.black[index] |= mask
            self.red[index] &= 0xFF - mask
        else:
            self.black[index] |= mask
            self.red[index] |= mask

    def get_color(self, x, y):
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return None
        index = y * self.stride + (x >> 3)
        mask = 0x80 >> (x & 7)
        black = 1 if self.black[index] & mask else 0
        red = 1 if self.red[index] & mask else 0
        if black:
            return WHITE if red else RED
        return BLACK

    def fill_rect(self, x, y, width, height, colour):
        if width <= 0 or height <= 0:
            return
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + width)
        y1 = min(self.height, y + height)
        if x1 <= x0 or y1 <= y0:
            return

        black_value, red_value = self._plane_values(colour)
        stride = self.stride
        first_bit = x0 & 7
        last_bit = (x1 - 1) & 7
        first_byte = x0 >> 3
        last_byte = (x1 - 1) >> 3
        # MSB-first byte packing (verified against framebuf on-device).
        first_mask = (0xFF >> first_bit) & 0xFF
        last_mask = (0xFF << (7 - last_bit)) & 0xFF

        for yy in range(y0, y1):
            base = yy * stride
            if first_byte == last_byte:
                mask = first_mask & last_mask
                self.black[base + first_byte] = (
                    (self.black[base + first_byte] & (0xFF - mask))
                    | (black_value & mask)
                )
                self.red[base + first_byte] = (
                    (self.red[base + first_byte] & (0xFF - mask))
                    | (red_value & mask)
                )
            else:
                self.black[base + first_byte] = (
                    (self.black[base + first_byte] & (0xFF - first_mask))
                    | (black_value & first_mask)
                )
                self.red[base + first_byte] = (
                    (self.red[base + first_byte] & (0xFF - first_mask))
                    | (red_value & first_mask)
                )
                middle = last_byte - first_byte - 1
                if middle > 0:
                    self.black[base + first_byte + 1:base + last_byte] = (
                        bytes((black_value,)) * middle
                    )
                    self.red[base + first_byte + 1:base + last_byte] = (
                        bytes((red_value,)) * middle
                    )
                self.black[base + last_byte] = (
                    (self.black[base + last_byte] & (0xFF - last_mask))
                    | (black_value & last_mask)
                )
                self.red[base + last_byte] = (
                    (self.red[base + last_byte] & (0xFF - last_mask))
                    | (red_value & last_mask)
                )

    def hline(self, x, y, width, colour):
        self.fill_rect(x, y, width, 1, colour)

    def vline(self, x, y, height, colour):
        self.fill_rect(x, y, 1, height, colour)

    def rect(self, x, y, width, height, colour, fill=False):
        if fill:
            self.fill_rect(x, y, width, height, colour)
            return
        if width <= 0 or height <= 0:
            return
        self.hline(x, y, width, colour)
        self.hline(x, y + height - 1, width, colour)
        self.vline(x, y, height, colour)
        self.vline(x + width - 1, y, height, colour)

    def line(self, x0, y0, x1, y1, colour):
        dx = abs(x1 - x0)
        sx = 1 if x0 < x1 else -1
        dy = -abs(y1 - y0)
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        while True:
            self.pixel(x0, y0, colour)
            if x0 == x1 and y0 == y1:
                break
            twice = 2 * err
            if twice >= dy:
                err += dy
                x0 += sx
            if twice <= dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, radius, colour, fill=False):
        x = radius
        y = 0
        err = 0
        while x >= y:
            if fill:
                self.hline(cx - x, cy + y, 2 * x + 1, colour)
                self.hline(cx - x, cy - y, 2 * x + 1, colour)
                self.hline(cx - y, cy + x, 2 * y + 1, colour)
                self.hline(cx - y, cy - x, 2 * y + 1, colour)
            else:
                self.pixel(cx + x, cy + y, colour)
                self.pixel(cx + y, cy + x, colour)
                self.pixel(cx - y, cy + x, colour)
                self.pixel(cx - x, cy + y, colour)
                self.pixel(cx - x, cy - y, colour)
                self.pixel(cx - y, cy - x, colour)
                self.pixel(cx + y, cy - x, colour)
                self.pixel(cx + x, cy - y, colour)
            y += 1
            if err <= 0:
                err += 2 * y + 1
            if err > 0:
                x -= 1
                err -= 2 * x + 1

    def dither_rect(self, x, y, width, height, foreground, background, level):
        """Ordered dither.  ``level`` is 0..16 (0 = background, 16 = fg)."""
        if level <= 0:
            self.fill_rect(x, y, width, height, background)
            return
        if level >= 16:
            self.fill_rect(x, y, width, height, foreground)
            return
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.width, x + width)
        y1 = min(self.height, y + height)
        for yy in range(y0, y1):
            row = BAYER4[yy & 3]
            for xx in range(x0, x1):
                if row[xx & 3] < level:
                    self.pixel(xx, yy, foreground)
                else:
                    self.pixel(xx, yy, background)

    # ------------------------------------------------------------------ text
    def text(self, x, y, text, colour, font, anchor="left"):
        widths = list(codepoints(text))
        width = len(widths) * font.advance
        if anchor == "right":
            x -= width
        elif anchor == "center":
            x -= width // 2

        fallback = font.glyphs.get(63)  # '?'
        for ch in widths:
            glyph = font.glyphs.get(ch)
            if glyph is None:
                glyph = fallback
            if glyph is not None:
                for row in range(font.height):
                    py = y + row
                    if py < 0 or py >= self.height:
                        continue
                    base = row * font.bytes_per_row
                    for col in range(font.width):
                        if glyph[base + (col >> 3)] & (0x80 >> (col & 7)):
                            self.pixel(x + col, py, colour)
            x += font.advance
        return width
