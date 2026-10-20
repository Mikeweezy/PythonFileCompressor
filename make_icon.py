"""
make_icon.py - Builds icon.ico for PyCompressor (standard library only!).

What you can learn from this file:

  * An .ico file is a tiny container that stores the SAME image at
    several sizes (16, 32, 48, 64, 128, 256). Windows picks the best
    one for each place the icon appears (taskbar, Explorer, desktop).
  * Each size is stored as a raw uncompressed BMP: a 40-byte header,
    then pixel rows written BOTTOM-to-TOP, each pixel as BGRA
    (Blue, Green, Red, Alpha) - yes, the channels are reversed, and
    yes, the image is upside down. Old-school format quirks!
  * After the pixels comes a 1-bit "AND mask". We fill it with zeros
    (meaning "opaque"); on modern Windows the alpha channel does the
    real transparency work.

Run:   python make_icon.py   ->  writes icon.ico next to this file.
"""

import os
import struct

MASTER = 256                            # draw once at high resolution...
SIZES = (16, 32, 48, 64, 128, 256)      # ...then shrink to these sizes.

# One big byte buffer: 256x256 pixels, 4 bytes each (R, G, B, A),
# rows stored top to bottom.
img = bytearray(4 * MASTER * MASTER)


def draw_master():
    """Paint the icon design into the master image."""
    margin, radius = 8, 56

    def inside_rounded(x, y):
        """True if (x, y) is inside our rounded-corner square.

        Trick: clamp the point into the inner straight-edge rectangle,
        then measure the distance to that clamped point. One formula
        handles straight edges AND all four corners.
        """
        lo, hi = margin, MASTER - 1 - margin
        if not (lo <= x <= hi and lo <= y <= hi):
            return False
        cx = min(max(x, lo + radius), hi - radius)
        cy = min(max(y, lo + radius), hi - radius)
        return (x - cx) ** 2 + (y - cy) ** 2 <= radius * radius

    def put(x, y, r, g, b, a=255):
        i = 4 * (y * MASTER + x)
        img[i] = r
        img[i + 1] = g
        img[i + 2] = b
        img[i + 3] = a

    # Background: blue gradient, clipped to the rounded square.
    for y in range(MASTER):
        t = y / (MASTER - 1)
        r, g, b = int(70 + (32 - 70) * t), int(130 + (88 - 130) * t), int(245 + (200 - 245) * t)
        for x in range(MASTER):
            if inside_rounded(x, y):
                put(x, y, r, g, b)

    # Three white bars that get narrower = the "squeezing" metaphor.
    def bar(y0, y1, x0, x1):
        for y in range(y0, y1):
            for x in range(x0, x1):
                put(x, y, 250, 250, 252)

    bar(64, 88, 60, 196)    # widest
    bar(112, 136, 78, 178)  # medium
    bar(160, 184, 96, 160)  # narrowest


def shrink(size):
    """Box-average the master image down to the requested size.

    For each output pixel we average a rectangular block of master
    pixels. 'edges' handles sizes that don't divide 256 evenly
    (like 48) by giving every block fair boundaries.
    """
    edges = [round(i * MASTER / size) for i in range(size + 1)]
    out = bytearray(4 * size * size)
    for oy in range(size):
        y0, y1 = edges[oy], edges[oy + 1]
        for ox in range(size):
            x0, x1 = edges[ox], edges[ox + 1]
            r = g = b = a = n = 0
            for y in range(y0, y1):
                base = 4 * (y * MASTER)
                for x in range(x0, x1):
                    i = base + 4 * x
                    r += img[i]
                    g += img[i + 1]
                    b += img[i + 2]
                    a += img[i + 3]
                    n += 1
            j = 4 * (oy * size + ox)
            out[j] = round(r / n)
            out[j + 1] = round(g / n)
            out[j + 2] = round(b / n)
            out[j + 3] = round(a / n)
    return out


def bmp_bytes(pixels, size):
    """Wrap RGBA pixels as a bottom-up BGRA bitmap (the ICO's image part)."""
    # BITMAPINFOHEADER: 40 bytes. biHeight is DOUBLED because the ICO
    # format appends the AND mask below the pixels.
    pixel_bytes = size * size * 4
    header = struct.pack(
        "<IiiHHIIiiII",
        40, size, size * 2, 1, 32, 0,          # size, w, h*2, planes, bpp, BI_RGB
        pixel_bytes + mask_bytes(size),        # biSizeImage
        0, 0, 0, 0,
    )
    rows = bytearray()
    for y in range(size - 1, -1, -1):          # bottom row first!
        for x in range(size):
            i = 4 * (y * size + x)
            rows += bytes((pixels[i + 2], pixels[i + 1], pixels[i], pixels[i + 3]))
    return header + bytes(rows)


def mask_bytes(size):
    """Bytes for a 1-bit mask whose rows are padded to 4-byte boundaries."""
    return ((size + 31) // 32 * 4) * size


def build_ico():
    """Assemble all sizes into one .ico blob."""
    entries = b""
    blob = b""
    offset = 6 + 16 * len(SIZES)               # header + one entry per size
    for size in SIZES:
        data = bmp_bytes(shrink(size), size) + b"\x00" * mask_bytes(size)
        # Width/height byte: 0 is the special code for 256.
        wb = 0 if size == 256 else size
        entries += struct.pack("<BBBBHHII", wb, wb, 0, 0, 1, 32, len(data), offset)
        blob += data
        offset += len(data)
    # ICONDIR: reserved=0, type=1 (icon), count.
    return struct.pack("<HHH", 0, 1, len(SIZES)) + entries + blob


draw_master()
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.ico")
with open(out_path, "wb") as f:
    f.write(build_ico())
print(f"Wrote {out_path} ({os.path.getsize(out_path):,} bytes)")