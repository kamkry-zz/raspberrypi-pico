"""Simple vector icons drawn with the canvas primitives."""

from canvas import BLACK, RED, WHITE


def sun(canvas, cx, cy, radius, colour=RED):
    canvas.circle(cx, cy, radius, colour, fill=True)
    inner = radius + 3
    outer = radius + 7
    for dx, dy in (
        (1, 0), (-1, 0), (0, 1), (0, -1),
        (1, 1), (1, -1), (-1, 1), (-1, -1),
    ):
        canvas.line(cx + dx * inner, cy + dy * inner, cx + dx * outer, cy + dy * outer, colour)


def moon(canvas, cx, cy, radius, colour=BLACK):
    canvas.circle(cx, cy, radius, colour, fill=True)
    canvas.circle(cx + radius // 3, cy - radius // 4, radius, WHITE, fill=True)


def cloud(canvas, x, y, size, colour=BLACK):
    r = max(3, size // 5)
    cy = y + size // 2
    canvas.circle(x + r, cy, r, colour, fill=True)
    canvas.circle(x + size // 2, cy - r // 2, r + 1, colour, fill=True)
    canvas.circle(x + size - r, cy, r, colour, fill=True)
    canvas.fill_rect(x + r, cy, size - 2 * r, r + 2, colour)


def rain(canvas, x, y, size, colour=BLACK):
    cloud(canvas, x, y, size)
    base = y + size * 2 // 3
    for offset in (size // 4, size // 2, 3 * size // 4):
        canvas.line(x + offset, base, x + offset - 3, base + size // 5, colour)


def snow(canvas, x, y, size, colour=BLACK):
    cloud(canvas, x, y, size)
    base = y + size * 2 // 3
    for offset in (size // 4, size // 2, 3 * size // 4):
        cx = x + offset
        cy = base + size // 7
        arm = max(2, size // 12)
        canvas.line(cx - arm, cy, cx + arm, cy, colour)
        canvas.line(cx, cy - arm, cx, cy + arm, colour)


def storm(canvas, x, y, size, colour=BLACK):
    cloud(canvas, x, y, size)
    base = y + size * 2 // 3
    canvas.line(x + size // 2, base, x + size // 3, base + size // 4, RED)
    canvas.line(x + size // 3, base + size // 4, x + size // 2, base + size // 4, RED)
    canvas.line(x + size // 2, base + size // 4, x + size // 3, base + size // 2, RED)


def fog(canvas, x, y, size, colour=BLACK):
    for index, offset in enumerate((size // 4, size // 2, 3 * size // 4)):
        start = x + (index % 2) * size // 8
        canvas.line(start, y + offset, x + size - size // 8, y + offset, colour)


def weather_icon(canvas, x, y, size, code, is_day=True):
    if code == 0:
        if is_day:
            sun(canvas, x + size // 2, y + size // 2, size // 4)
        else:
            moon(canvas, x + size // 2, y + size // 2, size // 4)
    elif code in (1, 2):
        if is_day:
            sun(canvas, x + size // 3, y + size // 3, max(3, size // 6))
        else:
            moon(canvas, x + size // 3, y + size // 3, max(3, size // 6))
        cloud(canvas, x + size // 4, y + size // 3, size - size // 4)
    elif code == 3:
        cloud(canvas, x, y + size // 4, size)
    elif code in (45, 48):
        fog(canvas, x, y, size)
    elif code in (51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82):
        rain(canvas, x, y, size)
    elif code in (71, 73, 75, 77, 85, 86):
        snow(canvas, x, y, size)
    elif code in (95, 96, 99):
        storm(canvas, x, y, size)
    else:
        cloud(canvas, x, y + size // 4, size)


def wifi_bars(canvas, x, y, rssi):
    if rssi is None:
        rssi = -100
    if rssi >= -55:
        level = 4
    elif rssi >= -65:
        level = 3
    elif rssi >= -75:
        level = 2
    else:
        level = 1
    colour = RED if level <= 1 else BLACK
    for index in range(4):
        height = 4 + index * 3
        bx = x + index * 5
        by = y + 13 - height
        if index < level:
            canvas.fill_rect(bx, by, 3, height, colour)
        else:
            canvas.rect(bx, by, 3, height, BLACK)


def check(canvas, x, y, colour=BLACK):
    canvas.line(x, y + 4, x + 3, y + 7, colour)
    canvas.line(x + 3, y + 7, x + 9, y, colour)


def cross(canvas, x, y, colour=RED):
    canvas.line(x, y, x + 7, y + 7, colour)
    canvas.line(x + 7, y, x, y + 7, colour)
