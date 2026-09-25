"""Draw the app logo ("DC" on a terracotta tile, autumn palette) and write every size the app needs.

    python windows/make_icon.py

Writes windows/app.png (256 px), windows/app.ico (16-256 px) and dyslexia_converter/assets/icon.png
(used by the window and the header).
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "dyslexia_converter" / "assets" / "fonts" / "AtkinsonHyperlegible-Bold.ttf"

TILE = "#A0654E"       # terracotta
TILE_EDGE = "#8A5441"
LETTERS = "#F7F0E6"    # cream
LINES = "#E2B56A"      # caramel


def draw(size: int = 1024) -> Image.Image:
    s = size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad = round(s * 0.04)
    radius = round(s * 0.22)
    d.rounded_rectangle((pad, pad, s - pad, s - pad), radius=radius, fill=TILE_EDGE)
    inset = round(s * 0.018)
    d.rounded_rectangle((pad + inset, pad + inset, s - pad - inset, s - pad - inset),
                        radius=radius - inset, fill=TILE)

    font = ImageFont.truetype(str(FONT), round(s * 0.46))
    text = "DC"
    box = d.textbbox((0, 0), text, font=font)
    w, h = box[2] - box[0], box[3] - box[1]
    x = (s - w) / 2 - box[0]
    y = s * 0.40 - h / 2 - box[1]
    d.text((x, y), text, font=font, fill=LETTERS)

    # three "lines of text", like a page laid out for easy reading
    lw = round(s * 0.05)
    top = round(s * 0.66)
    for i, frac in enumerate((0.56, 0.44, 0.32)):
        half = s * frac / 2
        yy = top + i * round(s * 0.085)
        d.rounded_rectangle((s / 2 - half, yy, s / 2 + half, yy + lw), radius=lw // 2, fill=LINES)
    return im


def main() -> None:
    big = draw(1024)
    png = big.resize((256, 256), Image.LANCZOS)
    png.save(ROOT / "windows" / "app.png")
    png.save(ROOT / "dyslexia_converter" / "assets" / "icon.png")
    big.save(ROOT / "windows" / "app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                                  (128, 128), (256, 256)])
    print("icon written")


if __name__ == "__main__":
    main()
