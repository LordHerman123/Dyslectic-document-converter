"""Draw the app logo ("Dc" in Playfair Display on a white tile, burgundy border, champagne line).

    python windows/make_icon.py

Writes windows/app.png (256 px), windows/app.ico (16-256 px) and dyslexia_converter/assets/icon.png
(used by the window and the header). The font is in windows/logo_font (SIL Open Font License); it is
only used to draw the logo and is not shipped with the app.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / "windows" / "logo_font" / "PlayfairDisplay-ExtraBold.woff"

TILE = "#FFFBF5"       # warm white
BORDER = "#7A2E3A"     # burgundy
LETTERS = "#4A1C24"    # deep burgundy
LINE = "#D8B26E"       # champagne


def draw(size: int = 1024) -> Image.Image:
    s = size
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pad, radius, border = round(s * 0.04), round(s * 0.2), round(s * 0.045)
    d.rounded_rectangle((pad, pad, s - pad, s - pad), radius=radius, fill=BORDER)
    d.rounded_rectangle((pad + border, pad + border, s - pad - border, s - pad - border),
                        radius=radius - border, fill=TILE)

    # largest size at which "Dc" fits the tile
    pt = round(s * 0.52)
    font = ImageFont.truetype(str(FONT), pt)
    while True:
        box = d.textbbox((0, 0), "Dc", font=font)
        if box[2] - box[0] <= s * 0.62 and box[3] - box[1] <= s * 0.40:
            break
        pt -= 8
        font = ImageFont.truetype(str(FONT), pt)
    w, h = box[2] - box[0], box[3] - box[1]
    d.text(((s - w) / 2 - box[0], s * 0.62 - h - box[1]), "Dc", font=font, fill=LETTERS)

    # one line underneath, like a line of text
    lw, top = round(s * 0.055), round(s * 0.70)
    half = max(w * 0.55, s * 0.28)
    d.rounded_rectangle((s / 2 - half, top, s / 2 + half, top + lw), radius=lw // 2, fill=LINE)
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
