"""PDF reading: page-type detection, text/layout extraction, images, tables, OCR.

The original PDF is opened read-only and is never modified.
"""
from __future__ import annotations

import concurrent.futures
import io
import itertools
import os
import re
import statistics
import threading
import time
import unicodedata
from collections import Counter
from dataclasses import replace, dataclass, field
from typing import Callable, Optional

import numpy as np
import pymupdf

from ..model import ImageData, OcrWordConfidence, PageInfo, Rect, StyleRange, TableData
from .mathtext import TEX_TEXT_FONT_RE, base_font, is_math_font, is_math_italic, math_text
from .ocr import OcrEngine

ProgressFn = Callable[[str, float], None]

OCR_DPI = 300
SCAN_DPI = 225  # full-page scans: as accurate as 300 dpi on book text, about a third faster
FIGURE_DPI = 200
EQUATION_DPI = 300  # equations are small: render them sharp
CAPTION_RE = re.compile(r"^\s*(fig\.?|figure|figuur|afb\.?|afbeelding|table|tab\.?|tabel|chart|graph|plate)\s*"
                        r"[\dIVXivx]+[a-z]?\b", re.I)


@dataclass
class RawLine:
    """One line of text as read from a page, before structure detection.

    ``bbox`` is in PDF points on the page; ``size`` is the font size; ``source`` says whether it came from the
    PDF's text ("text"), OCR ("ocr") or the scanner's stored text; ``styles`` mark bold, italic, math and links
    within the line; ``conf`` holds OCR word confidences.
    """
    text: str
    bbox: Rect
    size: float
    page: int
    source: str = "text"
    block_no: int = 0
    styles: list[StyleRange] = field(default_factory=list)
    bold: bool = False
    italic: bool = False
    font: str = ""
    conf: list[OcrWordConfidence] = field(default_factory=list)
    baseline: float = 0.0  # 0 when unknown (OCR)
    # small formulas that cannot be written on one line (a fraction, a sum with limits), kept as pictures;
    # the text holds one placeholder character for each
    inline_images: dict[str, ImageData] = field(default_factory=dict)

    @property
    def x0(self) -> float:
        """Left edge (points)."""
        return self.bbox[0]

    @property
    def y0(self) -> float:
        """Top edge (points)."""
        return self.bbox[1]

    @property
    def x1(self) -> float:
        """Right edge (points)."""
        return self.bbox[2]

    @property
    def y1(self) -> float:
        """Bottom edge (points)."""
        return self.bbox[3]

    @property
    def height(self) -> float:
        """Height of the line's box (points)."""
        return self.bbox[3] - self.bbox[1]


@dataclass
class RawFigure:
    """A picture on a page (a photo, graph or formula kept as an image) with where it was."""
    bbox: Rect
    image: ImageData


@dataclass
class RawTable:
    """A table found on a page, with where it was."""
    bbox: Rect
    table: TableData


@dataclass
class RawPage:
    """Everything read from one page: its lines, figures and tables, and facts about the page."""
    info: PageInfo
    lines: list[RawLine] = field(default_factory=list)
    figures: list[RawFigure] = field(default_factory=list)
    tables: list[RawTable] = field(default_factory=list)


@dataclass
class RawDocument:
    """The whole PDF as read: its pages, title, author, bookmarks (level, title, page) and warnings for the user."""
    pages: list[RawPage]
    title: str = ""
    author: str = ""
    toc: list[tuple[int, str, int]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- helpers

def _area(r: Rect) -> float:
    """Area of a rectangle (0 when it is empty)."""
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _intersect(a: Rect, b: Rect) -> Rect:
    """The overlap of two rectangles (may be empty: check with :func:`_area`)."""
    return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))


def overlap_ratio(inner: Rect, outer: Rect) -> float:
    """Fraction of ``inner`` covered by ``outer``."""
    a = _area(inner)
    return _area(_intersect(inner, outer)) / a if a else 0.0


def _union(a: Rect, b: Rect) -> Rect:
    """The smallest rectangle around two rectangles."""
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _expand(r: Rect, d: float) -> Rect:
    """A rectangle grown by ``d`` points on every side."""
    return (r[0] - d, r[1] - d, r[2] + d, r[3] + d)


def _is_bold_font(name: str, flags: int) -> bool:
    """Whether a font is bold, from its flags or its name."""
    return bool(flags & 16) or bool(re.search(r"bold|black|heavy|semibold|demi", name, re.I))


def _is_italic_font(name: str, flags: int) -> bool:
    """Whether a font is italic, from its flags or its name."""
    return bool(flags & 2) or bool(re.search(r"italic|oblique", name, re.I))


def render_clip(page: pymupdf.Page, rect: Rect, dpi: int = FIGURE_DPI) -> ImageData:
    """A part of a page as a PNG picture (for figures and formulas kept as images)."""
    pix = page.get_pixmap(clip=pymupdf.Rect(rect), dpi=dpi, alpha=False)
    return ImageData(pix.tobytes("png"), "png", pix.width, pix.height)


# --------------------------------------------------------------------------- detection

def image_boxes(page: pymupdf.Page, **kw) -> list[tuple[Rect, dict]]:
    """Image placements in page coordinates (rotated pages included)."""
    m = page.rotation_matrix
    out = []
    for info in page.get_image_info(**kw):
        r = pymupdf.Rect(info["bbox"]) * m if page.rotation else pymupdf.Rect(info["bbox"])
        out.append((tuple(r), info))
    return out


def image_coverage(page: pymupdf.Page, grid: int = 40) -> float:
    """Fraction of the page covered by images (union, so tiled scans count once)."""
    rect = page.rect
    if rect.width <= 0 or rect.height <= 0:
        return 0.0
    covered = [[False] * grid for _ in range(grid)]
    for bbox, _info in image_boxes(page):
        x0, y0, x1, y1 = _intersect(bbox, tuple(rect))
        if x1 <= x0 or y1 <= y0:
            continue
        gx0 = int((x0 - rect.x0) / rect.width * grid)
        gx1 = int(np.ceil((x1 - rect.x0) / rect.width * grid))
        gy0 = int((y0 - rect.y0) / rect.height * grid)
        gy1 = int(np.ceil((y1 - rect.y0) / rect.height * grid))
        for gy in range(max(0, gy0), min(grid, gy1)):
            row = covered[gy]
            for gx in range(max(0, gx0), min(grid, gx1)):
                row[gx] = True
    return sum(sum(r) for r in covered) / (grid * grid)


def has_invisible_text(page: pymupdf.Page) -> bool:
    """True when the page carries an OCR text layer (text drawn invisibly over a scan)."""
    try:
        spans = page.get_texttrace()
    except Exception:
        return False
    invisible = sum(len(s.get("chars", ())) for s in spans if s.get("type") == 3)
    total = sum(len(s.get("chars", ())) for s in spans)
    return total > 0 and invisible > 0.8 * total


def classify_page(page: pymupdf.Page) -> str:
    """Return "text", "scanned" or "mixed" for one page.

    A page whose area is (almost) entirely covered by images is a scan, even
    when a scanner or copier added an invisible OCR text layer on top.
    """
    text = page.get_text("text")
    chars = len(re.sub(r"\s", "", text))
    coverage = image_coverage(page)
    if coverage > 0.7 and (chars < 25 or has_invisible_text(page)):
        return "scanned"
    if chars < 25 and coverage > 0.3:
        return "scanned"
    if chars < 25 and coverage <= 0.3:
        # Could be a vector-drawn page or a blank page. Treat as text.
        return "text"
    if coverage > 0.5 and chars < 200:
        return "mixed"
    return "text"


# --------------------------------------------------------------------------- text pages

def _normalise_rotation(page: pymupdf.Page) -> None:
    """Undo a page's display rotation (in memory only) when its text runs horizontally without it.

    A normal text page stored with /Rotate 90 would otherwise be read sideways. Scans
    (whose image is stored sideways) keep their rotation, which makes them upright.
    """
    if not page.rotation:
        return
    horizontal = vertical = 0
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines", []):
            n = sum(len(s["text"]) for s in l["spans"])
            if abs(l["dir"][1]) < 0.1:
                horizontal += n
            else:
                vertical += n
    if horizontal > 50 and horizontal > 3 * vertical and not has_invisible_text(page):
        page.set_rotation(0)  # the document is opened from the file and never saved


def _page_mapper(page: pymupdf.Page):
    """Map text coordinates to the page as displayed.

    PyMuPDF reports text positions of a rotated page (/Rotate 90, 180, 270) in
    the unrotated frame; everything else here works on the displayed page.
    """
    if not page.rotation:
        return (lambda r: tuple(r)), (lambda d: tuple(d))
    m = page.rotation_matrix
    origin = pymupdf.Point(0, 0) * m

    def rect(r) -> Rect:
        """A rectangle in unrotated page coordinates."""
        return tuple(pymupdf.Rect(r) * m)

    def direction(d) -> tuple[float, float]:
        """A text direction in unrotated page coordinates."""
        q = pymupdf.Point(d) * m - origin
        return (q.x, q.y)

    return rect, direction


@dataclass
class _Span:
    """A run of characters in one font from the PDF's text, with its box and baseline (points)."""
    text: str
    bbox: Rect
    baseline: float
    size: float
    font: str
    flags: int
    block_no: int

    @property
    def x0(self) -> float:
        """Left edge (points)."""
        return self.bbox[0]

    @property
    def x1(self) -> float:
        """Right edge (points)."""
        return self.bbox[2]

    @property
    def mid_y(self) -> float:
        """Vertical middle of the span's box (points)."""
        return (self.bbox[1] + self.bbox[3]) / 2


# accents typeset above a letter as a separate glyph -> the combining character for that letter
ACCENTS = {"˜": "\u0303", "~": "\u0303", "ˆ": "\u0302", "^": "\u0302", "¯": "\u0304", "ˉ": "\u0304",
           "˙": "\u0307", "¨": "\u0308", "ˇ": "\u030c", "´": "\u0301", "`": "\u0300", "˘": "\u0306",
           "˚": "\u030a", "→": "\u20d7", "\u20d7": "\u20d7", "\u0303": "\u0303", "\u0302": "\u0302",
           "\u0304": "\u0304", "\u0307": "\u0307", "\u0308": "\u0308"}


def _is_accent(sp: "_Span") -> bool:
    """Whether a span is only a loose accent mark (placed over a letter by position in some PDFs)."""
    t = sp.text.strip()
    return bool(t) and len(t) <= 3 and all(c in ACCENTS or c.isspace() for c in t) and not t.startswith("→")


def _font_family(font: str) -> str:
    """'ABCDEF+NimbusRomNo9L-Regu' -> 'nimbusromno9l', 'CMR10' -> 'cmr'."""
    name = base_font(font).split("-")[0].split(",")[0]
    return re.sub(r"\d+$", "", name).lower()


SPACING_ACCENTS = {"¨": "\u0308", "´": "\u0301", "`": "\u0300", "ˆ": "\u0302", "˜": "\u0303", "ˇ": "\u030c",
                   "˘": "\u0306", "˚": "\u030a", "¸": "\u0327"}
# only where a letter can carry that accent ("don´t" keeps its apostrophe-like mark)
SPACING_ACCENT_RE = re.compile("([¨´ˆ])([AEIOUYaeiouy])|(˜)([AONaon])|(ˇ)([CSZRENcszren])|(˘)([AGUagu])|(˚)([AUau])|"
                               "(¸)([CSTcst])")
LEADER_RE = re.compile(r"\s*(?:\.\s?){5,}\s*(?=\S*\s*$)")


def _replace_run(text: str, styles: list[StyleRange], start: int, end: int, repl: str
                 ) -> tuple[str, list[StyleRange]]:
    """Replace text[start:end] with ``repl`` and move the style ranges along with the text."""
    delta = len(repl) - (end - start)

    def at(i: int) -> int:
        """Where position ``i`` ends up after the replacement."""
        return i if i <= start else (start + len(repl) if i < end else i + delta)
    moved = [replace(st, start=at(st.start), end=at(st.end)) for st in styles]
    return text[:start] + repl + text[end:], [st for st in moved if st.end > st.start]


def _unspace(text: str, styles: list[StyleRange], positions: list[tuple[int, float]],
             boxes: list[tuple[float, float]]) -> tuple[str, list[StyleRange]]:
    """'H I G H L I G H T S' -> 'HIGHLIGHTS': a letter-spaced heading, where wider gaps part the words."""
    pts = sorted(positions)
    letters = sorted(boxes)
    if len(letters) == len(pts):  # one box per letter: measure the white space between them
        steps = [b[0] - a[1] for a, b in zip(letters, letters[1:])]
    else:
        steps = [b[1] - a[1] for a, b in zip(pts, pts[1:])]
    typical = sorted(steps)[len(steps) // 3]
    wide = {b[0] for (a, b), d in zip(zip(pts, pts[1:]), steps) if d > 1.4 * typical + 0.3}
    new_index: dict[int, int] = {}
    out = ""
    for i, c in enumerate(text):
        if c.isspace():
            continue
        if i in wide and out:
            out += " "
        new_index[i] = len(out)
        out += c
    lead = len(text) - len(text.lstrip())

    def at(i: int) -> int:
        """Where position ``i`` of the old text ends up in the new text."""
        keys = [k for k in new_index if k >= i]
        return new_index[min(keys)] if keys else len(out)
    moved = [replace(st, start=at(st.start), end=at(st.end) if st.end < len(text) else len(out)) for st in styles]
    return " " * lead + out, [st for st in moved if st.end > st.start]


def _rotated_blocks(page: pymupdf.Page, taken: list[Rect]) -> list[RawFigure]:
    """Text set sideways (a landscape table, a rotated diagram) cannot be reflowed; keep it as a picture.

    Single rotated lines are left out: those are margin stamps (arXiv identifiers) or axis titles.
    """
    to_page, to_dir = _page_mapper(page)
    boxes: list[tuple[Rect, str]] = []
    try:
        blocks = page.get_text("dict")["blocks"]
    except Exception:
        return []
    for block in blocks:
        for line in block.get("lines", []):
            dx, dy = to_dir(line["dir"])
            if abs(dy) <= 0.1 and dx >= 0:
                continue
            text = "".join(sp["text"] for sp in line["spans"]).strip()
            if text:
                boxes.append((to_page(line["bbox"]), text, (round(dx), round(dy))))
    boxes = [x for x in boxes if not any(overlap_ratio(x[0], r) > 0.5 for r in taken)]
    clusters: list[list] = [[b, [t], [d]] for b, t, d in boxes]
    merged = True
    while merged:
        merged = False
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                if _area(_intersect(_expand(clusters[i][0], 22), clusters[j][0])) > 0:
                    clusters[i][0] = _union(clusters[i][0], clusters[j][0])
                    clusters[i][1] += clusters[j][1]
                    clusters[i][2] += clusters[j][2]
                    del clusters[j]
                    merged = True
                    break
            if merged:
                break
    out: list[RawFigure] = []
    for rect, texts, dirs in clusters:
        if len(texts) < 3:
            continue
        try:
            for d in page.get_drawings():  # the rules of a rotated table
                r = tuple(d["rect"])
                if _area(_intersect(_expand(rect, 6), r)) > 0 and _area(r) < 4 * _area(rect):
                    rect = _union(rect, r)
        except Exception:
            pass
        img = render_clip(page, _expand(rect, 3))
        # turn it so that its text reads left to right
        direction = Counter(dirs).most_common(1)[0][0]
        angle = {(0, -1): -90, (0, 1): 90, (-1, 0): 180}.get(direction, 0)
        if angle:
            try:
                from PIL import Image
                im = Image.open(io.BytesIO(img.data)).rotate(angle, expand=True)
                buf = io.BytesIO()
                im.save(buf, "PNG")
                img = ImageData(buf.getvalue(), "png", im.width, im.height)
                rect = (rect[0], rect[1], rect[0] + (rect[3] - rect[1]), rect[1] + (rect[2] - rect[0])) \
                    if abs(angle) == 90 else rect
            except Exception:
                pass
        img.kind = "figure"
        img.alt = " ".join(texts)
        out.append(RawFigure(rect, img))
    return out


def _join_drop_caps(spans: list[_Span]) -> list[_Span]:
    """A drop cap (one large capital at the start of an article, several lines tall) is put back in front of
    the rest of its word ("M" + "ichael"), instead of being read as a line of its own that swallows the text
    beside it. Only a single letter at least 2.5 times the text size counts, with lower-case text starting just
    right of its top."""
    sizes = Counter()
    for sp in spans:
        sizes[round(sp.size)] += len(sp.text.strip())
    if not sizes:
        return spans
    body = sizes.most_common(1)[0][0]
    out = list(spans)
    for cap in spans:
        letter = cap.text.strip()
        if len(letter) != 1 or not letter.isalpha() or not letter.isupper() or cap.size < 2.5 * body:
            continue
        top, height = cap.bbox[1], cap.bbox[3] - cap.bbox[1]
        beside = [sp for sp in out if sp is not cap and sp.text[:1].islower() and sp.size < cap.size / 2
                  and -1 <= sp.x0 - cap.x1 < 3 * sp.size and top - 0.2 * height <= sp.bbox[1] <= top + 0.5 * height]
        if not beside:
            continue
        first = min(beside, key=lambda sp: (sp.bbox[1], sp.x0))
        out[out.index(first)] = replace(first, text=letter + first.text)
        out.remove(cap)
    return out


def _false_spaces(chars: list[dict], size: float, known_word: Optional[Callable[[str], bool]]) -> set[int]:
    """Indices of spaces in one line of the PDF's text that split a word ("o f", "com puter", "W hen"), as the text
    layers of some scanned articles have: there is hardly any room for them (a real space on the line leaves
    about twice as much), and taking them out makes a known word, from pieces that are not both words."""
    if known_word is None:
        return set()
    gaps: list[tuple[int, int, float]] = []  # (first space, next letter, room between the letters around it)
    prev = None
    i = 0
    while i < len(chars):
        if chars[i]["c"].isspace():
            j = i
            while j < len(chars) and chars[j]["c"].isspace():
                j += 1
            if prev is not None and j < len(chars):
                gaps.append((i, j, chars[j]["bbox"][0] - chars[prev]["bbox"][2]))
            i = j
            continue
        prev = i
        i += 1
    if len(gaps) < 3:
        return set()
    typical = statistics.median(g for _, _, g in gaps)
    if typical < 0.2 * size:
        return set()  # a tightly set line: no room to tell false spaces from real ones

    def piece(k: int, step: int) -> str:
        """The run of letters from index ``k`` going left (-1) or right (+1)."""
        out = ""
        while 0 <= k < len(chars) and chars[k]["c"].isalpha():
            out = out + chars[k]["c"] if step > 0 else chars[k]["c"] + out
            k += step
        return out

    def word(w: str) -> bool:
        return len(w) > 1 or w in "aAI"

    def lone(w: str, other: str) -> bool:
        """A single letter that is not a word by itself ("o f", "b y", "j ournals", "W hen")."""
        return len(w) == 1 and not word(w) and (w.islower() or (len(other) > 1 and other.islower()))

    drop: set[int] = set()
    for start, nxt, gap in gaps:
        left, right = piece(start - 1, -1), piece(nxt, 1)
        if not left or not right:
            continue
        # a lone letter can't stand by itself, so its space may be as wide as a real one (the text layer spaces
        # letters evenly); anything else must have clearly less room than the spaces around it
        loose = lone(left, right) or lone(right, left)
        if gap >= 0.3 * size or (not loose and (gap >= 0.5 * typical or gap >= 0.25 * size)):
            continue
        both_words = word(left) and word(right) and known_word(left) and known_word(right)
        if not both_words and known_word(left + right):
            drop.update(range(start, nxt))
    return drop


def _page_spans(page: pymupdf.Page, known_word: Optional[Callable[[str], bool]] = None) -> list[_Span]:
    """Every horizontal run of text on a page, in unrotated page coordinates (rotated text such as margin notes and
    watermarks is left out). With ``known_word``, spaces that split a word in the PDF's text are taken out
    (see :func:`_false_spaces`).
    """
    d = page.get_text("rawdict", flags=pymupdf.TEXTFLAGS_RAWDICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
    to_page, to_dir = _page_mapper(page)
    spans: list[_Span] = []
    for bno, block in enumerate(d["blocks"]):
        if block.get("type", 0) != 0:
            continue
        for line in block["lines"]:
            dx, dy = to_dir(line["dir"])
            if abs(dy) > 0.1 or dx < 0:  # rotated text (margins, watermarks)
                continue
            line_chars = [c for span in line["spans"] for c in span.get("chars", [])]
            size = max((span["size"] for span in line["spans"]), default=10.0)
            false = {id(line_chars[k]) for k in _false_spaces(line_chars, size, known_word)}
            for span in line["spans"]:
                chars = [c for c in span.get("chars", []) if id(c) not in false]
                t = "".join(c["c"] for c in chars)
                if not t or not t.strip():
                    continue  # word gaps are recovered from positions
                # a leading space can keep the position of the index before it: measure from the first letter
                first = next(c for c in chars if not c["c"].isspace())
                ox, oy = first["origin"]
                baseline = to_page((ox, oy, ox, oy))[1]
                bbox = span["bbox"]
                if chars[0]["c"].isspace():
                    ink = [c["bbox"] for c in chars if not c["c"].isspace()]
                    bbox = (min(b[0] for b in ink), min(b[1] for b in ink), max(b[2] for b in ink),
                            max(b[3] for b in ink))
                spans.append(_Span(t.replace("\u00a0", " "), to_page(bbox), baseline, span["size"],
                                   span["font"], span["flags"], bno))
    return spans


def _attach_small(sp: _Span, rows: list[dict], rules: Optional[list[Rect]], math_like: frozenset = frozenset()) -> bool:
    """Put a sub-/superscript, limit or fraction part on the line it belongs to; False if none fits.
    ``math_like``: ids of small spans in a text font that are part of a formula (they touch a maths span)."""
    # maths indices and limits can sit a little apart from their line; small print in the text font (a
    # footnote marker, 'th') follows its word directly, and a smaller line beyond a column gutter is not part
    # of it at all
    math = is_math_font(sp.font) or bool(re.match(r"^(CMEX|MTEX|TXEX|PXEX|RMTEX)", base_font(sp.font), re.I)) \
        or id(sp) in math_like
    if not math and len(sp.text.strip()) > 12:
        return False

    def nearest(expand: float, key) -> Optional[dict]:
        """The row a small span most likely belongs to (within ``expand`` extra font sizes), ranked by ``key``."""
        best, best_d = None, None
        for row in rows:
            lo = row["baseline"] - (1.05 + expand) * row["size"]
            hi = row["baseline"] + (0.5 + expand) * row["size"]
            reach = (1.5 if math else 0.6) * row["size"]
            if lo <= sp.mid_y <= hi and row["x0"] - reach <= sp.x0 <= row["x1"] + reach:
                d = key(row)
                if best is None or d < best_d:
                    best, best_d = row, d
        return best

    best = nearest(0.0, lambda row: abs(sp.mid_y - (row["baseline"] - 0.3 * row["size"])))
    # the numerator or denominator of a small fraction in running text belongs to the line that holds the
    # fraction bar, not to the line above or below (a display fraction has lines of its own above and below)
    bar = next((r for r in rules or [] if r[0] - 1 <= (sp.x0 + sp.x1) / 2 <= r[2] + 1 and r[2] - r[0] < 20 * sp.size
                and (0 <= r[1] - sp.bbox[3] < 0.9 * sp.size or 0 <= sp.bbox[1] - r[3] < 0.9 * sp.size)), None)
    if bar is not None:
        bar_y = (bar[1] + bar[3]) / 2
        own_part = best is not None and abs(best["baseline"] - bar_y) < 1.2 * best["size"] and \
            (best["baseline"] < bar_y) == (sp.mid_y < bar_y)
        if not own_part:
            best = nearest(0.4, lambda row: abs(bar_y - (row["baseline"] - 0.25 * row["size"]))) or best
    if best is None:
        return False
    best["spans"].append(sp)
    best["x0"] = min(best["x0"], sp.x0)
    best["x1"] = max(best["x1"], sp.x1)
    return True


def _rows(spans: list[_Span], rules: Optional[list[Rect]] = None) -> list[list[_Span]]:
    """Group a page's spans into lines by baseline.

    Full-size spans form lines within their PDF text block. Sub- and superscripts (smaller type, shifted up
    or down) join the line they belong to, even when the PDF stores them in a block or line of their own
    (e.g. W with both a sub- and a superscript).
    """
    main: dict[int, float] = {}
    by_block: dict[int, Counter] = {}
    for sp in spans:
        by_block.setdefault(sp.block_no, Counter())[round(sp.size, 1)] += len(sp.text.strip()) or 1
    page_sizes = Counter()
    for c in by_block.values():
        page_sizes.update(c)
    page_main = page_sizes.most_common(1)[0][0] if page_sizes else 10.0
    for bno, c in by_block.items():
        main[bno] = c.most_common(1)[0][0]

    def is_small(sp: _Span) -> bool:
        """Whether a span is small (an index, accent or big math sign) and is placed by position instead of by
        baseline.
        """
        if _is_accent(sp):
            return True  # an accent over a letter belongs to that letter's line
        if re.match(r"^(CMEX|MTEX|TXEX|PXEX|RMTEX)", base_font(sp.font), re.I):
            return True  # big brackets and operators hang from the top: place them by position
        return sp.size < main[sp.block_no] * 0.85 or (
            sp.size < page_main * 0.8 and len(sp.text.strip()) <= 12)

    big = sorted((sp for sp in spans if not is_small(sp)), key=lambda sp: (round(sp.baseline), sp.x0))
    small = sorted((sp for sp in spans if is_small(sp)), key=lambda sp: (sp.baseline, sp.x0))
    rows: list[dict] = []

    def join(sp: _Span, by_box: bool) -> bool:
        """Put a span into an existing row when it lines up with it (``by_box``: by its box instead of its
        baseline); False when it starts a new row.
        """
        for row in rows:
            size = max(sp.size, row["size"])
            if by_box:
                # PyMuPDF sometimes reports a symbol's baseline at the height of a neighbouring index;
                # its box still sits where the characters of its line do
                if sp.text.strip() in ("√", "∛", "∜"):
                    # a radical sign's box sits high; it belongs to the line of the radicand right after it
                    if not any(abs(o.x0 - sp.x1) < 1.5 and o.bbox[1] >= sp.bbox[1] - 1 for o in row["spans"]):
                        continue
                elif not row["baseline"] - 0.8 * size <= sp.mid_y <= row["baseline"] + 0.05 * size:
                    continue
            elif abs(sp.baseline - row["baseline"]) > 0.25 * size:
                continue
            if any(sp.x0 < o.x1 - 1 and o.x0 < sp.x1 - 1 for o in row["spans"]):
                continue
            # the PDF may split one line over several blocks; a column gutter is wider than a word gap
            # (formula pieces can be spaced further apart; plain words next to a narrow gutter cannot)
            reach = (1.6 if is_math_font(sp.font) or any(is_math_font(o.font) for o in row["spans"]) else 0.7) \
                * sp.size
            near = -1 <= sp.x0 - row["x1"] < reach or -1 <= row["x0"] - sp.x1 < reach \
                or (row["x0"] - 1 <= sp.x0 and sp.x1 <= row["x1"] + 1)  # fills a gap inside the line
            # the same PDF block, but not across a wide empty stretch (labels of side-by-side charts)
            same_block = sp.block_no in row["blocks"] and (sp.x0 - row["x1"] < 5 * sp.size and
                                                           row["x0"] - sp.x1 < 5 * sp.size)
            if same_block or near:
                row["spans"].append(sp)
                row["blocks"].add(sp.block_no)
                row["x0"] = min(row["x0"], sp.x0)
                row["x1"] = max(row["x1"], sp.x1)
                return True
        return False

    # letters first: their baselines are reliable; lone symbols may report a shifted baseline
    wordy = [sp for sp in big if sum(c.isalnum() for c in sp.text) >= 2]
    lone = [sp for sp in big if sum(c.isalnum() for c in sp.text) < 2]
    deferred: list[_Span] = []
    for group in (wordy, lone):
        for sp in group:
            if not join(sp, False):
                if group is lone:
                    deferred.append(sp)
                else:
                    rows.append({"baseline": sp.baseline, "size": sp.size, "spans": [sp], "blocks": {sp.block_no},
                                 "x0": sp.x0, "x1": sp.x1})
    for sp in deferred:
        if not join(sp, True):
            rows.append({"baseline": sp.baseline, "size": sp.size, "spans": [sp], "blocks": {sp.block_no},
                         "x0": sp.x0, "x1": sp.x1})
    # pieces of one line that only met once the formulas between them were placed
    changed = True
    while changed:
        changed = False
        for i, a in enumerate(rows):
            for b in rows[i + 1:]:
                size = max(a["size"], b["size"])
                if abs(a["baseline"] - b["baseline"]) > 0.25 * size:
                    continue
                math_rows = any(is_math_font(o.font) for o in a["spans"] + b["spans"])
                reach = (1.6 if math_rows else 0.7) * size
                touching = a["x0"] - reach <= b["x1"] and b["x0"] - reach <= a["x1"]
                if not touching:
                    # an integral sign with its limits (placed later, by position) can fill the gap
                    g0, g1 = min(a["x1"], b["x1"]), max(a["x0"], b["x0"])
                    fill = sorted((max(g0, o.x0), min(g1, o.x1)) for o in small
                                  if o.x1 > g0 and o.x0 < g1 and abs(o.mid_y - a["baseline"]) < 1.2 * size
                                  and is_math_font(o.font))
                    covered, end = 0.0, g0
                    for f0, f1 in fill:
                        covered += max(0.0, f1 - max(f0, end))
                        end = max(end, f1)
                    touching = bool(fill) and g1 - g0 - covered < 1.6 * size
                clash = any(x.x0 < y.x1 - 1 and y.x0 < x.x1 - 1 for x in a["spans"] for y in b["spans"])
                if touching and not clash:
                    a["spans"] += b["spans"]
                    a["blocks"] |= b["blocks"]
                    a["x0"], a["x1"] = min(a["x0"], b["x0"]), max(a["x1"], b["x1"])
                    rows.remove(b)
                    changed = True
                    break
            if changed:
                break
    for row in rows:
        row["x0"] = min(o.x0 for o in row["spans"])
        row["x1"] = max(o.x1 for o in row["spans"])
    orphans: list[_Span] = list(small)
    # an index set in the text font right against a maths index ("=1" after the "k" of k=1 under a sum) is part
    # of the formula: it is placed like maths
    math_like = frozenset(id(sp) for sp in small if not is_math_font(sp.font) and any(
        is_math_font(o.font) and abs(o.baseline - sp.baseline) < 0.3 * sp.size and
        (abs(o.x1 - sp.x0) < 1.0 or abs(sp.x1 - o.x0) < 1.0) for o in small))
    # repeated, so that a chain of pieces (a sum sign, its index, then the text) grows its line leftwards
    progress = True
    while progress and orphans:
        progress = False
        pending, orphans = orphans, []
        for sp in pending:
            if _attach_small(sp, rows, rules, math_like):
                progress = True
            else:
                orphans.append(sp)
    # second chance for the limits of a sum or the parts of a small fraction in running text, which sit
    # further above or below the line: join the nearest line if it is clearly the closest one
    still: list[_Span] = []
    for sp in orphans:
        cands = []
        for row in rows:
            if row["size"] < sp.size:
                continue
            lo, hi = row["baseline"] - 1.7 * row["size"], row["baseline"] + 1.1 * row["size"]
            if lo <= sp.mid_y <= hi and row["x0"] - row["size"] <= sp.x0 <= row["x1"] + row["size"]:
                cands.append((abs(sp.mid_y - (row["baseline"] - 0.3 * row["size"])), row))
        cands.sort(key=lambda c: c[0])
        if cands and (len(cands) == 1 or cands[1][0] - cands[0][0] > 0.3 * cands[0][1]["size"]) and \
                any(is_math_font(o.font) for o in cands[0][1]["spans"]) and is_math_font(sp.font) or \
                (cands and len(sp.text.strip()) <= 4 and (len(cands) == 1 or cands[1][0] - cands[0][0] > 0.3 * cands[0][1]["size"])
                 and any(re.match(r"^(CMEX|MTEX)", base_font(o.font), re.I) or is_math_font(o.font) for o in cands[0][1]["spans"])):
            cands[0][1]["spans"].append(sp)
        else:
            still.append(sp)
    orphans = still
    small_rows: list[dict] = []
    for sp in orphans:
        for row in small_rows:
            if abs(sp.baseline - row["baseline"]) <= 0.3 * row["size"] and sp.x0 - row["x1"] < 3 * row["size"] \
                    and row["x0"] - sp.x1 < 3 * row["size"]:
                row["spans"].append(sp)
                row["x0"] = min(row["x0"], sp.x0)
                row["x1"] = max(row["x1"], sp.x1)
                break
        else:
            small_rows.append({"baseline": sp.baseline, "size": sp.size, "spans": [sp], "x0": sp.x0, "x1": sp.x1})
    out = []
    for row in rows + small_rows:
        row["spans"].sort(key=lambda sp: sp.x0)
        out.append(row["spans"])
    return out


BIG_OPERATORS = set("∑∏∫∮⋃⋂⨁⨂⨀⨆⨄⋀⋁∐")
_placeholders = itertools.count()


def new_placeholder() -> str:
    """A private-use character standing for one inline formula picture."""
    return chr(0xF0000 + next(_placeholders) % 0xFFFD)



def _stacks(row: list[_Span], rules: list[Rect], baseline: float, size: float) -> list[tuple[Rect, list[_Span], str]]:
    """Parts of a text line that are stacked vertically: fractions and big operators with limits.

    Returns (region, spans, text) for each; these cannot be written as text on one line.
    """
    found: list[tuple[Rect, list[_Span], str]] = []

    def cx(sp: _Span) -> float:
        """Horizontal centre of a span."""
        return (sp.x0 + sp.x1) / 2

    for r in rules:
        if not (baseline - 1.3 * size <= r[1] <= baseline + 0.4 * size) or r[2] - r[0] > 14 * size:
            continue
        # numerator and denominator: next to the bar (not the limits of a sum on the line below)
        above = [sp for sp in row if r[0] - 1.5 <= sp.x0 and sp.x1 <= r[2] + 1.5 and -1.5 <= r[1] - sp.bbox[3] < 1.2 * size]
        below = [sp for sp in row if r[0] - 1.5 <= sp.x0 and sp.x1 <= r[2] + 1.5 and -1.5 <= sp.bbox[1] - r[3] < 1.2 * size]
        if above and below:
            spans = above + below
            rect = _union(r, (min(sp.bbox[0] for sp in spans), min(sp.bbox[1] for sp in spans),
                              max(sp.bbox[2] for sp in spans), max(sp.bbox[3] for sp in spans)))
            text = "(" + "".join(sp.text.strip() for sp in above) + ")/(" + \
                "".join(sp.text.strip() for sp in below) + ")"
            found.append((rect, spans, text))
    for op in row:
        t = math_text(op.font, op.text).strip() if is_math_font(op.font) else op.text.strip()
        if t not in BIG_OPERATORS:
            continue
        # limits set under and over the sign (not beside it, as the scripts of an integral in running text)
        lower = [sp for sp in row if sp is not op and op.x0 - 2 <= cx(sp) <= op.x1 + 2 and sp.x0 < op.x1 - 1
                 and sp.bbox[1] >= op.bbox[3] - 0.35 * size]
        upper = [sp for sp in row if sp is not op and op.x0 - 2 <= cx(sp) <= op.x1 + 2 and sp.x0 < op.x1 - 1
                 and sp.bbox[3] <= op.bbox[1] + 0.35 * size]
        if lower or upper:
            spans = [op] + lower + upper
            rect = (min(sp.bbox[0] for sp in spans), min(sp.bbox[1] for sp in spans),
                    max(sp.bbox[2] for sp in spans), max(sp.bbox[3] for sp in spans))
            text = t + ("_{" + "".join(sp.text.strip() for sp in lower) + "}" if lower else "") + \
                ("^{" + "".join(sp.text.strip() for sp in upper) + "}" if upper else "")
            found.append((rect, spans, text))
    # overlapping stacks (a fraction under a sum) become one picture
    merged: list[list] = []
    for rect, spans, text in sorted(found, key=lambda f: f[0][0]):
        for m in merged:
            if rect[0] < m[0][2] + 0.5 and m[0][0] < rect[2] + 0.5:
                m[0] = _union(m[0], rect)
                m[1] = m[1] + [sp for sp in spans if sp not in m[1]]
                m[2] = m[2] + " " + text
                break
        else:
            merged.append([rect, list(spans), text])
    # big brackets hugging a stack belong to it
    for m in merged:
        for sp in row:
            if sp in m[1] or not re.match(r"^(CMEX|MTEX|TXEX|PXEX)", base_font(sp.font), re.I):
                continue
            if (0 <= m[0][0] - sp.x1 < 2 or 0 <= sp.x0 - m[0][2] < 2) and sp.bbox[1] <= m[0][1] + 2:
                m[0] = _union(m[0], sp.bbox)
                m[1].append(sp)
    return [(tuple(m[0]), m[1], m[2]) for m in merged]


def _group_scripts(row: list[_Span], baseline: float, ref_size: float, skip: dict) -> list[_Span]:
    """Order a row's spans for reading. A subscript and a superscript on the same symbol overlap in x
    (a_{i1 i2}^{(k)}); taken strictly by position their characters would interleave. Each cluster of scripts is
    written subscript first, then superscript."""
    out: list[_Span] = []
    cluster: list[_Span] = []

    def flush() -> None:
        """Write out the collected indices; a sub- and superscript on the same character stay together."""
        subs = [sp for sp in cluster if sp.baseline > baseline]
        sups = [sp for sp in cluster if sp.baseline <= baseline]
        if subs and sups and min(sp.x0 for sp in sups) < max(sp.x1 for sp in subs) - 0.5 and \
                min(sp.x0 for sp in subs) < max(sp.x1 for sp in sups) - 0.5:
            out.extend(subs + sups)
        else:
            out.extend(cluster)
        cluster.clear()

    for sp in row:
        script = sp.size < ref_size * 0.85 and id(sp) not in skip and abs(sp.baseline - baseline) > 0.08 * ref_size
        if script:
            cluster.append(sp)
        else:
            flush()
            out.append(sp)
    flush()
    return out


def _text_lines(page: pymupdf.Page, pno: int, known_word: Optional[Callable[[str], bool]] = None) -> list[RawLine]:
    """The text lines of a page, with bold/italic/math styles, formulas recognised and indices placed.
    ``known_word`` is used to take out spaces that split words, only on a page whose text lies over a picture of
    the whole page: text made by OCR software (a typeset page spaces symbols and initials tightly on purpose)."""
    if known_word is not None and image_coverage(page) < 0.9:
        known_word = None
    spans = _join_drop_caps(_page_spans(page, known_word))
    try:
        rules = [tuple(d["rect"]) for d in page.get_drawings()
                 if d["rect"].height < 1.6 and 2 < d["rect"].width]
    except Exception:
        rules = []
    # the page's text typeface; TeX text fonts (CMR...) in a Times/Arial document are formula parts
    fam = Counter()
    for sp in spans:
        if not is_math_font(sp.font):
            fam[_font_family(sp.font)] += len(sp.text.strip())
    body_family = fam.most_common(1)[0][0] if fam else ""
    tex_body = bool(TEX_TEXT_FONT_RE.match(body_family))

    lines: list[RawLine] = []
    for row in _rows(spans, rules):
        bno = Counter(sp.block_no for sp in row).most_common(1)[0][0]
        # the text size of the row; a bullet or symbol drawn in a much larger font does not count
        common = Counter()
        for sp in row:
            common[round(sp.size, 1)] += len(sp.text.strip())
        main = common.most_common(1)[0][0] if common else 0
        max_size = max((sp.size for sp in row if not (len(sp.text.strip()) == 1 and not sp.text.strip().isalnum()
                                                         and sp.size > 1.3 * main)), default=0) \
            or max(sp.size for sp in row)
        # the baseline of the full-size text (not of such a large bullet, which would make the text beside it
        # look like superscript)
        full = [sp for sp in row if sp.size >= max_size * 0.85]
        weights = Counter()
        for sp in full:
            weights[round(sp.baseline, 1)] += len(sp.text.strip()) or 1
        baseline = weights.most_common(1)[0][0] if weights else row[0].baseline
        text = ""
        styles: list[StyleRange] = []
        weighted = Counter()
        bold_chars = italic_chars = 0
        fonts = Counter()
        # what counts as smaller type: symbols of a maths font can be set larger than the text around
        # them (ϕ at 9.7 pt in 8 pt text), which must not turn that text into superscript
        on_line = [sp for sp in row if abs(sp.baseline - baseline) < 0.1 * sp.size]
        line_sizes = Counter()
        for sp in on_line:
            line_sizes[round(sp.size, 1)] += len(sp.text.strip())
        line_main = line_sizes.most_common(1)[0][0] if line_sizes else max_size
        ref_size = max((sp.size for sp in on_line if sp.size <= 1.15 * line_main), default=0) or max_size
        prev: Optional[_Span] = None
        prev_math = False
        accents = [sp for sp in row if _is_accent(sp)]
        row = [sp for sp in row if not _is_accent(sp)] or row
        positions: list[tuple[int, float]] = []  # (index in text, x centre) of each character
        right_edge = 0.0  # rightmost ink so far (stacked indices end at different points)
        inline_images: dict[str, ImageData] = {}
        stack_of: dict[int, int] = {}
        # (also on lines without a maths font: in a Times document the maths is set in Times italic, and ½ is a
        # small 1 and 2 around a short bar)
        stacks = _stacks(row, rules, baseline, max_size) if rules or any(is_math_font(sp.font) for sp in row) else []
        for k, (_r, members, _t) in enumerate(stacks):
            for sp in members:
                stack_of[id(sp)] = k
        emitted: set[int] = set()
        row = _group_scripts(row, baseline, ref_size, stack_of)
        for sp in row:
            if id(sp) in stack_of:
                k = stack_of[id(sp)]
                if k in emitted:
                    continue
                emitted.add(k)
                rect, members, alt = stacks[k]
                # tight above and below: the neighbouring lines' letters come close to a fraction
                clip = pymupdf.Rect(rect[0] - 0.8, rect[1] - 0.2, rect[2] + 0.8, rect[3] + 0.2)
                try:
                    pix = page.get_pixmap(clip=clip, dpi=EQUATION_DPI, alpha=True)
                except Exception:
                    pix = None
                if pix is None:
                    continue
                ph = new_placeholder()
                inline_images[ph] = ImageData(pix.tobytes("png"), "png", pix.width, pix.height, kind="inline-math",
                                              alt=alt, text_size=float(max_size), descent=clip.y1 - baseline,
                                              width_pt=clip.width)
                if text and not text[-1].isspace() and rect[0] - right_edge > max_size * 0.15:
                    text += " "
                styles.append(StyleRange(len(text), len(text) + 1, math=True))
                text += ph
                positions.append((len(text) - 1, (rect[0] + rect[2]) / 2))
                prev, prev_math = sp, True
                right_edge = max(right_edge, rect[2])
                continue
            math_font = is_math_font(sp.font)
            t = math_text(sp.font, sp.text) if math_font else sp.text
            if not t:
                continue
            small = sp.size < ref_size * 0.85
            # position decides (PyMuPDF's own superscript flag also marks some full-size commas)
            sup = small and (sp.baseline < baseline - 0.12 * max_size or
                             (bool(sp.flags & 1) and sp.baseline < baseline + 0.02 * max_size))
            sub = small and not sup and sp.baseline > baseline + 0.08 * max_size
            if sup or sub:
                t = t.strip()  # "W" + " K" (an index) is W^K, not "W K"
                if not t:
                    continue
            gap = sp.x0 - right_edge if prev is not None else 0
            math = math_font or (not tex_body and bool(TEX_TEXT_FONT_RE.match(_font_family(sp.font)))) \
                or ((sup or sub) and prev_math and gap < 0.2 * max_size)
            # word-per-span layers carry no spaces; formulas and scripts are spaced by position
            if prev is not None and text and not text[-1].isspace() and not t[0].isspace() \
                    and gap > max_size * (0.2 if (sup or sub) else 0.15):
                text += " "
            elif text[-1:] in (",", ";") and t[0].isalpha() and not (sup or sub) and len(text) > 1 \
                    and not text[-2].isdigit():
                text += " "  # "∈ ℝ^h, b": the space after a comma is not always stored as a gap
            start = len(text)
            text += t
            step = (sp.x1 - sp.x0) / max(1, len(t))
            positions += [(start + k, sp.x0 + step * (k + 0.5)) for k, c in enumerate(t) if not c.isspace()]
            bold = _is_bold_font(sp.font, sp.flags) or bool(re.match(r"^(CMBX|CMMIB|CMBSY)", base_font(sp.font)))
            italic = _is_italic_font(sp.font, sp.flags) or (is_math_italic(sp.font) and any(c.isalpha() for c in t))
            n = len(t.strip())
            if not (sup or sub):
                weighted[round(sp.size, 1)] += n
            bold_chars += n if bold else 0
            italic_chars += n if italic else 0
            fonts[sp.font] += n
            if bold or italic or sup or sub or math:
                styles.append(StyleRange(start, len(text), bold, italic, sup, sub, math))
            prev, prev_math = sp, math or (prev_math and (sup or sub))
            right_edge = max(right_edge, sp.x1)
        # accents: a combining mark after the letter underneath (x̂, h̃)
        for acc in sorted(accents, key=lambda a: -(a.x0 + a.x1) / 2):
            if acc in row or not positions:
                continue
            cx = (acc.x0 + acc.x1) / 2
            idx, x = min(positions, key=lambda p: abs(p[1] - cx))
            if abs(x - cx) > max(4.0, acc.size * 0.6):
                continue
            mark = ACCENTS.get(acc.text.strip()[0], "")
            if not mark:
                continue
            k = idx + 1
            text = text[:k] + mark + text[k:]
            styles = [st.moved(0, st.start + (1 if st.start >= k else 0), st.end + (1 if st.end >= k else 0))
                      for st in styles]
            positions = [(i + 1 if i >= k else i, px) for i, px in positions]
        stripped = text.strip()
        if not stripped:
            continue
        # TeX's older fonts write "ö" as a spacing ¨ before the o: join them into one letter
        for m in reversed(list(SPACING_ACCENT_RE.finditer(text))):
            accent, base = [g for g in m.groups() if g]
            letter = unicodedata.normalize("NFC", base + SPACING_ACCENTS[accent])
            text, styles = _replace_run(text, styles, m.start(), m.end(), letter)
        leader = LEADER_RE.search(text)
        if leader:  # "2.1. Results . . . . . . . 12" (a printed table of contents): one short leader
            text, styles = _replace_run(text, styles, leader.start(), leader.end(), " … ")
        if re.fullmatch(r"(?:\S ){4,}\S", stripped) and stripped.replace(" ", "").isalpha() \
                and (stripped.isupper() or len(stripped) >= 15) \
                and not any(st.math or st.superscript or st.subscript for st in styles) \
                and not any(is_math_font(sp.font) for sp in row):
            text, styles = _unspace(text, styles, positions,
                                    [(sp.x0, sp.x1) for sp in row if len(sp.text.strip()) == 1])
        lead = len(text) - len(text.lstrip())
        text = text.strip()
        styles = [st.moved(-lead, max(lead, st.start), min(len(text) + lead, st.end))
                  for st in styles if st.end - lead > 0 and st.start - lead < len(text)]
        total = max(1, len(re.sub(r"\s", "", text)))
        size = weighted.most_common(1)[0][0] if weighted else max_size or 10.0
        bbox = (min(sp.bbox[0] for sp in row), min(sp.bbox[1] for sp in row),
                max(sp.bbox[2] for sp in row), max(sp.bbox[3] for sp in row))
        lines.append(RawLine(
            text=text, bbox=bbox, size=float(size), page=pno, block_no=bno,
            styles=styles, bold=bold_chars / total > 0.6, italic=italic_chars / total > 0.6,
            font=fonts.most_common(1)[0][0] if fonts else "", baseline=baseline,
            inline_images=inline_images,
        ))
    return _merge_same_baseline(lines)


def _continues_line(prev: RawLine, ln: RawLine) -> bool:
    """Whether line ``ln`` is the continuation of ``prev`` on the same visual line (split by fonts or formulas)."""
    gap = ln.x0 - prev.x1
    size = max(prev.size, ln.size)
    has_math = any(st.math for st in prev.styles + ln.styles)
    if has_math and prev.baseline and ln.baseline and abs(prev.baseline - ln.baseline) < 0.25 * size \
            and abs(prev.size - ln.size) < 1.5 and -1 <= gap < 1.6 * size:
        return True  # same baseline: indices and formulas can make the boxes differ in height
    # Fragments of one PyMuPDF block may be far apart in justified text; across
    # blocks a wide gap is more likely a column gutter.
    limit = size * 1.5 if prev.block_no == ln.block_no else max(3.0, size * 0.6)
    if -1 <= gap < limit:
        if abs(prev.y1 - ln.y1) < 2.5 and abs(prev.size - ln.size) < 1.5:
            return True  # same baseline, same size
        if ln.size < prev.size * 0.85 and len(ln.text) <= 8 and ln.y0 >= prev.y0 - 3 and ln.y1 <= prev.y1 + 1:
            return True  # superscript / subscript fragment
    return False


def _merge_same_baseline(lines: list[RawLine]) -> list[RawLine]:
    """Join fragments PyMuPDF reports as separate lines on the same baseline."""
    out: list[RawLine] = []
    for ln in sorted(lines, key=lambda l: l.x0):
        target = None
        for prev in out:
            if prev.page == ln.page and _continues_line(prev, ln):
                target = prev
                break
        if target is None:
            out.append(ln)
            continue
        prev = target
        sep = "" if ln.x0 - prev.x1 < prev.size * 0.15 else " "
        base = len(prev.text) + len(sep)
        prev.text += sep + ln.text
        prev.styles += [s.moved(base) for s in ln.styles]
        prev.inline_images.update(ln.inline_images)
        if ln.size < prev.size * 0.85 and not any(s.superscript or s.subscript for s in ln.styles):
            low = ln.y1 > prev.y1 + 0.5  # hangs below the line: a subscript
            prev.styles.append(StyleRange(base, base + len(ln.text), superscript=not low, subscript=low))
        prev.bbox = _union(prev.bbox, ln.bbox)
    out.sort(key=lambda l: (l.y0, l.x0))
    return out


# --------------------------------------------------------------------------- figures

def _clear_of_text(clip: Rect, rect: Rect, lines: list[RawLine]) -> Rect:
    """Shrink a picture's margin so it does not cut into a text line just above or below it."""
    x0, y0, x1, y1 = clip
    for l in lines:
        if overlap_ratio(l.bbox, rect) > 0.5 or l.x1 <= x0 or l.x0 >= x1:
            continue
        if l.y1 <= rect[1] + 1 and l.y1 > y0:
            y0 = l.y1
        elif l.y0 >= rect[3] - 1 and l.y0 < y1:
            y1 = l.y0
    return (x0, y0, x1, y1)


def _figures(page: pymupdf.Page, doc: pymupdf.Document, lines: list[RawLine],
             exclude: list[Rect], repeated_xrefs: set[int]) -> list[RawFigure]:
    """The pictures on a page (photos, graphs, drawings), leaving out logos repeated on every page, full-page
    backgrounds and areas in ``exclude`` (tables, formulas).
    """
    prect = tuple(page.rect)
    parea = _area(prect)
    regions: list[list] = []  # [rect, xref or 0]
    for bbox, info in image_boxes(page, xrefs=True):
        r = _intersect(bbox, prect)
        if r[2] - r[0] < 12 or r[3] - r[1] < 12:
            continue
        if info.get("xref") in repeated_xrefs:
            continue  # logos repeated on every page
        if _area(r) > 0.9 * parea:
            continue  # background / scanned page image
        regions.append([r, info.get("xref", 0)])
    try:
        clusters = page.cluster_drawings()
    except Exception:
        clusters = []
    for c in clusters:
        r = _intersect(tuple(c), prect)
        w, h = r[2] - r[0], r[3] - r[1]
        if w < 0.08 * (prect[2] - prect[0]) or h < 0.04 * (prect[3] - prect[1]):
            continue  # rules, underlines, small ornaments
        if _area(r) > 0.85 * parea:
            continue  # page frame / background
        if any(overlap_ratio(r, e) > 0.5 for e in exclude):
            continue  # tables
        inside = [l for l in lines if overlap_ratio(l.bbox, r) > 0.8]
        text_chars = sum(len(l.text) for l in inside)
        # A box that just frames ordinary paragraphs is not a figure.
        if text_chars > 400 and _area(r) / max(1, text_chars) < 60:
            continue
        regions.append([r, 0])

    def merge_overlapping(grow: float) -> None:
        """Join picture regions that touch or overlap (within ``grow`` points) into one figure."""
        merged = True
        while merged:
            merged = False
            for i in range(len(regions)):
                for j in range(i + 1, len(regions)):
                    if _area(_intersect(_expand(regions[i][0], grow), regions[j][0])) > 0:
                        regions[i][0] = _union(regions[i][0], regions[j][0])
                        regions[i][1] = 0
                        del regions[j]
                        merged = True
                        break
                if merged:
                    break

    merge_overlapping(4)

    # absorb labels (axis titles, legends) belonging to the figure; labels are
    # set smaller than body text, so body lines next to a figure are never taken
    sizes = Counter()
    for l in lines:
        sizes[round(l.size)] += len(l.text)
    body_size = sizes.most_common(1)[0][0] if sizes else 10
    for reg in regions:
        for _ in range(3):
            grown = False
            for l in lines:
                if CAPTION_RE.match(l.text):
                    continue
                if overlap_ratio(l.bbox, reg[0]) > 0.5:
                    continue
                near = _area(_intersect(_expand(reg[0], 10), l.bbox)) > 0
                # tick labels ("0.5 1.0 1.5") and a short axis title can be as large as the text
                tick = bool(re.fullmatch(r"[\d.,−\-+%×\s]+", l.text)) or len(l.text.strip()) <= 2 or (
                    len(l.text) <= 20 and len(l.text.split()) <= 2 and not l.text.rstrip().endswith((".", ":"))
                    and reg[0][0] - 5 <= l.x0 and l.x1 <= reg[0][2] + 5)
                if near and len(l.text) < 40 and (l.size < body_size * 0.93 or tick) and \
                        (l.x1 - l.x0) < (reg[0][2] - reg[0][0]) * 1.05:
                    reg[0] = _union(reg[0], l.bbox)
                    reg[1] = 0
                    grown = True
            if not grown:
                break
    merge_overlapping(0)  # labels taken in may make two regions overlap: one picture, not the same part twice

    figures: list[RawFigure] = []
    for rect, xref in regions:
        has_text = any(overlap_ratio(l.bbox, rect) > 0.5 for l in lines)
        img: Optional[ImageData] = None
        if xref and not has_text:
            try:
                ex = doc.extract_image(xref)
                if ex and ex.get("ext") in ("png", "jpeg", "jpg") and not ex.get("smask"):
                    img = ImageData(ex["image"], "jpeg" if ex["ext"] == "jpg" else ex["ext"],
                                    ex["width"], ex["height"])
            except Exception:
                img = None
        if img is None:
            img = render_clip(page, _clear_of_text(_expand(rect, 2), rect, lines))
        small = (rect[2] - rect[0]) < 40 and (rect[3] - rect[1]) < 40
        # journal logos / "check for updates" badges near the top of the first page
        logo = (page.number == 0 and rect[3] < prect[3] * 0.3 and _area(rect) < 0.05 * parea
                and not has_text)
        img.kind = "decorative" if (small or logo) else "figure"
        figures.append(RawFigure(rect, img))
    return figures


# --------------------------------------------------------------------------- equations

EQ_NUMBER_RE = re.compile(r"^\(\s*[A-Z]?[\dIVX]+(?:[.\-–]\d+)*[a-z]?\s*\)$")
EQ_END_RE = re.compile(r"\s\(\s*[A-Z]?[\dIVX]+(?:[.\-–]\d+)*[a-z]?\s*\)\s*$")
# names that appear as words inside formulas
MATH_WORDS = {"sin", "cos", "tan", "log", "exp", "max", "min", "arg", "argmax", "argmin", "lim", "sup", "inf",
              "det", "diag", "tr", "var", "cov", "mod", "sgn", "softmax", "where", "for", "and", "if", "otherwise",
              "s.t", "with", "all", "subject"}
_NEUTRAL = set("0123456789=+-−–×·∗*/()[]{}|,.;:<>≤≥≈∼~^_'′’!?⋯…%")


def _math_profile(line: RawLine) -> tuple[int, int, int, int]:
    """(maths-font characters, formula-like characters, all characters, ordinary words) of a line."""
    flags = [False] * len(line.text)
    for st in line.styles:
        if st.math:
            for i in range(max(0, st.start), min(len(flags), st.end)):
                flags[i] = True
    math = sum(1 for i, c in enumerate(line.text) if flags[i] and not c.isspace())
    formula = sum(1 for i, c in enumerate(line.text) if not c.isspace() and (
        flags[i] or c in _NEUTRAL or unicodedata.category(c) == "Sm" or "\u0370" <= c <= "\u03ff"))
    total = sum(1 for c in line.text if not c.isspace())
    words = 0
    for m in re.finditer(r"[A-Za-z]+", line.text):
        if any(flags[i] for i in range(m.start(), m.end())):
            continue
        after = line.text[m.end():m.end() + 1]
        tok = m.group()
        if not (re.fullmatch(r"[A-Z]?[a-z]+", tok) or (tok.isupper() and re.search(r"[AEIOUY]", tok))):
            formula += len(tok)  # "ziJi", "JAt", "NH": symbols written next to each other, not a word
            continue
        if len(m.group()) <= 2 or m.group().lower() in MATH_WORDS:
            formula += len(m.group())  # variables set in the text italic (x, y, h), and cos, log, max
            continue
        if after == "(":
            continue  # Attention(...), Softmax(...)
        words += 1
    return math, formula, total, words


def _columns(lines: list[RawLine]) -> list[tuple[float, float]]:
    """(left, right) edges of the text columns on a page, from its full-width lines.

    Indented first lines and long formulas are not columns: only lines about as wide as the widest
    running text count, and edges that differ by an indent are merged.
    """
    long = [l for l in lines if len(l.text) >= 45]
    if not long:
        return []
    widths = sorted(l.x1 - l.x0 for l in long)
    wide = widths[int(len(widths) * 0.8)] if len(widths) > 1 else widths[0]
    body = sorted((l for l in long if l.x1 - l.x0 >= 0.85 * wide), key=lambda l: l.x0)
    groups: list[list[RawLine]] = []
    for l in body:
        if groups and l.x0 - groups[-1][-1].x0 < 4:
            groups[-1].append(l)
        else:
            groups.append([l])
    cols: list[tuple[float, float, int]] = []
    for g in groups:
        rights = sorted(l.x1 for l in g)
        cols.append((g[0].x0, rights[len(rights) * 3 // 4], len(g)))
    merged: list[list] = []
    for left, right, n in sorted(cols):
        for m in merged:
            if abs(m[1] - right) < 10 and left - m[0] < 30:  # a first-line indent of the same column
                m[2] += n
                break
        else:
            merged.append([left, right, n])
    return [(m[0], m[1]) for m in merged if m[2] >= 3]


def _equations(page: pymupdf.Page, lines: list[RawLine]) -> tuple[list[RawFigure], list[RawLine]]:
    """Display equations: kept exactly as typeset (a sharp picture), with their text as alt text.

    Returns the equation figures and the remaining text lines.
    """
    if not any(st.math for l in lines for st in l.styles):
        return [], lines
    cols = _columns(lines)
    if not cols:
        cols = [(min(l.x0 for l in lines), max(l.x1 for l in lines))]
    sizes = Counter()
    for l in lines:
        sizes[round(l.size)] += len(l.text)
    body = sizes.most_common(1)[0][0] if sizes else 10

    def column(l: RawLine) -> tuple[float, float]:
        """The text column a line is in (left, right)."""
        left = [c for c in cols if c[0] <= l.x0 + 3 and l.x1 <= c[1] + 0.25 * (c[1] - c[0])]
        return max(left, key=lambda c: c[0]) if left else min(cols, key=lambda c: abs(c[0] - l.x0))

    ordered = sorted(lines, key=lambda l: (l.y0, l.x0))
    gaps = [b.y0 - a.y1 for a, b in zip(ordered, ordered[1:])
            if 0 <= b.y0 - a.y1 < 2 * a.size and abs(a.x0 - b.x0) < 2 and len(a.text) > 40]
    typical_gap = statistics.median(gaps) if gaps else body * 0.3

    def spaced(l: RawLine) -> bool:
        """Extra white space above or below, as TeX puts around display equations."""
        def near(o: RawLine) -> bool:
            """Whether another line overlaps this one horizontally."""
            return o is not l and min(o.x1, l.x1) - max(o.x0, l.x0) > 0
        above = [l.y0 - o.y1 for o in lines if near(o) and o.y1 <= l.y0 + 1]
        below = [o.y0 - l.y1 for o in lines if near(o) and o.y0 >= l.y1 - 1]
        extra = typical_gap + 0.35 * l.size
        return (min(above) if above else 99) > extra or (min(below) if below else 99) > extra

    marked: list[RawLine] = []
    numbers: list[RawLine] = []
    for l in lines:
        if CAPTION_RE.match(l.text) or (l.bold and l.size > body * 1.05) or l.text[:1] in "•◦▪●‣":
            continue  # captions, headings and bullet points are text
        if l.size < body * 0.88:
            continue  # small print (footnotes, notes) keeps its formulas inline
        left, right = column(l)
        width = max(1.0, right - left)
        if EQ_NUMBER_RE.match(l.text.strip()) and l.x0 > left + 0.55 * width:
            numbers.append(l)
            continue
        math, formula, total, words = _math_profile(l)
        if math == 0 or total == 0:
            continue
        indent, gap_right = l.x0 - left, right - l.x1
        end_number = EQ_END_RE.search(l.text)
        if end_number and gap_right < 2 * l.size and len(l.text) > len(end_number.group()) + 2:
            # the equation number shares the line with its formula
            rest = replace(l, text=l.text[:end_number.start()].rstrip())
            m2, f2, t2, w2 = _math_profile(rest)
            if t2 and w2 == 0 and m2 >= 2 and f2 / t2 >= 0.8:
                marked.append(l)
                continue
        set_apart = indent > 1.8 * l.size or (gap_right > 1.8 * l.size and indent > 0.8 * l.size)
        centred = abs(indent - gap_right) < 0.2 * width
        if (formula / total >= 0.6 and set_apart and (words == 0 or (words <= 2 and (centred or spaced(l))))) or \
                (formula / total >= 0.85 and words == 0 and math >= 2 and spaced(l)
                 and l.x1 - l.x0 > 0.35 * width) or \
                (total <= 6 and words == 0 and set_apart):
            marked.append(l)
    # a display equation never shares its line with running text; inline formulas do
    prose = [l for l in lines if _math_profile(l)[3] >= 3]

    candidates = {id(l) for l in marked}

    def inline(l: RawLine) -> bool:
        """Whether a formula-looking line is part of the running text (not a display equation)."""
        left = column(l)[0]
        # the last line of a paragraph that happens to be all formula: it starts where the text above starts
        # and follows it at the normal line distance
        above = [p for p in lines if p is not l and p.y1 <= l.y0 + 1 and min(p.x1, l.x1) - max(p.x0, l.x0) > 0]
        if above:
            a = max(above, key=lambda p: p.y1)
            if _math_profile(a)[3] >= 3 and abs(a.x0 - l.x0) < 2 and a.x0 - left > 0.8 * a.size \
                    and l.y0 - a.y1 < typical_gap + 0.35 * l.size:
                return True
        for p in lines:
            # the rest of a text line: something that is not a formula starts the row at the margin
            if p is l or id(p) in candidates or p.x1 > l.x0 + 1:
                continue
            if -2 <= p.x0 - left < 1.0 * p.size and min(p.y1, l.y1) - max(p.y0, l.y0) > 0.4 * p.height:
                return True
        tiny = sum(1 for c in l.text if not c.isspace()) <= 6
        for p in prose:
            if p is l:
                continue
            overlap = min(p.y1, l.y1) - max(p.y0, l.y0)
            if tiny and overlap > 0.5 and p.x0 - 2 <= l.x0 and l.x1 <= p.x1 + 2:
                return True  # a small stacked fraction or index inside a line of text
            mid = (l.y0 + l.y1) / 2
            if overlap > 0.5 * min(p.height, l.height) and p.y0 - 1 <= mid <= p.y1 + 1 \
                    and p.x0 - 2 <= l.x0 and l.x1 <= p.x1 + 2:
                return True
        return False

    marked = [l for l in marked if not inline(l)]
    # a numbered equation: the lines beside an equation number that are not prose, also when set
    # flush left (Elsevier) and written with text-font letters ("JAt", "RemovalNH4")
    kept = {id(l) for l in marked}
    for n in numbers:
        col = column(n)

        def formula_like(l: RawLine) -> bool:
            """Whether a line next to a numbered formula is part of it (short, mostly formula)."""
            if l is n or id(l) in kept or column(l) != col or l.x1 > n.x0 + 1 or CAPTION_RE.match(l.text):
                return False
            math, formula, total, words = _math_profile(l)
            return total > 0 and len(l.text) <= 45 and words <= 1 and (math > 0 or formula / total >= 0.5
                                                                         or total <= 12)
        band = [l for l in lines if formula_like(l) and min(l.y1, n.y1) - max(l.y0, n.y0) > 0]
        grown = bool(band)
        while grown:
            grown = False
            y0, y1 = min(l.y0 for l in band), max(l.y1 for l in band)
            for l in lines:
                if l not in band and formula_like(l) and l.y0 < y1 + 0.6 * body and l.y1 > y0 - 0.6 * body:
                    band.append(l)
                    grown = True
        if not any(_math_profile(l)[0] or any(c in l.text for c in "=<>≤≥∑∫") for l in band):
            continue
        for l in band:
            kept.add(id(l))
            marked.append(l)
    if not marked:
        return [], lines

    # join neighbouring formula lines (fractions, sum limits, multi-line equations) into regions
    marked.sort(key=lambda l: (l.y0, l.x0))
    regions: list[list[RawLine]] = []
    for l in marked:
        for reg in regions:
            y0, y1 = min(m.y0 for m in reg), max(m.y1 for m in reg)
            x1 = max(m.x1 for m in reg)
            same_col = column(reg[0]) == column(l)
            if same_col and l.y0 - y1 < 1.1 * max(l.size, body) and l.y1 > y0 - 1.1 * body \
                    and not (l.x0 > x1 + 3 * body and l.y0 > y1):
                reg.append(l)
                break
        else:
            regions.append([l])
    used = {id(l) for reg in regions for l in reg}
    # equation numbers on the same height, and short pieces sitting inside a region
    # and the rest of a cases block: conditions in words beside it, rows below it that stay indented
    for reg in regions:
        grown = True
        while grown:
            grown = False
            y0, y1 = min(m.y0 for m in reg), max(m.y1 for m in reg)
            rx0 = min(m.x0 for m in reg)
            for l in numbers + lines:
                if id(l) in used or column(l) != column(reg[0]) or CAPTION_RE.match(l.text):
                    continue
                if l.x0 > column(reg[0])[1] + 3 or l.x1 < column(reg[0])[0] - 3:
                    continue  # a note in the margin
                overlap = min(l.y1, y1) - max(l.y0, y0)
                math, _f, _t, words = _math_profile(l)
                rx1 = max(m.x1 for m in reg)
                # a lone denominator or limit hanging just below or above (partly outside the region)
                piece = bool(re.fullmatch(r"[\w′'∗*+−-]{1,3}|[⎧⎨⎩⎪⎛⎜⎝⎞⎟⎠⎡⎢⎣⎤⎥⎦\s]{1,6}", l.text.strip())) and overlap > -0.2 * body and rx0 - 1 <= l.x0 and l.x1 <= rx1 + 1
                beside = piece or overlap > 0.4 * l.height and (len(l.text) <= 25 or (
                    len(l.text) <= 70 and words <= 4 and l.x0 >= rx0 - body))
                # rows of a cases block above or below, indented from the region's left edge
                touching = (l.y0 < y1 + 0.5 * body and l.y1 > y1) or (l.y1 > y0 - 0.5 * body and l.y0 < y0)
                brace = any(c in l.text for c in "⎧⎨⎩⎪{⎛⎝⎜⌈⌊")  # a row of a cases block or matrix
                row = touching and l.x0 > rx0 + body and words <= (3 if brace else 1) and len(l.text) <= 70 \
                    and math > 0 \
                    and not inline(l)
                # the last row of a matrix or array: numbers and symbols only, within the region's width
                prof = _math_profile(l)
                cells = touching and rx0 - 1 <= l.x0 and l.x1 <= rx1 + 1 and prof[3] == 0 and prof[2] > 0 \
                    and prof[1] / prof[2] >= 0.8 and len(l.text) <= 40 and not inline(l)
                if beside or row or cells:
                    reg.append(l)
                    used.add(id(l))
                    grown = True

    try:
        drawings = [tuple(d["rect"]) for d in page.get_drawings()]
    except Exception:
        drawings = []
    figures: list[RawFigure] = []
    for reg in regions:
        math_chars = sum(_math_profile(l)[0] for l in reg)
        numbered = any(any(l is n for n in numbers) for l in reg)
        if math_chars < 2 and not (numbered and any(c in l.text for l in reg for c in "=<>≤≥∑∫")):
            for l in reg:
                used.discard(id(l))
            continue
        rect = (min(l.x0 for l in reg), min(l.y0 for l in reg), max(l.x1 for l in reg), max(l.y1 for l in reg))
        # fraction bars, radicals and big brackets drawn as lines
        for d in drawings:
            if _area(_intersect(_expand(rect, 2), d)) > 0 or (d[3] - d[1] < 1.5 and
                                                              _area(_intersect(_expand(rect, 3), d)) >= 0 and
                                                              rect[0] - 2 <= d[0] and d[2] <= rect[2] + 2 and
                                                              rect[1] - 3 <= d[1] <= rect[3] + 3):
                if d[2] - d[0] < 1.2 * (rect[2] - rect[0]) + 20 and d[3] - d[1] < 3 * (rect[3] - rect[1]) + 20:
                    rect = _union(rect, d)
        # the letter boxes already hold the ink; more room would catch accents of the next line
        clip = (rect[0] - 3, rect[1] - 0.3, rect[2] + 3, rect[3] + 0.3)
        pix = page.get_pixmap(clip=pymupdf.Rect(clip), dpi=EQUATION_DPI, alpha=True)

        def alt_of(members: list[RawLine]) -> str:
            """The text of a formula built from several lines, read top to bottom, left to right."""
            ordered = sorted(members, key=lambda l: (round(l.y0 / 3), l.x0))
            alt = " ".join(l.text for l in ordered)
            for l in members:
                for ph, im in l.inline_images.items():
                    alt = alt.replace(ph, im.alt or "")
            return alt
        left, right = column(reg[0])
        # a long equation broken over lines (multline) spans the whole column: its lines go one below the
        # other as separate pictures, so that each keeps a readable size
        bands = _ink_bands(pix, body) if rect[2] - rect[0] > 0.7 * (right - left) else []
        if len(bands) < 2:
            bands = [(0, pix.height)]
        scale = 72.0 / EQUATION_DPI
        for b0, b1 in bands:
            part = pix if (b0, b1) == (0, pix.height) else _crop_rows(pix, b0, b1)
            y0, y1 = clip[1] + b0 * scale, clip[1] + b1 * scale
            members = [l for l in reg if y0 - 1 <= (l.y0 + l.y1) / 2 <= y1 + 1] if len(bands) > 1 else reg
            png, width, height = _close_number_gap(part, body)
            box = (clip[0], y0, clip[0] + width * scale, y1)
            img = ImageData(png, "png", width, height, kind="equation", alt=alt_of(members), text_size=float(body))
            figures.append(RawFigure(box, img))
    rest = [l for l in lines if id(l) not in used]
    return figures, rest


def _ink_bands(pix: pymupdf.Pixmap, body: float) -> list[tuple[int, int]]:
    """Rows of a picture separated by clear horizontal gaps (at least a third of a line high)."""
    try:
        alpha = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, -1]
    except Exception:
        return []
    inked = np.flatnonzero(alpha.max(axis=1) > 20)
    if len(inked) == 0:
        return []
    min_gap = 0.2 * body * EQUATION_DPI / 72.0
    bands: list[list[int]] = [[int(inked[0]), int(inked[0]) + 1]]
    for y in inked[1:]:
        if y - bands[-1][1] > min_gap:
            bands.append([int(y), int(y) + 1])
        else:
            bands[-1][1] = int(y) + 1
    # a band much narrower than the picture (the limits of a sum, a lone denominator) is not a line of
    # its own: it stays with the neighbouring band
    cols = alpha > 20

    def width(b0: int, b1: int) -> int:
        """Width of the inked part of rows b0..b1 of the picture (pixels)."""
        inked_x = np.flatnonzero(cols[b0:b1].any(axis=0))
        return int(inked_x[-1] - inked_x[0]) if len(inked_x) else 0
    changed = True
    while changed and len(bands) > 1:
        changed = False
        for i, (b0, b1) in enumerate(bands):
            if width(b0, b1) < 0.3 * pix.width:
                j = i - 1 if i > 0 and (i == len(bands) - 1 or b0 - bands[i - 1][1] <= bands[i + 1][0] - b1) else i + 1
                lo, hi = min(i, j), max(i, j)
                bands[lo] = [bands[lo][0], bands[hi][1]]
                del bands[hi]
                changed = True
                break
    pad = int(0.1 * body * EQUATION_DPI / 72.0)
    return [(max(0, b0 - pad), min(pix.height, b1 + pad)) for b0, b1 in bands]


def _crop_rows(pix: pymupdf.Pixmap, y0: int, y1: int) -> pymupdf.Pixmap:
    """Rows y0..y1 of a pixmap as a new pixmap."""
    part = pymupdf.Pixmap(pix.colorspace, pymupdf.IRect(0, 0, pix.width, y1 - y0), pix.alpha)
    stride = pix.stride
    part.set_origin(0, 0)
    samples = pix.samples[y0 * stride:y1 * stride]
    part.samples_mv[:] = samples
    return part


def _close_number_gap(pix: pymupdf.Pixmap, body: float) -> tuple[bytes, int, int]:
    """An equation number set at the far right leaves a wide empty stretch in the picture, which would make
    the formula tiny once the picture is fitted to the page: bring the number closer."""
    try:
        import numpy as np
        from PIL import Image
        alpha = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, -1]
        ink = alpha.max(axis=0) > 20
        px_per_pt = EQUATION_DPI / 72.0
        cols = np.flatnonzero(ink)
        if len(cols) < 2:
            return pix.tobytes("png"), pix.width, pix.height
        # the widest run of empty columns between inked ones
        gaps = np.diff(cols)
        k = int(gaps.argmax())
        gap_px = int(gaps[k])
        left_end, right_start = int(cols[k]), int(cols[k + 1])
        right_w = pix.width - right_start
        if gap_px < 4 * body * px_per_pt or right_w > 0.2 * pix.width:
            return pix.tobytes("png"), pix.width, pix.height
        keep = int(2 * body * px_per_pt)
        im = Image.frombytes("RGBA", (pix.width, pix.height), pix.samples) if pix.n == 4 else None
        if im is None:
            return pix.tobytes("png"), pix.width, pix.height
        out = Image.new("RGBA", (left_end + 1 + keep + right_w, pix.height), (0, 0, 0, 0))
        out.paste(im.crop((0, 0, left_end + 1, pix.height)), (0, 0))
        out.paste(im.crop((right_start, 0, pix.width, pix.height)), (left_end + 1 + keep, 0))
        buf = io.BytesIO()
        out.save(buf, "PNG")
        return buf.getvalue(), out.width, out.height
    except Exception:
        return pix.tobytes("png"), pix.width, pix.height


# --------------------------------------------------------------------------- tables

def _tables(page: pymupdf.Page) -> list[RawTable]:
    """The tables PyMuPDF finds on a page, checked against the page's ruling lines and turned into TableData."""
    out: list[RawTable] = []
    try:
        found = page.find_tables()
    except Exception:
        return out
    try:
        drawings = page.get_drawings()
    except Exception:
        drawings = []
    for tab in found.tables:
        try:
            rows = tab.extract()
        except Exception:
            rows = []
        rect = tuple(tab.bbox)
        if _looks_like_chart(drawings, rect):
            continue  # gridlines of a chart, not a table
        cells = [c for r in rows for c in r]
        n_rows = len(rows)
        n_cols = max((len(r) for r in rows), default=0)
        empty = sum(1 for c in cells if c is None or not str(c).strip())
        if n_rows < 2 or n_cols < 2:
            continue
        clean = [[(c or "").replace("\n", " ").strip() for c in r] for r in rows]
        reliable = empty / max(1, len(cells)) < 0.35 and n_cols <= 10
        out.append(RawTable(rect, TableData(clean, render_clip(page, _expand(rect, 2)), reliable)))
    return out


TABLE_CAPTION_RE = re.compile(r"^\s*(table|tab\.?|tabel)\s*[\dIVX]+", re.I)


def _horizontal_rules(drawings: list[dict]) -> list[Rect]:
    """Horizontal lines drawn on a page (at least 40 points wide), as (x0, y, x1, y)."""
    out = []
    for d in drawings:
        r = d["rect"]
        if r.height <= 1.6 and r.width >= 40:
            out.append((r.x0, (r.y0 + r.y1) / 2, r.x1, (r.y0 + r.y1) / 2))
    return out


def _looks_like_chart(drawings: list[dict], rect: Rect) -> bool:
    """A chart has curves, markers and filled shapes inside; a table only straight rules."""
    other = 0
    for d in drawings:
        r = d["rect"]
        if overlap_ratio(tuple(r), rect) <= 0.8:
            continue
        if any(it[0] in ("c", "qu") for it in d.get("items", [])):
            other += 1
        elif not (r.height <= 1.6 or r.width <= 1.6) and d.get("fill") is None:
            other += 1
        elif sum(1 for it in d.get("items", []) if it[0] == "l") > 6:
            other += 1  # a polyline: a plotted series
    return other > 2


def _rule_tables(page: pymupdf.Page, existing: list[RawTable]) -> list[RawTable]:
    """Tables drawn with horizontal rules only (LaTeX booktabs: top rule, mid rule, bottom rule)."""
    try:
        drawings = page.get_drawings()
    except Exception:
        return []
    rules = sorted(_horizontal_rules(drawings), key=lambda r: r[1])
    try:
        page_lines = [l for b in page.get_text("dict")["blocks"] for l in b.get("lines", [])]
    except Exception:
        page_lines = []

    def caption_between(y0: float, y1: float, x0: float, x1: float) -> bool:
        """Whether a table/figure caption lies between two heights within x0..x1 (the ruled area is then not one
        table).
        """
        for l in page_lines:
            b = l["bbox"]
            if y0 < b[1] and b[3] < y1 and b[0] < x1 and b[2] > x0 and \
                    CAPTION_RE.match("".join(sp["text"] for sp in l["spans"])):
                return True
        return False

    groups: list[list[Rect]] = []
    for r in rules:
        for g in reversed(groups):
            # same table: booktabs rules share both edges and follow each other within a table's height
            # (a long table may run far, but another table's caption between them starts a new one)
            gap = r[1] - g[-1][1]
            if abs(g[-1][0] - r[0]) < 4 and abs(g[-1][2] - r[2]) < 4 and \
                    (gap < 220 or (gap < 600 and not caption_between(g[-1][1], r[1], r[0], r[2]))):
                g.append(r)
                break
        else:
            groups.append([r])
    words = page.get_text("words")
    try:
        span_bold = [(tuple(sp["bbox"]), _is_bold_font(sp["font"], sp["flags"]), is_math_font(sp["font"]))
                     for b in page.get_text("dict")["blocks"] for l in b.get("lines", []) for sp in l["spans"]
                     if sp["text"].strip()]
    except Exception:
        span_bold = []
    out: list[RawTable] = []
    for g in groups:
        # drop duplicates (thick rules are drawn as two lines)
        ys: list[Rect] = []
        for r in g:
            if not ys or r[1] - ys[-1][1] > 2.5:
                ys.append(r)
        if len(ys) < 2:
            continue
        top, bottom = ys[0][1], ys[-1][1]
        x0, x1 = min(r[0] for r in ys), max(r[2] for r in ys)
        rect = (x0 - 2, top - 1, x1 + 2, bottom + 1)
        if bottom - top < 12 or any(overlap_ratio(rect, t.bbox) > 0.3 for t in existing + out):
            continue
        if _looks_like_chart(drawings, rect):
            continue
        inside = [w for w in words if x0 - 2 <= (w[0] + w[2]) / 2 <= x1 + 2 and top < (w[1] + w[3]) / 2 < bottom]
        if len(inside) < 4:
            continue
        # rows by vertical position
        inside.sort(key=lambda w: ((w[1] + w[3]) / 2, w[0]))
        rows: list[list] = []
        for w in inside:
            cy = (w[1] + w[3]) / 2
            if rows and abs(cy - rows[-1][0]) < 0.45 * (w[3] - w[1]):
                rows[-1][1].append(w)
            else:
                rows.append([cy, [w]])
        # a caption set between the top rules ("Table 1. ...") is not a row of the table
        if rows and CAPTION_RE.match(" ".join(w[4] for w in sorted(rows[0][1], key=lambda w: w[0]))):
            cap_bottom = max(w[3] for w in rows[0][1])
            rows = rows[1:]
            rect = (rect[0], cap_bottom + 0.5, rect[2], rect[3])
            top = cap_bottom + 0.5
            ys = [r for r in ys if r[1] > cap_bottom] or ys
        if len(rows) < 2:
            continue
        # hyphenated line ends mean running prose between two rules (a highlights box), not a table
        if sum(1 for _cy, ws in rows if re.search(r"[a-z]-$", max(ws, key=lambda w: w[2])[4])) >= 2:
            continue
        # header rows: those above the second rule (booktabs mid rule)
        mid = ys[1][1] if len(ys) >= 3 else top
        header_rows = sum(1 for cy, _ in rows if cy < mid) if len(ys) >= 3 else 1
        body = [ws for cy, ws in rows if cy >= mid] or [ws for _, ws in rows]
        # column boundaries: white space shared by (nearly) all body rows
        grid_x0, grid_x1 = int(x0) - 2, int(x1) + 3
        covered = [0] * (grid_x1 - grid_x0)
        for ws in body:
            seen = [False] * len(covered)
            for w in ws:
                for x in range(max(0, int(w[0]) - grid_x0), min(len(covered), int(w[2]) + 1 - grid_x0)):
                    seen[x] = True
            for i, v in enumerate(seen):
                covered[i] += v
        # the gap between two columns is wider than a word space (even a stretched one in justified text)
        heights = sorted(w[3] - w[1] for ws in body for w in ws)
        min_gap = max(3.0, 0.45 * heights[len(heights) // 2])
        limit = max(1, int(len(body) * 0.1))
        cuts, run = [], None
        for i, c in enumerate(covered):
            if c < limit:
                run = i if run is None else run
            else:
                if run is not None and i - run >= min_gap and run > 0:
                    cuts.append(grid_x0 + (run + i) / 2)
                run = None
        n_cols = len(cuts) + 1
        if n_cols < 2 or n_cols > 20:
            continue

        def col_of(w) -> int:
            """The column a word's box falls in, from the column borders ``cuts``."""
            cx = (w[0] + w[2]) / 2
            return sum(1 for c in cuts if cx > c)

        cells: list[list[str]] = []
        bold_cells: set = set()
        math_chars = total_chars = 0
        for ri, (_cy, ws) in enumerate(rows):
            row = [""] * n_cols
            ws = sorted(ws, key=lambda w: w[0])
            place = [col_of(w) for w in ws]
            if ri < header_rows:
                # a header can be wider than its column: keep its words together, placed by the phrase centre
                start = 0
                for k in range(1, len(ws) + 1):
                    if k == len(ws) or ws[k][0] - ws[k - 1][2] >= min_gap or \
                            any(ws[k - 1][2] < c < ws[k][0] for c in cuts):
                        ci = col_of((ws[start][0], 0, ws[k - 1][2], 0))
                        place[start:k] = [ci] * (k - start)
                        start = k
            for w, ci in zip(ws, place):
                row[ci] = (row[ci] + " " + w[4]).strip()
                box = (w[0], w[1], w[2], w[3])
                for sb, bold, math in span_bold:
                    if overlap_ratio(box, sb) > 0.6:
                        total_chars += len(w[4])
                        math_chars += len(w[4]) if math else 0
                        if bold and ri >= header_rows:
                            bold_cells.add((ri, ci))
                        break
            cells.append(row)
        # a header wrapped over two tight lines is one header row
        heights_by_row = [max(w[3] - w[1] for w in ws) for _cy, ws in rows]
        ri = 1
        while ri < header_rows:
            if rows[ri][0] - rows[ri - 1][0] < 1.3 * heights_by_row[ri]:
                cells[ri - 1] = [(a + " " + b).strip() for a, b in zip(cells[ri - 1], cells[ri])]
                del cells[ri], rows[ri], heights_by_row[ri]
                bold_cells = {(r - (r > ri), c) for r, c in bold_cells}
                header_rows -= 1
            else:
                ri += 1
        # columns that stay empty (the space around a vertical separator) are dropped
        keep = [ci for ci in range(n_cols) if any(r[ci] for r in cells)]
        if len(keep) < 2:
            continue
        remap = {old: new for new, old in enumerate(keep)}
        cells = [[r[ci] for ci in keep] for r in cells]
        bold_cells = {(ri, remap[ci]) for ri, ci in bold_cells if ci in remap}
        n_cols = len(keep)
        # a row whose first cell is empty continues the row above (a wrapped cell), unless it has numbers
        merged: list[list[str]] = []
        for ri, row in enumerate(cells):
            if merged and not row[0] and sum(1 for c in row if c) <= 2 and ri >= header_rows and \
                    not any(re.match(r"^[\d.,±%-]+$", c) for c in row if c):
                merged[-1] = [(a + " " + b).strip() for a, b in zip(merged[-1], row)]
            else:
                merged.append(row)
        # running text split in two (an "article info | abstract" header between rules): a column whose
        # cells continue each other mid-sentence
        flows = 0
        for ci in range(n_cols):
            col = [r[ci] for r in merged if r[ci]]
            flows = max(flows, sum(1 for a, b in zip(col, col[1:])
                                   if len(re.findall(r"[A-Za-z]{3,}", a)) >= 4 and b[:1].islower()
                                   and not a.endswith((".", ":", ";"))))
        if flows >= 2:
            continue
        filled = sum(1 for r in merged for c in r if c) / max(1, len(merged) * n_cols)
        # formulas in cells read better as the original picture
        reliable = filled > 0.45 and math_chars <= 0.1 * max(1, total_chars)
        out.append(RawTable(rect, TableData(merged, render_clip(page, _expand(rect, 2)), reliable,
                                            header_rows=max(1, header_rows), bold_cells=bold_cells)))
    return out


def _caption_tables(page: pymupdf.Page, lines: list[RawLine], existing: list[RawTable]) -> list[RawTable]:
    """Find tables without ruling lines, using their "Table N" caption as anchor."""
    out: list[RawTable] = []
    if not lines:
        return out
    sizes = Counter()
    for l in lines:
        sizes[round(l.size, 1)] += len(l.text)
    body = sizes.most_common(1)[0][0]
    width = page.rect.width
    mid = width / 2
    body_widths = sorted(l.x1 - l.x0 for l in lines if l.size >= body * 0.97 and len(l.text) >= 30)
    col_width = body_widths[len(body_widths) // 2] if body_widths else width
    for cap in lines:
        if not TABLE_CAPTION_RE.match(cap.text):
            continue
        if any(overlap_ratio(cap.bbox, _expand(t.bbox, 30)) > 0 for t in existing + out):
            continue
        left = cap.x0 - 3
        right = width - 4
        others = [l for l in lines if l.x0 > mid and l.size >= body * 0.97 and abs(l.y0 - cap.y0) < 80
                  and len(l.text) > 20]
        if cap.x1 < mid and others:
            right = mid
        below = sorted((l for l in lines if l.y0 >= cap.y1 - 1 and l is not cap and l.x0 >= left - 1
                        and l.x1 <= right + 1), key=lambda l: l.y0)
        region: list[RawLine] = []
        last_y = cap.y1
        for l in below:
            if l.y0 - last_y > max(2.5 * l.height, 14):
                break
            if l.size >= body * 0.97 and len(l.text) >= 30 and (l.x1 - l.x0) >= 0.85 * col_width:
                break  # a full-width line of running body text: the table has ended
            region.append(l)
            last_y = max(last_y, l.y1)
        if region:
            mode = Counter(round(l.size, 1) for l in region).most_common(1)[0][0]
            while region and region[-1].size < mode - 0.4:
                region.pop()  # smaller print below the table ("Source: ...") stays as text
        if len(region) < 4:
            continue
        clip = pymupdf.Rect(left, cap.y1 + 0.5, max(l.x1 for l in region) + 2, max(l.y1 for l in region) + 1)
        try:
            found = page.find_tables(clip=clip, strategy="text")
        except Exception:
            continue
        for tab in found.tables:
            rows = [[(c or "").replace("\n", " ").strip() for c in r] for r in tab.extract()]
            rows = [r for r in rows if any(r)]
            while rows and sum(1 for c in rows[-1] if c) <= 1 and len(rows) > 2:
                rows.pop()  # table notes such as "Source: ..." stay as normal text
            n_cols = max((len(r) for r in rows), default=0)
            if len(rows) < 2 or n_cols < 2:
                continue
            row_lines = [l for l in region if any(l.text and l.text[:12] in " ".join(r) for r in rows)]
            bottom = max((l.y1 for l in row_lines), default=tab.bbox[3])
            rect = (tab.bbox[0], tab.bbox[1], tab.bbox[2], min(tab.bbox[3], bottom + 0.5))
            if any(overlap_ratio(rect, t.bbox) > 0.3 or overlap_ratio(t.bbox, rect) > 0.3 for t in existing + out):
                break  # already found (by its rules)
            out.append(RawTable(rect, TableData(rows, render_clip(page, _expand(rect, 3)), n_cols <= 10)))
            break
    return out


# --------------------------------------------------------------------------- OCR pages

LEADER_STRIPS = int(__import__("os").environ.get("DC_LEADER_STRIPS", "1") or 1)  # experiment switch
OCR_GAP_MIN_WORDS = int(__import__("os").environ.get("DC_OCR_GAP_MIN", "1") or 1)  # experiment switch
OCR_COLUMN_GAP = float(__import__("os").environ.get("DC_OCR_GAP", "0") or 0)  # experiment switch


def _split_wide_gaps(groups: dict) -> dict:
    """Lines as OCR found them, split at a column gutter that OCR read across: two columns side by side read as
    one line each (as Tesseract sometimes does with a narrow column, such as an article's "article info" box,
    next to a wide one). A gutter is a gap much wider than the space between words, with words on both sides,
    that a line just above or below also has at the same place. Each side becomes a block of its own, so the
    columns are read one after the other. A single wide gap (a label beside a figure, a page number after a
    title) is left alone."""
    if not OCR_COLUMN_GAP:
        return groups
    info = []  # (key, words, line height, wide gaps)
    for key, words in groups.items():
        words = sorted(words, key=lambda w: w.bbox[0])
        heights = sorted(w.bbox[3] - w.bbox[1] for w in words)
        h = heights[len(heights) // 2]
        n = OCR_GAP_MIN_WORDS
        gaps = [(words[i - 1].bbox[2], words[i].bbox[0]) for i in range(n, len(words) - n + 1)
                if words[i].bbox[0] - words[i - 1].bbox[2] > OCR_COLUMN_GAP * h]
        info.append((key, words, h, gaps))
    out: dict = {}
    for key, words, h, gaps in info:
        y0, y1 = min(w.bbox[1] for w in words), max(w.bbox[3] for w in words)
        cut = None
        for a0, a1 in gaps:
            for key2, words2, h2, gaps2 in info:
                if key2 == key or not gaps2:
                    continue
                b_y0, b_y1 = min(w.bbox[1] for w in words2), max(w.bbox[3] for w in words2)
                if b_y0 > y1 + 2 * h or b_y1 < y0 - 2 * h:  # not a neighbouring line
                    continue
                for b0, b1 in gaps2:
                    if min(a1, b1) - max(a0, b0) > 0:
                        cut = (max(a0, b0) + min(a1, b1)) / 2
                        break
                if cut is not None:
                    break
            if cut is not None:
                break
        if cut is None:
            out[key] = words
            continue
        bn, par, ln = key
        out[key] = [w for w in words if w.bbox[2] <= cut]
        out[(bn + 500, par, ln)] = [w for w in words if w.bbox[2] > cut]
    return out


def _ocr_image(png: bytes, dpi: int, width_pt: float, height_pt: float, pno: int, engine: OcrEngine,
               languages: list[str], crop: Callable[[Rect], ImageData]) -> tuple[list[RawLine], list[RawFigure]]:
    """OCR one image and return lines/figures in points relative to that image."""
    res = engine.recognize(_without_leaders(png), languages)
    scale = 72.0 / dpi
    groups: dict[tuple[int, int, int], list] = {}
    for w in res.words:
        groups.setdefault((w.block, w.paragraph, w.line), []).append(w)
    lines: list[RawLine] = []
    for (bn, par, _ln), words in _split_wide_gaps(groups).items():
        text = ""
        conf: list[OcrWordConfidence] = []
        for w in words:
            if text:
                text += " "
            conf.append(OcrWordConfidence(len(text), len(text) + len(w.text), w.confidence))
            text += w.text
        x0 = min(w.bbox[0] for w in words) * scale
        y0 = min(w.bbox[1] for w in words) * scale
        x1 = max(w.bbox[2] for w in words) * scale
        y1 = max(w.bbox[3] for w in words) * scale
        # estimate from ordinary words; superscripts and symbols distort the ink height
        plain = [w for w in words if re.fullmatch(r"[A-Za-z][a-z]+[.,;:]?", w.text)] or \
            [w for w in words if len(w.text) >= 2 or w.text.isalnum()]
        estimates = sorted(_estimate_font_size(w.text, (w.bbox[3] - w.bbox[1]) * scale) for w in plain)
        size = estimates[len(estimates) // 2] if estimates else _estimate_font_size(text, y1 - y0)
        lines.append(RawLine(text=text, bbox=(x0, y0, x1, y1), size=round(size * 2) / 2, page=pno,
                             source="ocr", block_no=bn * 1000 + par, conf=conf))
    lines = [l for l in lines if not _is_ocr_noise(l)]
    regions = [tuple(v * scale for v in r.bbox) for r in res.regions]
    regions += _scan_graphic_regions(png, lines, width_pt, height_pt)
    from PIL import Image

    gray = np.asarray(Image.open(io.BytesIO(png)).convert("L"))
    regions = [r for r in regions if _plausible_scan_figure(r, lines, width_pt, height_pt, gray, dpi)]
    figures = _figures_from_regions(regions, lines, width_pt * height_pt, crop)
    fig_rects = [f.bbox for f in figures]
    lines = [l for l in lines if not any(overlap_ratio(l.bbox, f) > 0.6 for f in fig_rects)]
    formulas, lines = _scan_formulas(lines, width_pt, crop)
    return lines, figures + formulas


def _leader_spans(ink: np.ndarray) -> list[tuple[int, int, int, int]]:
    """Rows of dots in a black-and-white page image (``ink``: True where there is ink), as (y0, y1, x0, x1): the
    dot leaders between a title and its page number in a table of contents. Each text line is looked at on its
    own: a leader is at least five tiny specks low on the line, one after the other at a regular distance."""
    rows = ink.any(axis=1)
    spans = []
    y = 0
    n = len(rows)
    while y < n:
        if not rows[y]:
            y += 1
            continue
        y0 = y
        while y < n and rows[y]:
            y += 1
        band = ink[y0:y]
        h = y - y0
        if h < 6:
            continue
        cols = band.any(axis=0)
        if cols.sum() < 20:
            continue
        top = np.where(cols, band.argmax(axis=0), 0)
        bottom = np.where(cols, h - 1 - band[::-1].argmax(axis=0), 0)
        # specks: short blobs (a dot is at most about a third of the line high) in the lower part of the line
        dots = []
        xs = np.flatnonzero(cols)
        start = prev = int(xs[0])
        for x in list(xs[1:]) + [None]:
            if x is not None and x == prev + 1:
                prev = int(x)
                continue
            t, b = int(top[start:prev + 1].min()), int(bottom[start:prev + 1].max())
            if prev - start + 1 <= max(4, 0.35 * h) and b - t + 1 <= max(4, 0.35 * h) and t > 0.4 * h:
                dots.append((start, prev))
            else:
                dots.append(None)  # a letter or other mark: ends a row of dots
            if x is not None:
                start = prev = int(x)
        run: list = []
        for d in dots + [None]:
            if d is not None and (not run or d[0] - run[-1][1] <= 1.6 * h):
                run.append(d)
                continue
            if len(run) >= 5:
                gaps = [b[0] - a[1] for a, b in zip(run, run[1:])]
                if max(gaps) <= 3 * max(1, min(gaps)) + 2:  # evenly spaced
                    spans.append((y0, y, run[0][0], run[-1][1] + 1))
            run = [d] if d is not None else []
    return spans


def _without_leaders(png: bytes) -> bytes:
    """The page image with the rows of dots of a table of contents taken out: OCR reads them as made-up words,
    and they make it misread the titles next to them."""
    from PIL import Image

    im = Image.open(io.BytesIO(png)).convert("L")
    gray = np.asarray(im)
    ink = gray < 150
    strips = LEADER_STRIPS
    if strips > 1:
        # looked for in vertical strips: a slightly tilted scan or a page in columns makes lines run into each
        # other across the whole width, but not within a narrow strip
        spans = _leader_spans(ink)
        w = ink.shape[1]
        for k in range(strips):
            x0, x1 = k * w // strips, (k + 1) * w // strips
            spans += [(a, b, c + x0, d + x0) for a, b, c, d in _leader_spans(ink[:, x0:x1])]
    else:
        spans = _leader_spans(ink)
    if not spans:
        return png
    clean = gray.copy()
    for y0, y1, x0, x1 in spans:
        clean[y0:y1, x0:x1] = 255
    buf = io.BytesIO()
    Image.fromarray(clean).save(buf, format="PNG")
    return buf.getvalue()


def _scan_formulas(lines: list[RawLine], width: float, crop: Callable[[Rect], ImageData]
                   ) -> tuple[list[RawFigure], list[RawLine]]:
    """OCR cannot read formulas: on a scanned page, lines that look like displayed mathematics (set apart,
    few real words, symbols that OCR is unsure of) are kept as pictures of the page instead of garbled text."""
    long = [l for l in lines if len(l.text) >= 40]
    if len(long) < 3:
        return [], lines
    left = sorted(l.x0 for l in long)[len(long) // 5]
    right = sorted(l.x1 for l in long)[len(long) * 4 // 5]
    text_w = max(1.0, right - left)
    # a page in columns: "set apart" is measured within the column of the line, not across the page
    columns: list[list[RawLine]] = []
    for l in sorted(long, key=lambda l: l.x0):
        if columns and l.x0 - columns[-1][0].x0 < 0.15 * width:
            columns[-1].append(l)
        else:
            columns.append([l])
    columns = [c for c in columns if len(c) >= max(3, 0.15 * len(long))]
    bounds_of = []
    if len(columns) >= 2:
        for c in columns:
            c_left = sorted(l.x0 for l in c)[len(c) // 5]
            c_right = sorted(l.x1 for l in c)[len(c) * 4 // 5]
            bounds_of.append((c_left, c_right, max(1.0, c_right - c_left)))

    def bounds(l: RawLine) -> tuple[float, float, float]:
        """(left, right, width) of the text the line is set in: its column, or the page's text."""
        if not bounds_of:
            return left, right, text_w
        return max(bounds_of, key=lambda b: min(b[1], l.x1) - max(b[0], l.x0))

    def formula_like(l: RawLine) -> bool:
        """Whether an OCR line looks like a formula OCR could not read (set apart, few real words, low
        confidence, or an equation number).
        """
        left, right, text_w = bounds(l)
        body = re.sub(r"\s", "", l.text)
        if len(body) < 3 or (len(body) <= 5 and re.fullmatch(r"[\divxlcIVXLC.\-–—]+", body)):
            return False  # page numbers
        wordy = sum(len(w) for w in re.findall(r"[A-Za-z]{3,}", l.text))
        letters = wordy / len(body)
        conf = sum(c.confidence for c in l.conf) / len(l.conf) if l.conf else 100.0
        set_apart = l.x0 - left > 0.12 * text_w and right - l.x1 > 0.12 * text_w
        numbered = bool(re.search(r"\(\d{1,3}[a-z]?\)\s*$", l.text)) and l.x1 > right - 0.05 * text_w
        indented = l.x0 - left > 0.12 * text_w  # (an equation number may reach the right edge, read as "A)")
        return (set_apart and letters < 0.5 and conf < 85) or (numbered and letters < 0.5) or \
            (indented and conf < 50 and letters < 0.5) or \
            (set_apart and conf < 55 and letters < 0.7) or (letters < 0.3 and conf < 70 and len(body) <= 40) or \
            (letters < 0.2 and len(body) <= 30 and bool(re.search(r"[=+<>|/()\[\]{}^_]", body)))
    flagged = [l for l in lines if formula_like(l)]
    if not flagged:
        return [], lines

    def fragment(l: RawLine) -> bool:
        """A piece of a formula OCR read as a line of its own (a limit under an integral, a matrix row, "if x > 0",
        "otherwise"): set in from the margin, not a full line, and at most one real word."""
        left, _right, text_w = bounds(l)
        return l.x0 - left > 0.08 * text_w and l.x1 - l.x0 < 0.75 * text_w and \
            len(re.findall(r"[A-Za-z]{4,}", l.text)) <= 1 and len(re.sub(r"\s", "", l.text)) <= 30

    flagged_ids = {id(l) for l in flagged}
    text_lines = [l for l in lines if id(l) not in flagged_ids and not fragment(l)]

    def text_between(r: Rect, l: RawLine) -> bool:
        """Whether an ordinary line of text lies between a formula region and a line (they are separate then:
        "Equation (1) is classical." between two formulas)."""
        top, bottom = (r[3], l.y0) if l.y0 >= r[3] else (l.y1, r[1])
        return any(m.y0 >= top - 1 and m.y1 <= bottom + 1 for m in text_lines)

    regions: list[list] = []
    for l in sorted(flagged, key=lambda l: l.y0):
        for reg in regions:
            r = reg[0]
            if l.y0 - r[3] < 1.5 * l.size and min(r[2], l.x1) - max(r[0], l.x0) > -0.1 * text_w and \
                    not text_between(r, l):
                reg[0] = _union(r, l.bbox)
                reg[1].append(l)
                break
        else:
            regions.append([l.bbox, [l]])

    grown = True
    while grown:  # take in the pieces touching a formula (each piece can bring the next one)
        grown = False
        taken = {id(m) for reg in regions for m in reg[1]}
        for l in lines:
            if id(l) in taken or not fragment(l):
                continue
            for reg in regions:
                r = reg[0]
                near = max(l.size, 8.0)
                beside = min(r[3], l.y1) - max(r[1], l.y0) > 0.5 * (l.y1 - l.y0) and \
                    bounds(l) == bounds(reg[1][0])  # on the same line in the same column (a formula and its number)
                if l.y0 < r[3] + near and l.y1 > r[1] - near and not text_between(r, l) and \
                        (beside or min(r[2], l.x1) - max(r[0], l.x0) > -0.5 * near):
                    reg[0] = _union(r, l.bbox)
                    reg[1].append(l)
                    grown = True
                    break
    figures: list[RawFigure] = []
    used: set[int] = set()
    for rect, members in regions:
        # parts OCR did not see (a brace, a limit) stick out; a tall formula (brackets) reads as a big "size", so
        # the room is at most about a line of the running text
        body = float(statistics.median(l.size for l in long))
        pad = min(0.8 * max(l.size for l in members), 1.2 * body)
        # small pieces OCR dropped (a denominator, an index) sit just above or below: take some room, but
        # not into the text lines around it
        # (any line above or below counts, also one beside it at the margin: the picture must not start above it,
        # or it would be read before it)
        others = [l for l in lines if l not in members]
        top = max([l.y1 + 0.5 for l in others if l.y1 <= rect[1] + 1] + [rect[1] - pad])
        bottom = min([l.y0 - 0.5 for l in others if l.y0 >= rect[3] - 1] + [rect[3] + pad])
        # at the sides more room: a big symbol OCR did not see (a sum or integral sign) often starts the formula
        side = max(pad, 0.9 * body)
        box = (max(0.0, rect[0] - side), max(0.0, top), min(width, rect[2] + side), bottom)
        img = crop(box)
        img.kind = "equation"
        img.alt = "formula (see the picture)"
        img.text_size = float(statistics.median(l.size for l in long))
        figures.append(RawFigure(box, img))
        used.update(id(l) for l in members)
    return figures, [l for l in lines if id(l) not in used]


def _plausible_scan_figure(r: Rect, lines: list[RawLine], width: float, height: float,
                           gray: Optional[np.ndarray] = None, dpi: int = OCR_DPI) -> bool:
    """Reject 'figures' that are really text, page-edge shadows or page curl."""
    w, h = r[2] - r[0], r[3] - r[1]
    if w < 40 or h < 30:
        return False
    touches_lr = r[0] < width * 0.03 or r[2] > width * 0.97
    touches_tb = r[1] < height * 0.03 or r[3] > height * 0.97
    if touches_lr and w < width * 0.12:
        return False  # dark strip along the left/right edge (gutter, book edge)
    if touches_tb and h < height * 0.1:
        return False  # strip along the top/bottom edge (page curl, scanner lid)
    # share of the region covered by recognised text lines: paragraphs are dense, pictures are not
    text_area = sum(_area(_intersect(l.bbox, r)) for l in lines if len(l.text) >= 15)
    limit = 0.12 if (touches_lr or touches_tb) else 0.25
    if text_area / (w * h) >= limit:
        return False
    if gray is not None:
        # pictures and diagrams contain real ink; edge shadows leave a mostly blank area
        k = dpi / 72.0
        crop = gray[max(0, int(r[1] * k)):int(r[3] * k), max(0, int(r[0] * k)):int(r[2] * k)]
        if crop.size:
            m = max(2, int(min(crop.shape) * 0.08))  # ignore a band along the region border
            inner = crop[m:-m, m:-m] if min(crop.shape) > 3 * m else crop
            dark = inner < 170
            if dark.size:
                # solid bars (page edges, gutter shadow) are not picture content
                dark = dark[:, dark.mean(axis=0) < 0.8]
                dark = dark[dark.mean(axis=1) < 0.8, :] if dark.size else dark
            ink = float(dark.mean()) if dark.size else 0.0
            if ink < (0.06 if (touches_lr or touches_tb) else 0.015):
                return False
    return True


def _is_ocr_noise(line: RawLine) -> bool:
    """Speckles, page-edge shadows and bleed-through read as random characters."""
    text = line.text.strip()
    letters = sum(ch.isalnum() for ch in text)
    if letters == 0:
        return True
    good = [c.confidence for c in line.conf if c.confidence >= 0]
    mean_conf = sum(good) / len(good) if good else 100
    return (letters <= 3 and mean_conf < 40) or (mean_conf < 25 and letters < 12)


def _figures_from_regions(regions: list[Rect], lines: list[RawLine], page_area: float,
                          crop: Callable[[Rect], ImageData]) -> list[RawFigure]:
    """Figures cut from picture regions of a scanned page (too small, too large or overlapping regions skipped; edges
    that clip text lines trimmed).
    """
    figures: list[RawFigure] = []
    for r in regions:
        if _area(r) < 0.015 * page_area or _area(r) > 0.9 * page_area:
            continue
        if any(overlap_ratio(r, f.bbox) > 0.5 for f in figures):
            continue
        # trim edges that clip neighbouring text lines (they stay as text)
        x0, y0, x1, y1 = r
        for l in lines:
            if overlap_ratio(l.bbox, r) > 0.5 or _area(_intersect(l.bbox, (x0, y0, x1, y1))) == 0:
                continue
            if (l.y0 + l.y1) / 2 < (y0 + y1) / 2:
                y0 = max(y0, l.y1 + 1)
            else:
                y1 = min(y1, l.y0 - 1)
        if y1 - y0 < 20 or (y1 - y0) < 0.4 * (r[3] - r[1]):
            continue  # mostly text after all: only a sliver would remain
        r = (x0, y0, x1, y1)
        figures.append(RawFigure(r, crop((x0 - 2, y0, x1 + 2, y1))))
    return figures


def _ocr_page(page: pymupdf.Page, pno: int, engine: OcrEngine, languages: list[str]) -> tuple[list[RawLine], list[RawFigure]]:
    """OCR a page as it is (used for mixed pages that are not full scans)."""
    pix = page.get_pixmap(dpi=OCR_DPI, alpha=False)
    return _ocr_image(pix.tobytes("png"), OCR_DPI, page.rect.width, page.rect.height, pno, engine, languages,
                      lambda r: render_clip(page, r))


def _photo_crop(photo, dpi: int) -> Callable[[Rect], ImageData]:
    """A function that cuts a region (points) out of a scanned page's photo as a PNG at up to 200 dpi."""
    def crop(r: Rect) -> ImageData:
        """The region ``r`` (points) of the photo as a PNG."""
        k = dpi / 72.0
        box = (max(0, int(r[0] * k)), max(0, int(r[1] * k)), min(photo.width, int(r[2] * k)),
               min(photo.height, int(r[3] * k)))
        part = photo.crop(box)
        # figures are stored at up to 200 dpi, like figures from text PDFs
        f = min(1.0, FIGURE_DPI / dpi)
        if f < 1:
            part = part.resize((max(1, int(part.width * f)), max(1, int(part.height * f))))
        buf = io.BytesIO()
        part.save(buf, format="PNG")
        return ImageData(buf.getvalue(), "png", part.width, part.height)
    return crop


def _scan_pages(rendered, source_page: int, engine: OcrEngine, languages: list[str],
                split_spreads: bool) -> list[RawPage]:
    """Clean a rendered scan (split spreads, flatten, deskew) and OCR each book page.

    Runs in a worker thread: it only uses the rendered image, never the PDF.
    Page numbers are assigned by the caller.
    """
    out = _scan_image_pages(rendered, source_page, engine, languages, split_spreads)
    if _poor_ocr(out) and hasattr(engine, "orientation"):
        # sideways or upside-down scan: ask the OCR engine which way is up and try again
        buf = io.BytesIO()
        rendered.save(buf, format="PNG")
        turn = engine.orientation(buf.getvalue())
        if turn:
            rendered = rendered.rotate(-turn, expand=True)
            retry = _scan_image_pages(rendered, source_page, engine, languages, split_spreads)
            if _ocr_quality(retry) > _ocr_quality(out):
                out = retry
    return out


def _scan_image_pages(rendered, source_page: int, engine: OcrEngine, languages: list[str],
                      split_spreads: bool) -> list[RawPage]:
    """OCR one scanned page (split into two book pages when it is a spread), with its figures."""
    from .scan import prepare_page

    out: list[RawPage] = []
    for sp in prepare_page(rendered, SCAN_DPI, split_spreads=split_spreads):
        info = PageInfo(-1, sp.width_pt, sp.height_pt, "scanned", ocr_used=True, source_page=source_page,
                        side=sp.side, skew=sp.skew)
        lines, figures = _ocr_image(sp.png(), SCAN_DPI, sp.width_pt, sp.height_pt, -1, engine, languages,
                                    _photo_crop(sp.photo, SCAN_DPI))
        out.append(RawPage(info, lines, figures))
    return out


def _ocr_quality(pages: list[RawPage]) -> float:
    """Mean word confidence (0..100) weighted by the amount of text."""
    confs = [c.confidence for p in pages for l in p.lines for c in l.conf if c.confidence >= 0]
    return sum(confs) / len(confs) if confs else 0.0


def _poor_ocr(pages: list[RawPage]) -> bool:
    """Whether OCR found little text or had low confidence (then the scanner's own text may be better)."""
    words = sum(len(l.conf) for p in pages for l in p.lines)
    return words < 15 or _ocr_quality(pages) < 55


def _word_lines(page: pymupdf.Page, pno: int) -> list[RawLine]:
    """Lines rebuilt from word boxes: scanner text layers often lack real space characters."""
    groups: dict[tuple[int, int], list] = {}
    to_page, _ = _page_mapper(page)
    for x0, y0, x1, y1, word, bno, lno, _wno in page.get_text("words"):
        x0, y0, x1, y1 = to_page((x0, y0, x1, y1))
        groups.setdefault((bno, lno), []).append((x0, y0, x1, y1, word))
    lines: list[RawLine] = []
    for (bno, _lno), words in groups.items():
        words.sort(key=lambda w: w[0])
        text = " ".join(w[4] for w in words).strip()
        if not text:
            continue
        heights = sorted(w[3] - w[1] for w in words)
        size = round(heights[len(heights) // 2] / 1.15 * 2) / 2
        bbox = (min(w[0] for w in words), min(w[1] for w in words), max(w[2] for w in words),
                max(w[3] for w in words))
        # recognised text: it is checked against the dictionary like our own OCR
        lines.append(RawLine(text=text, bbox=bbox, size=size, page=pno, source="ocr", block_no=bno))
    return _merge_same_baseline(lines)


def _text_layer_scan_page(page: pymupdf.Page, pno: int,
                          known: Optional[Callable[[str], bool]] = None) -> tuple[list[RawLine], list[RawFigure]]:
    """Use the invisible OCR text layer a scanner added (when we cannot OCR ourselves).

    Where that text is garbled (common on curled or dark parts of a scan), the
    original is shown as a picture instead, so the content stays readable.
    """
    from PIL import Image

    lines = _word_lines(page, pno)
    dpi = 150
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    png = pix.tobytes("png")
    photo = Image.open(io.BytesIO(png)).convert("RGB")
    regions = _scan_graphic_regions(png, lines, page.rect.width, page.rect.height)
    gray = np.asarray(photo.convert("L"))
    regions = [r for r in regions if _plausible_scan_figure(r, lines, page.rect.width, page.rect.height, gray, dpi)]
    figures = _figures_from_regions(regions, lines, page.rect.width * page.rect.height, _photo_crop(photo, dpi))
    fig_rects = [f.bbox for f in figures]
    lines = [l for l in lines if not any(overlap_ratio(l.bbox, f) > 0.6 for f in fig_rects)]
    if known is not None:
        lines, figures = _replace_garbled_halves(page, lines, figures, known, photo, dpi)
    return lines, figures


def _garbled(line: RawLine, known: Callable[[str], bool]) -> bool:
    """Whether a line of the scanner's stored text is mostly non-words (then OCR is used instead)."""
    words = re.findall(r"[A-Za-z]{3,}", line.text)
    if len(line.text) < 15 or not words:
        return False
    return sum(1 for w in words if known(w)) / len(words) < 0.6


def _replace_garbled_halves(page: pymupdf.Page, lines: list[RawLine], figures: list[RawFigure],
                            known: Callable[[str], bool], photo, dpi: int):
    """Where the scanner's stored text is garbled on (half of) a page, use the page picture for that part instead."""
    w, h = page.rect.width, page.rect.height
    halves = [(0.0, w / 2), (w / 2, w)] if w > h * 1.15 else [(0.0, w)]  # spreads: judge each book page
    crop = _photo_crop(photo, dpi)
    for x0, x1 in halves:
        mine = [l for l in lines if x0 <= (l.x0 + l.x1) / 2 < x1]
        if len(mine) < 5:
            continue
        bad = sum(1 for l in mine if _garbled(l, known))
        if bad / len(mine) > 0.3:
            ids = {id(l) for l in mine}
            lines = [l for l in lines if id(l) not in ids]
            figures = [f for f in figures if not (x0 <= (f.bbox[0] + f.bbox[2]) / 2 < x1)]
            img = crop((x0, 0, x1, h))
            img.kind = "unreadable-text"
            figures.append(RawFigure((x0, 0, x1, h), img))
    return lines, figures


def _estimate_font_size(text: str, height: float) -> float:
    """Estimate the font size of an OCR line from its ink height."""
    has_asc = bool(re.search(r"[A-Zbdfhklt0-9(\[{|/]", text))
    has_desc = bool(re.search(r"[gjpqy,;(\[{|]", text))
    em = (0.72 if has_asc else 0.5) + (0.22 if has_desc else 0.0)
    return round(height / em * 2) / 2


def _scan_graphic_regions(png: bytes, lines: list[RawLine], width: float, height: float) -> list[Rect]:
    """Find pictures/diagrams/ruled tables on a scanned page.

    Text-line areas are blanked, the remaining ink is gridded into cells and
    connected cells form candidate graphic regions.
    """
    from PIL import Image, ImageDraw, ImageFilter

    img = Image.open(io.BytesIO(png)).convert("L").filter(ImageFilter.MinFilter(5))  # keep thin rules
    dpi = 60
    small = img.resize((max(1, int(width * dpi / 72)), max(1, int(height * dpi / 72))), Image.BOX)
    k = dpi / 72
    draw = ImageDraw.Draw(small)
    for l in lines:
        draw.rectangle([l.x0 * k - 1, l.y0 * k - 1, l.x1 * k + 1, l.y1 * k + 1], fill=255)
    ink = small.point(lambda v: 255 if v < 170 else 0)
    cell = 6
    gw, gh = max(1, small.width // cell), max(1, small.height // cell)
    grid = ink.resize((gw, gh), Image.BOX)
    px = grid.load()
    occupied = {(x, y) for y in range(gh) for x in range(gw) if px[x, y] > 12}
    regions: list[Rect] = []
    seen: set = set()
    for start in occupied:
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        xs, ys = [], []
        while stack:
            x, y = stack.pop()
            xs.append(x)
            ys.append(y)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    n = (x + dx, y + dy)
                    if n in occupied and n not in seen:
                        seen.add(n)
                        stack.append(n)
        f = cell / k
        r = (min(xs) * f, min(ys) * f, (max(xs) + 1) * f, (max(ys) + 1) * f)
        if r[2] - r[0] >= 50 and r[3] - r[1] >= 30 and len(xs) >= 12:
            regions.append(r)
    # include text lines that sit inside a region (labels, table cells)
    out = []
    for r in regions:
        for l in lines:
            if overlap_ratio(l.bbox, _expand(r, 2)) > 0.5:
                r = _union(r, l.bbox)
        out.append(r)
    return out


# --------------------------------------------------------------------------- main entry

def _duration(seconds: float) -> str:
    """A rough time left for the progress message ("25 s", "3 min")."""
    if seconds < 60:
        return f"{max(1, int(round(seconds / 5.0) * 5))} s"
    return f"{int(round(seconds / 60.0))} min"


def read_pdf(path: str, ocr_engine: Optional[OcrEngine] = None, languages: Optional[list[str]] = None,
             progress: Optional[ProgressFn] = None, pages: Optional[tuple[int, int]] = None,
             split_spreads: bool = True, prefer_text_layer: bool = False,
             known_word: Optional[Callable[[str], bool]] = None) -> RawDocument:
    """Read a PDF. ``pages`` is an optional 1-based inclusive (first, last) range.

    Scanned pages are cleaned (two-page spreads split, shadows removed,
    straightened) and OCR'd; each book page becomes its own page. Without an
    OCR engine, or when ``prefer_text_layer`` is set, an existing invisible
    text layer from the scanner is used instead.
    """
    page_range = pages
    doc = pymupdf.open(path)  # opened read-only; never saved back
    pool: Optional[concurrent.futures.ThreadPoolExecutor] = None
    try:
        if doc.needs_pass:
            raise ValueError("This PDF is password-protected. Please unlock it first.")
        pages: list[RawPage] = []
        warnings: list[str] = []
        meta = doc.metadata or {}
        n = doc.page_count

        # images that repeat on many pages are furniture (logos, backgrounds)
        xref_pages: Counter = Counter()
        for page in doc:
            for x in {i[0] for i in page.get_images()}:
                xref_pages[x] += 1
        repeated = {x for x, c in xref_pages.items() if n >= 3 and c >= max(3, n * 0.5)}

        ocr_langs = languages or ["en"]
        first, last = (1, n) if page_range is None else (max(1, page_range[0]), min(n, page_range[1]))
        workers = max(1, min(4, (os.cpu_count() or 2)))
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers)
        pending: list[concurrent.futures.Future] = []
        text_layer_pages: list[int] = []
        no_ocr_pages: list[int] = []
        scans_total = sum(1 for i in range(first - 1, last) if classify_page(doc[i]) == "scanned") \
            if ocr_engine is not None else 0
        scan_start = time.monotonic()
        scans_done = [0]
        lock = threading.Lock()

        def report_scan(_fut) -> None:
            """A scanned page is done: update the progress with an estimate of the time left."""
            with lock:
                scans_done[0] += 1
                done = scans_done[0]
            if progress and scans_total:
                left = (time.monotonic() - scan_start) / done * (scans_total - done)
                eta = f" - about {_duration(left)} left" if done < scans_total else ""
                progress(f"Read {done} of {scans_total} scanned page(s){eta}", done / scans_total)

        for pno, page in enumerate(doc):
            if not first <= pno + 1 <= last:
                continue
            _normalise_rotation(page)
            if progress and not scans_total:
                progress(f"Reading page {pno + 1} of {n}", pno / max(1, n))
            kind = classify_page(page)
            vno = len(pages)  # pages of the output (a two-page spread becomes two pages)
            info = PageInfo(vno, page.rect.width, page.rect.height, kind, source_page=pno)
            rp = RawPage(info)
            text_layer = kind == "scanned" and has_invisible_text(page)
            if kind == "scanned" and text_layer and (ocr_engine is None or prefer_text_layer):
                rp.lines, rp.figures = _text_layer_scan_page(page, vno, known_word)
                info.ocr_used = True
                info.text_source = "scanner"
                text_layer_pages.append(pno + 1)
            elif kind == "scanned" and ocr_engine is not None:
                # render here (PyMuPDF is not thread-safe); clean-up + OCR run in parallel
                from PIL import Image

                pix = page.get_pixmap(dpi=SCAN_DPI, alpha=False, colorspace=pymupdf.csRGB)
                rendered = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                del pix
                running = [f for f in pending if not f.done()]
                if len(running) >= workers * 2:  # bound memory: wait for a free slot
                    concurrent.futures.wait(running, return_when=concurrent.futures.FIRST_COMPLETED)
                fut = pool.submit(_scan_pages, rendered, pno, ocr_engine, ocr_langs, split_spreads)
                fut.add_done_callback(report_scan)
                pending.append(fut)
                pages.append(fut)  # placeholder, resolved below
                continue
            elif kind in ("scanned", "mixed"):
                if ocr_engine is None:
                    no_ocr_pages.append(pno + 1)
                    rp.figures.append(RawFigure(tuple(page.rect), render_clip(page, tuple(page.rect), 150)))
                else:
                    if progress:
                        progress(f"Running OCR on page {pno + 1} of {n}", pno / max(1, n))
                    lines, figs = _ocr_page(page, vno, ocr_engine, ocr_langs)
                    if kind == "mixed":
                        text_lines = _text_lines(page, vno, known_word)
                        lines = text_lines + [l for l in lines
                                              if not any(overlap_ratio(l.bbox, t.bbox) > 0.3 for t in text_lines)]
                    rp.lines, rp.figures = lines, figs
                    info.ocr_used = True
            else:
                all_lines = _text_lines(page, vno, known_word)
                rp.tables = _tables(page)
                rp.tables += _rule_tables(page, rp.tables)
                rp.tables += _caption_tables(page, all_lines, rp.tables)
                table_rects = [t.bbox for t in rp.tables]
                lines = [l for l in all_lines if not any(overlap_ratio(l.bbox, t) > 0.6 for t in table_rects)]
                rp.figures = _figures(page, doc, lines, table_rects, repeated)
                rp.figures += _rotated_blocks(page, [f.bbox for f in rp.figures] + table_rects)
                fig_rects = [f.bbox for f in rp.figures]
                lines = [l for l in lines if not any(overlap_ratio(l.bbox, f) > 0.6 for f in fig_rects)]
                equations, rp.lines = _equations(page, lines)
                rp.figures += equations
            pages.append(rp)
        if no_ocr_pages:
            warnings.append(f"{len(no_ocr_pages)} scanned page(s) are kept as pictures because no OCR engine is "
                            "installed. Install Tesseract OCR to convert them to text.")
        if text_layer_pages and ocr_engine is None:
            warnings.append(f"{len(text_layer_pages)} scanned page(s) used the text the scanner stored in the PDF, "
                            "which can be of lower quality. Install Tesseract OCR for the best results.")
        # resolve the scanned pages that were OCR'd in parallel, then number all pages
        flat: list[RawPage] = []
        for item in pages:
            if isinstance(item, concurrent.futures.Future):
                flat.extend(item.result())
            else:
                flat.append(item)
        for idx, rp in enumerate(flat):
            rp.info.number = idx
            for l in rp.lines:
                l.page = idx
        pages = flat
        toc = [(lvl, title.strip(), pg) for lvl, title, pg, *_ in doc.get_toc(simple=True)] if doc.get_toc() else []
        return RawDocument(pages, meta.get("title") or "", meta.get("author") or "", toc, warnings)
    finally:
        if pool is not None:
            pool.shutdown(wait=True, cancel_futures=True)
        doc.close()
