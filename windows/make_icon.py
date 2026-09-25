"""Draw the app logo: "Dc" on a warm-white tile with a burgundy border and a champagne line.

    python windows/make_icon.py

The "D" is Playfair Display; the "c" is Varela Round (a clear, open c that can't be mistaken for an e).
Writes windows/app.png (256 px), windows/app.ico (16-256 px), dyslexia_converter/assets/icon.png (window
icon) and dyslexia_converter/assets/logo_small.png (drawn small for the top bar, so it stays sharp).
The fonts in windows/logo_font (SIL Open Font License) are only used to draw the logo.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONTS = ROOT / "windows" / "logo_font"
FONT_D = FONTS / "PlayfairDisplay-ExtraBold.woff"
FONT_C = FONTS / "VarelaRound-Regular.woff"

TILE = "#FFFBF5"       # warm white
BORDER = "#7A2E3A"     # burgundy
LETTERS = "#4A1C24"    # deep burgundy
LINE = "#D8B26E"       # champagne
C_WEIGHT = 0.035       # extra thickness for the c, so it matches the bold D


def draw(size: int = 1024) -> Image.Image:
    s = size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad, radius, border = round(s * 0.04), round(s * 0.2), round(s * 0.045)
    d.rounded_rectangle((pad, pad, s - pad, s - pad), radius=radius, fill=BORDER)
    d.rounded_rectangle((pad + border, pad + border, s - pad - border, s - pad - border),
                        radius=radius - border, fill=TILE)

    font_d = ImageFont.truetype(str(FONT_D), round(s * 0.50))
    # size the c so it is as tall as a Playfair c would be (a proper lowercase next to the D)
    ref = d.textbbox((0, 0), "c", font=font_d)
    target = ref[3] - ref[1]
    pt = round(s * 0.50)
    for _ in range(60):
        font_c = ImageFont.truetype(str(FONT_C), pt)
        stroke = round(C_WEIGHT * pt)
        box = d.textbbox((0, 0), "c", font=font_c, stroke_width=stroke)
        if abs((box[3] - box[1]) - target) < 3:
            break
        pt = round(pt * target / (box[3] - box[1]))

    box_d = d.textbbox((0, 0), "D", font=font_d)
    box_c = d.textbbox((0, 0), "c", font=font_c, stroke_width=stroke)
    gap = s * 0.02
    w_d, w_c = box_d[2] - box_d[0], box_c[2] - box_c[0]
    total = w_d + gap + w_c
    x = (s - total) / 2
    base = s * 0.62  # both letters sit on this line
    d.text((x - box_d[0], base - box_d[3]), "D", font=font_d, fill=LETTERS)
    d.text((x + w_d + gap - box_c[0], base - box_c[3]), "c", font=font_c, fill=LETTERS,
           stroke_width=stroke, stroke_fill=LETTERS)

    # one line underneath, like a line of text
    lw, top = round(s * 0.055), round(s * 0.70)
    half = max(total * 0.55, s * 0.28)
    d.rounded_rectangle((s / 2 - half, top, s / 2 + half, top + lw), radius=lw // 2, fill=LINE)
    return im


def main() -> None:
    big = draw(1024)
    png = big.resize((256, 256), Image.LANCZOS)
    png.save(ROOT / "windows" / "app.png")
    png.save(ROOT / "dyslexia_converter" / "assets" / "icon.png")
    big.resize((96, 96), Image.LANCZOS).save(ROOT / "dyslexia_converter" / "assets" / "logo_small.png")
    big.save(ROOT / "windows" / "app.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64),
                                                  (128, 128), (256, 256)])
    print("icon written")


if __name__ == "__main__":
    main()
