"""Page images for the Original | Converted preview."""
from __future__ import annotations

import pymupdf


def page_count(pdf: bytes | str) -> int:
    """Number of pages in a PDF (given as bytes or a file path)."""
    with _open(pdf) as doc:
        return doc.page_count


def page_size(pdf: bytes | str, index: int) -> tuple[float, float]:
    """Width and height of a page in points."""
    with _open(pdf) as doc:
        r = doc[max(0, min(index, doc.page_count - 1))].rect
        return r.width, r.height


def tap_to_page(x: float, y: float, box_w: float, box_h: float, page_w: float, page_h: float):
    """Where a click on the preview lands on the page, in points (None beside the page).

    The page picture is fitted inside its box keeping its shape and centred (BoxFit.CONTAIN)."""
    if box_w <= 0 or box_h <= 0 or page_w <= 0 or page_h <= 0:
        return None
    scale = min(box_w / page_w, box_h / page_h)
    left = (box_w - page_w * scale) / 2
    top = (box_h - page_h * scale) / 2
    px, py = (x - left) / scale, (y - top) / scale
    if not (0 <= px <= page_w and 0 <= py <= page_h):
        return None
    return px, py


def render_page(pdf: bytes | str, index: int, width_px: int = 700) -> bytes:
    """PNG of one page scaled to ``width_px`` pixels wide."""
    with _open(pdf) as doc:
        index = max(0, min(index, doc.page_count - 1))
        page = doc[index]
        zoom = width_px / page.rect.width
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return pix.tobytes("png")


def _open(pdf: bytes | str) -> pymupdf.Document:
    """Open a PDF given as bytes (the converted document in memory) or as a file path."""
    if isinstance(pdf, (bytes, bytearray)):
        return pymupdf.open(stream=bytes(pdf), filetype="pdf")
    return pymupdf.open(pdf)


_page_cache: dict = {}

# page colours for reading (focus mode); "dark" shows light text on a dark page
TINTS = {"white": (255, 255, 255), "cream": (250, 241, 214), "blue": (214, 230, 248), "green": (216, 240, 220),
         "grey": (226, 226, 226), "dark": (32, 32, 36)}


def _tinted(base, tint: str):
    """The page picture in a reading colour.

    Light colours multiply the page (black text stays black, white paper takes the colour); "dark" inverts it to
    light text on a dark page.
    """
    from PIL import Image, ImageChops, ImageOps

    if tint == "dark":
        rgb = ImageOps.invert(base.convert("RGB"))  # black text on white -> light text on black
        rgb = ImageChops.lighter(ImageChops.multiply(rgb, Image.new("RGB", rgb.size, (225, 225, 220))),
                                 Image.new("RGB", rgb.size, TINTS["dark"]))
        return rgb.convert("RGBA")
    if tint in TINTS and tint != "white":
        return ImageChops.multiply(base.convert("RGB"), Image.new("RGB", base.size, TINTS[tint])).convert("RGBA")
    return base


def render_highlight(pdf: bytes | str, index: int, width_px: int, sentence: list, word: list,
                     dark: bool = False, marks: list = (), tint: str = "white", ruler: tuple = (),
                     notes: list = (), picked: list = (), selection: list = ()) -> bytes:
    """PNG of a page with the sentence being read aloud marked, and the word being said boxed.

    ``sentence`` and ``word`` are rectangles in PDF points; ``marks`` are the reader's own coloured
    highlights as (rectangle, RGBA). ``tint`` colours the page; ``ruler`` (top, bottom) keeps one line clear
    and dims the rest; ``notes`` are points where a highlight has a note; ``picked`` is the word chosen for
    the word card; ``selection`` are the bands of text being selected (blue, with a handle at each end). The
    plain page is rendered once and kept, so moving the highlight from word to word is quick.
    """
    import io

    from PIL import Image, ImageDraw

    key = (id(pdf), len(pdf), index, width_px)
    if key not in _page_cache:
        if len(_page_cache) > 24:
            _page_cache.clear()
        with _open(pdf) as doc:
            page = doc[max(0, min(index, doc.page_count - 1))]
            zoom = width_px / page.rect.width
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            _page_cache[key] = {"white": Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA"), "zoom": zoom}
    cached = _page_cache[key]
    z = cached["zoom"]
    if tint not in cached:
        cached[tint] = _tinted(cached["white"], tint)
    base = cached[tint]
    dark = dark or tint == "dark"
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for (x0, y0, x1, y1), rgba in marks:  # the reader's marker colours, under the read-aloud highlight
        d.rounded_rectangle([x0 * z - 2, y0 * z - 1, x1 * z + 2, y1 * z + 2], radius=3, fill=tuple(rgba))
    for x0, y0, x1, y1 in sentence:  # soft yellow behind the whole sentence
        d.rectangle([x0 * z - 2, y0 * z - 1, x1 * z + 2, y1 * z + 1], fill=(255, 214, 90, 105))
    edge = (122, 46, 58, 255) if not dark else (230, 110, 130, 255)
    for x0, y0, x1, y1 in word:  # the word being said: a burgundy box
        d.rounded_rectangle([x0 * z - 3, y0 * z - 2, x1 * z + 3, y1 * z + 2], radius=4, fill=(122, 46, 58, 60),
                            outline=edge, width=2)
    for x0, y0, x1, y1 in picked:  # the word on the word card: an outline
        d.rounded_rectangle([x0 * z - 4, y0 * z - 3, x1 * z + 4, y1 * z + 3], radius=5, outline=edge, width=3)
    if selection:  # selected text: light blue, with a handle at the start and at the end (like on a phone)
        blue = (21, 101, 192, 255)
        for x0, y0, x1, y1 in selection:
            d.rectangle([x0 * z - 2, y0 * z - 1, x1 * z + 2, y1 * z + 2], fill=(80, 150, 255, 90))
        (sx, sy0, _, sy1), (_, ey0, ex, ey1) = selection[0], selection[-1]
        r = 5 * z
        d.rectangle([sx * z - 3 - z, sy0 * z - 2, sx * z - 3 + z, sy1 * z + 2], fill=blue)
        d.ellipse([sx * z - 3 - r, sy0 * z - 2 - 2 * r, sx * z - 3 + r, sy0 * z - 2], fill=blue)
        d.rectangle([ex * z + 3 - z, ey0 * z - 2, ex * z + 3 + z, ey1 * z + 2], fill=blue)
        d.ellipse([ex * z + 3 - r, ey1 * z + 2, ex * z + 3 + r, ey1 * z + 2 + 2 * r], fill=blue)
    for x, y in notes:  # a note sign in the margin next to a highlight with a note (x, y: its top left)
        s = 12 * z
        box = [x * z, y * z, x * z + s, y * z + s]
        d.rounded_rectangle(box, radius=2.5 * z, fill=(184, 134, 11, 255))
        for k in (0.32, 0.52, 0.72):
            d.line([box[0] + s * 0.22, box[1] + s * k, box[2] - s * 0.22, box[1] + s * k], fill=(255, 255, 255, 255),
                   width=max(1, int(z)))
    if ruler:  # the reading ruler: the line being read stays clear, the rest is dimmed
        top, bottom = ruler[0] * z - 5 * z, ruler[1] * z + 5 * z
        r, g, b = TINTS.get(tint, TINTS["white"])
        veil = Image.new("RGBA", base.size, (0, 0, 0, 0))  # its own layer, so marks show through it
        v = ImageDraw.Draw(veil)
        v.rectangle([0, 0, base.size[0], top], fill=(r, g, b, 150))
        v.rectangle([0, bottom, base.size[0], base.size[1]], fill=(r, g, b, 150))
        v.line([0, top, base.size[0], top], fill=edge, width=max(2, int(z)))
        v.line([0, bottom, base.size[0], bottom], fill=edge, width=max(2, int(z)))
        layer = Image.alpha_composite(layer, veil)
    out = io.BytesIO()
    Image.alpha_composite(base, layer).convert("RGB").save(out, "PNG", optimize=False, compress_level=1)
    return out.getvalue()
