"""Draw the sleeping dog shown while focus mode prepares its pages and before a PDF is open.

Writes ``dyslexia_converter/assets/sleepy_dog.webp``: a small looping animation on a transparent background (it
suits the light and the dark theme alike). The dog lies curled up on a cushion, breathes slowly, and a few "z"s
float up. Run it again after changing the drawing:

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

FUR = (222, 170, 110, 255)
FUR_DARK = (168, 110, 62, 255)
FUR_EDGE = (196, 140, 86, 255)
MUZZLE = (246, 222, 188, 255)
LINE = (92, 58, 36, 255)
NOSE = (60, 40, 30, 255)
CUSHION = (122, 158, 214, 255)
CUSHION_EDGE = (92, 128, 186, 255)
BLUSH = (240, 150, 140, 150)
ZZZ = (112, 140, 196)

OUT = Path(__file__).resolve().parent.parent / "dyslexia_converter" / "assets" / "sleepy_dog.webp"


def _font(size: int):
    for name in ("DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def frame(t: float) -> Image.Image:
    """The picture at moment ``t`` (0..1 over one loop)."""
    s = SS
    img = Image.new("RGBA", (W * s, H * s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    breath = math.sin(t * 2 * math.pi)            # one slow breath per loop
    rise = 3.0 * (breath + 1) / 2                 # the back rises up to 3 px

    def box(x0, y0, x1, y1):
        return [x0 * s, y0 * s, x1 * s, y1 * s]

    # the cushion
    d.ellipse(box(22, 118, 206, 160), fill=CUSHION_EDGE)
    d.ellipse(box(26, 114, 202, 152), fill=CUSHION)
    # the curled tail, behind the body on the right
    d.ellipse(box(150, 92 - rise * 0.3, 196, 132), fill=FUR_DARK)
    d.ellipse(box(152, 98 - rise * 0.3, 188, 130), fill=FUR)
    # the body, breathing
    d.ellipse(box(62, 72 - rise, 184, 138), fill=FUR)
    d.ellipse(box(84, 84 - rise, 150, 112 - rise * 0.5), fill=(232, 186, 130, 255))  # a lighter patch on the back
    # the back leg
    d.ellipse(box(132, 108, 176, 136), fill=FUR_DARK)
    d.ellipse(box(134, 110, 172, 134), fill=FUR)
    # the front paws, in front of the head
    d.rounded_rectangle(box(40, 122, 94, 138), radius=8 * s, fill=FUR)
    d.ellipse(box(34, 122, 54, 138), fill=MUZZLE)
    # the head, resting on the paws; it rises a little less than the back
    hy = rise * 0.35
    d.ellipse(box(36, 78 - hy, 106, 134 - hy), fill=FUR_EDGE)  # a soft edge sets the head apart from the body
    d.ellipse(box(38, 80 - hy, 104, 132 - hy), fill=FUR)
    # the floppy ear hangs down over the side of the head: a rounded drop, tilted back
    ear = Image.new("RGBA", (36 * s, 54 * s), (0, 0, 0, 0))
    ImageDraw.Draw(ear).ellipse([2 * s, 2 * s, 27 * s, 50 * s], fill=FUR_DARK)
    ear = ear.rotate(28, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(ear, (int(80 * s), int((77 - hy) * s)))
    # the muzzle and nose
    d.ellipse(box(28, 106 - hy, 64, 132 - hy), fill=MUZZLE)
    d.ellipse(box(26, 108 - hy, 38, 117 - hy), fill=NOSE)
    # the closed eye: a small smiling arc, and a blush
    d.arc(box(56, 94 - hy, 74, 106 - hy), start=20, end=160, fill=LINE, width=int(2.2 * s))
    d.ellipse(box(60, 108 - hy, 72, 114 - hy), fill=BLUSH)
    # a little smile under the nose
    d.arc(box(34, 116 - hy, 46, 126 - hy), start=10, end=150, fill=LINE, width=int(1.6 * s))

    small = img.resize((W, H), Image.LANCZOS)

    # three "z"s float up and fade, one after the other
    zl = Image.new("RGBA", (W * s, H * s), (0, 0, 0, 0))
    zd = ImageDraw.Draw(zl)
    for k in range(3):
        p = (t + k / 3) % 1.0
        x = 70 + p * 44 + math.sin(p * 2 * math.pi) * 4
        y = 62 - p * 56
        size = int((11 + p * 11) * s)
        alpha = int(255 * min(1.0, p * 5) * (1 - p) ** 0.7)
        zd.text((x * s, y * s), "z", font=_font(size), fill=ZZZ + (alpha,))
    return Image.alpha_composite(small, zl.resize((W, H), Image.LANCZOS))


def main() -> None:
    frames = [frame(i / FRAMES) for i in range(FRAMES)]
    frames[0].save(OUT, "WEBP", save_all=True, append_images=frames[1:], duration=FRAME_MS, loop=0,
                   lossless=False, quality=90, method=6)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
