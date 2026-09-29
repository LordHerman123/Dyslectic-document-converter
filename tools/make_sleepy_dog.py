"""Draw Bobby, the sleeping labradoodle shown while focus mode prepares its pages and before a PDF is open.

Writes ``dyslexia_converter/assets/sleepy_dog.webp``: a small looping animation on a transparent background. Bobby
lies curled up with his head on his paws, drawn with the same round shapes as the app's icons; he breathes
slowly and a few "z"s float up. Run it again after changing the drawing:

    python tools/make_sleepy_dog.py
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 240, 170          # the size shown
SS = 4                   # drawn this many times larger, then scaled down for smooth edges
FRAMES = 32
FRAME_MS = 90

FUR = (40, 38, 44, 255)          # his black curly coat
EDGE = (92, 88, 102, 255)        # a soft grey line sets the curls and parts apart (and shows on a dark theme)
CURL = (150, 146, 160, 255)
EYES = (235, 230, 240, 255)
NOSE = (10, 10, 12, 255)
ZZZ = (130, 150, 200)
LINE = 3.2                       # the edge width, like an icon's line scaled up

OUT = Path(__file__).resolve().parent.parent / "dyslexia_converter" / "assets" / "sleepy_dog.webp"


def curly(cx, cy, rx, ry, b, n=None):
    """An ellipse with a curly edge: the ellipse plus little circles along its rim."""
    n = n or max(6, int(math.pi * (rx + ry) / (b * 1.9)))
    return [(cx, cy, rx, ry)] + [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n),
                                  b, b) for k in range(n)]


def chain(pts, r0, r1, dy=0.0):
    """Circles along a path, growing from r0 to r1: a curly ear, the paws or the tail."""
    segs = list(zip(pts, pts[1:]))
    lens = [math.dist(a, b) for a, b in segs]
    total, t, out = sum(lens), 0.0, []
    while t <= total:
        acc, i = 0.0, 0
        while i < len(lens) - 1 and acc + lens[i] < t:
            acc += lens[i]
            i += 1
        (x0, y0), (x1, y1) = segs[i]
        f = (t - acc) / lens[i]
        r = r0 + (r1 - r0) * t / total
        out.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f + dy, r, r))
        t += r * 0.8
    return out


def frame(t: float) -> Image.Image:
    """The picture at moment ``t`` (0..1 over one loop)."""
    s = SS
    img = Image.new("RGBA", (W * s, H * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rise = 2.2 * (math.sin(t * 2 * math.pi) + 1) / 2   # one slow breath per loop
    hy = rise * 0.35                                     # the head rises a little less than the back

    parts = [
        curly(146, 94 - rise / 2, 72, 38 + rise / 2, 7, n=26),                        # body, curled up
        chain([(214, 104), (208, 128), (184, 142), (156, 146)], 9, 11),               # tail round the front
        chain([(66, 88), (58, 108), (54, 130)], 10, 12.5, -hy),                        # long curly ears
        chain([(118, 88), (126, 108), (130, 130)], 10, 12.5, -hy),
        curly(92, 98 - hy, 30, 26, 6.5),                                                # head, resting
        chain([(72, 138), (90, 141), (112, 138)], 8, 8),                               # paws under the chin
        curly(92, 120 - hy, 15, 11, 4),                                                 # muzzle and beard
    ]
    for part in parts:  # back to front: the grey edge, then the coat over it
        for grow, colour in ((LINE, EDGE), (0, FUR)):
            for cx, cy, rx, ry in part:
                d.ellipse([(cx - rx - grow) * s, (cy - ry - grow) * s, (cx + rx + grow) * s, (cy + ry + grow) * s],
                          fill=colour)

    w = int(LINE * s * 0.8)
    d.ellipse([86 * s, (107 - hy) * s, 98 * s, (115 - hy) * s], fill=NOSE)
    for x0, x1 in ((72, 86), (98, 112)):  # closed eyes
        d.arc([x0 * s, (94 - hy) * s, x1 * s, (102 - hy) * s], 15, 165, fill=EYES, width=w)
    curls = [(150, 72 - rise), (176, 80 - rise), (196, 98 - rise / 2), (160, 100 - rise / 2), (136, 70 - rise),
             (82, 82 - hy), (102, 82 - hy)]
    for x, y in curls:
        d.arc([(x - 6) * s, (y - 5) * s, (x + 6) * s, (y + 5) * s], 200, 340, fill=CURL, width=int(w * 0.8))

    small = img.resize((W, H), Image.LANCZOS)

    # three "z"s float up from his head and fade, one after the other
    zl = Image.new("RGBA", (W * s, H * s), (0, 0, 0, 0))
    zd = ImageDraw.Draw(zl)
    for k in range(3):
        p = (t + k / 3) % 1.0
        x = 98 + p * 30 + math.sin(p * 2 * math.pi) * 3
        y = 46 - p * 44
        alpha = int(255 * min(1.0, p * 5) * (1 - p) ** 0.7)
        zd.text((x * s, y * s), "z", font=_font(int((10 + p * 11) * s)), fill=ZZZ + (alpha,))
    return Image.alpha_composite(small, zl.resize((W, H), Image.LANCZOS))


def _font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def main() -> None:
    frames = [frame(i / FRAMES) for i in range(FRAMES)]
    frames[0].save(OUT, "WEBP", save_all=True, append_images=frames[1:], duration=FRAME_MS, loop=0,
                   lossless=False, quality=90, method=6)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
