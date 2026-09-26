"""Page images for the Original | Converted preview."""
from __future__ import annotations

import pymupdf


def page_count(pdf: bytes | str) -> int:
    with _open(pdf) as doc:
        return doc.page_count


def render_page(pdf: bytes | str, index: int, width_px: int = 700) -> bytes:
    """PNG of one page scaled to ``width_px`` pixels wide."""
    with _open(pdf) as doc:
        index = max(0, min(index, doc.page_count - 1))
        page = doc[index]
        zoom = width_px / page.rect.width
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
        return pix.tobytes("png")


def _open(pdf: bytes | str) -> pymupdf.Document:
    if isinstance(pdf, (bytes, bytearray)):
        return pymupdf.open(stream=bytes(pdf), filetype="pdf")
    return pymupdf.open(pdf)


_page_cache: dict = {}


def render_highlight(pdf: bytes | str, index: int, width_px: int, sentence: list, word: list,
                     dark: bool = False) -> bytes:
    """PNG of a page with the sentence being read aloud marked, and the word being said boxed.

    ``sentence`` and ``word`` are rectangles in PDF points. The plain page is rendered once and kept, so
    moving the highlight from word to word is quick.
    """
    import io

    from PIL import Image, ImageDraw

    key = (id(pdf), len(pdf), index, width_px)
    if key not in _page_cache:
        if len(_page_cache) > 6:
            _page_cache.clear()
        with _open(pdf) as doc:
            page = doc[max(0, min(index, doc.page_count - 1))]
            zoom = width_px / page.rect.width
            pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), alpha=False)
            _page_cache[key] = (Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGBA"), zoom)
    base, z = _page_cache[key]
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for x0, y0, x1, y1 in sentence:  # soft yellow behind the whole sentence
        d.rectangle([x0 * z - 2, y0 * z - 1, x1 * z + 2, y1 * z + 1], fill=(255, 214, 90, 105))
    edge = (122, 46, 58, 255) if not dark else (200, 60, 80, 255)
    for x0, y0, x1, y1 in word:  # the word being said: a burgundy box
        d.rounded_rectangle([x0 * z - 3, y0 * z - 2, x1 * z + 3, y1 * z + 2], radius=4, fill=(122, 46, 58, 60),
                            outline=edge, width=2)
    out = io.BytesIO()
    Image.alpha_composite(base, layer).convert("RGB").save(out, "PNG", optimize=False, compress_level=1)
    return out.getvalue()
