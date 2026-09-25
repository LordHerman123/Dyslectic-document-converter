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
        return self.bbox[0]

    @property
    def y0(self) -> float:
        return self.bbox[1]

    @property
    def x1(self) -> float:
        return self.bbox[2]

    @property
    def y1(self) -> float:
        return self.bbox[3]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]


@dataclass
class RawFigure:
    bbox: Rect
    image: ImageData


@dataclass
class RawTable:
    bbox: Rect
    table: TableData


@dataclass
class RawPage:
    info: PageInfo
    lines: list[RawLine] = field(default_factory=list)
    figures: list[RawFigure] = field(default_factory=list)
    tables: list[RawTable] = field(default_factory=list)


@dataclass
class RawDocument:
    pages: list[RawPage]
    title: str = ""
    author: str = ""
    toc: list[tuple[int, str, int]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------- helpers

def _area(r: Rect) -> float:
    return max(0.0, r[2] - r[0]) * max(0.0, r[3] - r[1])


def _intersect(a: Rect, b: Rect) -> Rect:
    return (max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]))


def overlap_ratio(inner: Rect, outer: Rect) -> float:
    """Fraction of ``inner`` covered by ``outer``."""
    a = _area(inner)
    return _area(_intersect(inner, outer)) / a if a else 0.0


def _union(a: Rect, b: Rect) -> Rect:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _expand(r: Rect, d: float) -> Rect:
    return (r[0] - d, r[1] - d, r[2] + d, r[3] + d)


def _is_bold_font(name: str, flags: int) -> bool:
    return bool(flags & 16) or bool(re.search(r"bold|black|heavy|semibold|demi", name, re.I))


def _is_italic_font(name: str, flags: int) -> bool:
    return bool(flags & 2) or bool(re.search(r"italic|oblique", name, re.I))


def render_clip(page: pymupdf.Page, rect: Rect, dpi: int = FIGURE_DPI) -> ImageData:
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
        return tuple(pymupdf.Rect(r) * m)

    def direction(d) -> tuple[float, float]:
        q = pymupdf.Point(d) * m - origin
        return (q.x, q.y)

    return rect, direction


@dataclass
class _Span:
    text: str
    bbox: Rect
    baseline: float
    size: float
    font: str
    flags: int
    block_no: int

    @property
    def x0(self) -> float:
        return self.bbox[0]

    @property
    def x1(self) -> float:
        return self.bbox[2]

    @property
    def mid_y(self) -> float:
        return (self.bbox[1] + self.bbox[3]) / 2


# accents typeset above a letter as a separate glyph -> the combining character for that letter
ACCENTS = {"˜": "\u0303", "~": "\u0303", "ˆ": "\u0302", "^": "\u0302", "¯": "\u0304", "ˉ": "\u0304",
           "˙": "\u0307", "¨": "\u0308", "ˇ": "\u030c", "´": "\u0301", "`": "\u0300", "˘": "\u0306",
           "˚": "\u030a", "→": "\u20d7", "\u20d7": "\u20d7", "\u0303": "\u0303", "\u0302": "\u0302",
           "\u0304": "\u0304", "\u0307": "\u0307", "\u0308": "\u0308"}


def _is_accent(sp: "_Span") -> bool:
    t = sp.text.strip()
    return bool(t) and len(t) <= 3 and all(c in ACCENTS or c.isspace() for c in t) and not t.startswith("→")


def _font_family(font: str) -> str:
    """'ABCDEF+NimbusRomNo9L-Regu' -> 'nimbusromno9l', 'CMR10' -> 'cmr'."""
    name = base_font(font).split("-")[0].split(",")[0]
    return re.sub(r"\d+$", "", name).lower()


LEADER_RE = re.compile(r"\s*(?:\.\s?){5,}\s*(?=\S*\s*$)")


def _replace_run(text: str, styles: list[StyleRange], start: int, end: int, repl: str
                 ) -> tuple[str, list[StyleRange]]:
    delta = len(repl) - (end - start)

    def at(i: int) -> int:
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
        keys = [k for k in new_index if k >= i]
        return new_index[min(keys)] if keys else len(out)
    moved = [replace(st, start=at(st.start), end=at(st.end) if st.end < len(text) else len(out)) for st in styles]
    return " " * lead + out, [st for st in moved if st.end > st.start]


def _page_spans(page: pymupdf.Page) -> list[_Span]:
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
            for span in line["spans"]:
                chars = span.get("chars", [])
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


def _rows(spans: list[_Span]) -> list[list[_Span]]:
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
        for row in rows:
            size = max(sp.size, row["size"])
            if by_box:
                # PyMuPDF sometimes reports a symbol's baseline at the height of a neighbouring index;
                # its box still sits where the characters of its line do
                if not row["baseline"] - 0.8 * size <= sp.mid_y <= row["baseline"] + 0.05 * size:
                    continue
            elif abs(sp.baseline - row["baseline"]) > 0.25 * size:
                continue
            if any(sp.x0 < o.x1 - 1 and o.x0 < sp.x1 - 1 for o in row["spans"]):
                continue
            # the PDF may split one line over several blocks; a column gutter is wider than a word gap
            near = -1 <= sp.x0 - row["x1"] < 1.6 * sp.size or -1 <= row["x0"] - sp.x1 < 1.6 * sp.size \
                or (row["x0"] - 1 <= sp.x0 and sp.x1 <= row["x1"] + 1)  # fills a gap inside the line
            if sp.block_no in row["blocks"] or near:
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
                touching = a["x0"] - 1.6 * size <= b["x1"] and b["x0"] - 1.6 * size <= a["x1"]
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
    orphans: list[_Span] = []
    for sp in small:
        best, best_d = None, None
        for row in rows:
            lo, hi = row["baseline"] - 1.05 * row["size"], row["baseline"] + 0.5 * row["size"]
            if lo <= sp.mid_y <= hi and row["x0"] - 1.5 * row["size"] <= sp.x0 <= row["x1"] + 1.5 * row["size"]:
                dist = abs(sp.mid_y - (row["baseline"] - 0.3 * row["size"]))
                if best is None or dist < best_d:
                    best, best_d = row, dist
        if best is not None:
            best["spans"].append(sp)
            best["x1"] = max(best["x1"], sp.x1)
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
            if abs(sp.baseline - row["baseline"]) <= 0.3 * row["size"] and sp.x0 - row["x1"] < 3 * row["size"]:
                row["spans"].append(sp)
                row["x1"] = max(row["x1"], sp.x1)
                break
        else:
            small_rows.append({"baseline": sp.baseline, "size": sp.size, "spans": [sp], "x1": sp.x1})
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


def is_placeholder(ch: str) -> bool:
    return 0xF0000 <= ord(ch) <= 0xFFFFD


def _stacks(row: list[_Span], rules: list[Rect], baseline: float, size: float) -> list[tuple[Rect, list[_Span], str]]:
    """Parts of a text line that are stacked vertically: fractions and big operators with limits.

    Returns (region, spans, text) for each; these cannot be written as text on one line.
    """
    found: list[tuple[Rect, list[_Span], str]] = []

    def cx(sp: _Span) -> float:
        return (sp.x0 + sp.x1) / 2

    for r in rules:
        if not (baseline - 1.3 * size <= r[1] <= baseline + 0.4 * size) or r[2] - r[0] > 14 * size:
            continue
        above = [sp for sp in row if r[0] - 1 <= cx(sp) <= r[2] + 1 and sp.bbox[3] <= r[1] + 1.5]
        below = [sp for sp in row if r[0] - 1 <= cx(sp) <= r[2] + 1 and sp.bbox[1] >= r[3] - 1.5]
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
        lower = [sp for sp in row if sp is not op and op.x0 - 2 <= cx(sp) <= op.x1 + 2 and sp.bbox[1] >= op.bbox[3] - 0.35 * size]
        upper = [sp for sp in row if sp is not op and op.x0 - 2 <= cx(sp) <= op.x1 + 2 and sp.bbox[3] <= op.bbox[1] + 0.35 * size]
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


def _text_lines(page: pymupdf.Page, pno: int) -> list[RawLine]:
    spans = _page_spans(page)
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
    if True:
        for row in _rows(spans):
            bno = Counter(sp.block_no for sp in row).most_common(1)[0][0]
            full = [sp for sp in row if sp.size >= max(o.size for o in row) * 0.85]
            weights = Counter()
            for sp in full:
                weights[round(sp.baseline, 1)] += len(sp.text.strip()) or 1
            baseline = weights.most_common(1)[0][0] if weights else row[0].baseline
            text = ""
            styles: list[StyleRange] = []
            weighted = Counter()
            bold_chars = italic_chars = 0
            fonts = Counter()
            # the text size of the row; a bullet or symbol drawn in a much larger font does not count
            common = Counter()
            for sp in row:
                common[round(sp.size, 1)] += len(sp.text.strip())
            main = common.most_common(1)[0][0] if common else 0
            max_size = max((sp.size for sp in row if not (len(sp.text.strip()) == 1 and not sp.text.strip().isalnum()
                                                             and sp.size > 1.3 * main)), default=0) \
                or max(sp.size for sp in row)
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
            stacks = _stacks(row, rules, baseline, max_size) if any(is_math_font(sp.font) for sp in row) else []
            for k, (_r, members, _t) in enumerate(stacks):
                for sp in members:
                    stack_of[id(sp)] = k
            emitted: set[int] = set()
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
    gap = ln.x0 - prev.x1
    size = max(prev.size, ln.size)
    if prev.baseline and ln.baseline and abs(prev.baseline - ln.baseline) < 0.25 * size \
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

    # merge overlapping regions
    merged = True
    while merged:
        merged = False
        for i in range(len(regions)):
            for j in range(i + 1, len(regions)):
                if _area(_intersect(_expand(regions[i][0], 4), regions[j][0])) > 0:
                    regions[i][0] = _union(regions[i][0], regions[j][0])
                    regions[i][1] = 0
                    del regions[j]
                    merged = True
                    break
            if merged:
                break

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
                if near and len(l.text) < 40 and l.size < body_size * 0.93 and (l.x1 - l.x0) < (reg[0][2] - reg[0][0]) * 1.05:
                    reg[0] = _union(reg[0], l.bbox)
                    reg[1] = 0
                    grown = True
            if not grown:
                break

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
        left = [c for c in cols if c[0] <= l.x0 + 3 and l.x1 <= c[1] + 0.25 * (c[1] - c[0])]
        return max(left, key=lambda c: c[0]) if left else min(cols, key=lambda c: abs(c[0] - l.x0))

    ordered = sorted(lines, key=lambda l: (l.y0, l.x0))
    gaps = [b.y0 - a.y1 for a, b in zip(ordered, ordered[1:])
            if 0 <= b.y0 - a.y1 < 2 * a.size and abs(a.x0 - b.x0) < 2 and len(a.text) > 40]
    typical_gap = statistics.median(gaps) if gaps else body * 0.3

    def spaced(l: RawLine) -> bool:
        """Extra white space above or below, as TeX puts around display equations."""
        def near(o: RawLine) -> bool:
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
        left = column(l)[0]
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
                overlap = min(l.y1, y1) - max(l.y0, y0)
                math, _f, _t, words = _math_profile(l)
                rx1 = max(m.x1 for m in reg)
                # a lone denominator or limit hanging just below or above (partly outside the region)
                piece = bool(re.fullmatch(r"[\w′'∗*+−-]{1,3}", l.text.strip())) and overlap > -0.2 * body and rx0 - 1 <= l.x0 and l.x1 <= rx1 + 1
                beside = piece or overlap > 0.4 * l.height and (len(l.text) <= 25 or (
                    len(l.text) <= 70 and words <= 4 and l.x0 >= rx0 - body))
                # rows of a cases block above or below, indented from the region's left edge
                touching = (l.y0 < y1 + 0.5 * body and l.y1 > y1) or (l.y1 > y0 - 0.5 * body and l.y0 < y0)
                row = touching and l.x0 > rx0 + body and words <= 1 and len(l.text) <= 70 and math > 0 \
                    and not inline(l)
                if beside or row:
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
        ordered = sorted(reg, key=lambda l: (round(l.y0 / 3), l.x0))
        alt = " ".join(l.text for l in ordered)
        for l in reg:
            for ph, im in l.inline_images.items():
                alt = alt.replace(ph, im.alt or "")
        png, width, height = _close_number_gap(pix, body)
        if width != pix.width:
            clip = (clip[0], clip[1], clip[0] + width * 72.0 / EQUATION_DPI, clip[3])
        img = ImageData(png, "png", width, height, kind="equation", alt=alt, text_size=float(body))
        figures.append(RawFigure(clip, img))
    rest = [l for l in lines if id(l) not in used]
    return figures, rest


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
    groups: list[list[Rect]] = []
    for r in rules:
        for g in reversed(groups):
            # same table: booktabs rules share both edges and follow each other within a table's height
            if abs(g[-1][0] - r[0]) < 4 and abs(g[-1][2] - r[2]) < 4 and r[1] - g[-1][1] < 220:
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
            out.append(RawTable(rect, TableData(rows, render_clip(page, _expand(rect, 3)), n_cols <= 10)))
            break
    return out


# --------------------------------------------------------------------------- OCR pages

def _ocr_image(png: bytes, dpi: int, width_pt: float, height_pt: float, pno: int, engine: OcrEngine,
               languages: list[str], crop: Callable[[Rect], ImageData]) -> tuple[list[RawLine], list[RawFigure]]:
    """OCR one image and return lines/figures in points relative to that image."""
    res = engine.recognize(png, languages)
    scale = 72.0 / dpi
    groups: dict[tuple[int, int, int], list] = {}
    for w in res.words:
        groups.setdefault((w.block, w.paragraph, w.line), []).append(w)
    lines: list[RawLine] = []
    for (bn, par, _ln), words in groups.items():
        words.sort(key=lambda w: w.bbox[0])
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
    return lines, figures


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
    def crop(r: Rect) -> ImageData:
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
    words = re.findall(r"[A-Za-z]{3,}", line.text)
    if len(line.text) < 15 or not words:
        return False
    return sum(1 for w in words if known(w)) / len(words) < 0.6


def _replace_garbled_halves(page: pymupdf.Page, lines: list[RawLine], figures: list[RawFigure],
                            known: Callable[[str], bool], photo, dpi: int):
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
                        text_lines = _text_lines(page, vno)
                        lines = text_lines + [l for l in lines
                                              if not any(overlap_ratio(l.bbox, t.bbox) > 0.3 for t in text_lines)]
                    rp.lines, rp.figures = lines, figs
                    info.ocr_used = True
            else:
                all_lines = _text_lines(page, vno)
                rp.tables = _tables(page)
                rp.tables += _rule_tables(page, rp.tables)
                rp.tables += _caption_tables(page, all_lines, rp.tables)
                table_rects = [t.bbox for t in rp.tables]
                lines = [l for l in all_lines if not any(overlap_ratio(l.bbox, t) > 0.6 for t in table_rects)]
                rp.figures = _figures(page, doc, lines, table_rects, repeated)
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
