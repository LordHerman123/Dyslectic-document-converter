"""PDF reading: page-type detection, text/layout extraction, images, tables, OCR.

The original PDF is opened read-only and is never modified.
"""
from __future__ import annotations

import concurrent.futures
import io
import os
import re
import threading
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Optional

import numpy as np
import pymupdf

from ..model import ImageData, OcrWordConfidence, PageInfo, Rect, StyleRange, TableData
from .ocr import OcrEngine

ProgressFn = Callable[[str, float], None]

OCR_DPI = 300
SCAN_DPI = 225  # full-page scans: as accurate as 300 dpi on book text, about a third faster
FIGURE_DPI = 200
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


def _text_lines(page: pymupdf.Page, pno: int) -> list[RawLine]:
    d = page.get_text("dict", flags=pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES)
    to_page, to_dir = _page_mapper(page)
    lines: list[RawLine] = []
    for bno, block in enumerate(d["blocks"]):
        if block.get("type", 0) != 0:
            continue
        for line in block["lines"]:
            dx, dy = to_dir(line["dir"])
            if abs(dy) > 0.1 or dx < 0:  # rotated text (margins, watermarks)
                continue
            text = ""
            styles: list[StyleRange] = []
            weighted = Counter()
            bold_chars = italic_chars = 0
            fonts = Counter()
            max_size = 0.0
            prev_x1 = None
            for span in line["spans"]:
                t = span["text"]
                if not t:
                    continue
                t = t.replace("\u00a0", " ")
                # word-per-span text layers (common in scanner OCR) carry no space characters
                if (prev_x1 is not None and text and not text[-1].isspace() and not t[0].isspace()
                        and to_page(span["bbox"])[0] - prev_x1 > span["size"] * 0.15):
                    text += " "
                prev_x1 = to_page(span["bbox"])[2]
                start = len(text)
                text += t
                size, flags, font = span["size"], span["flags"], span["font"]
                bold = _is_bold_font(font, flags)
                italic = _is_italic_font(font, flags)
                sup = bool(flags & 1)
                n = len(t.strip())
                if not sup:
                    weighted[round(size, 1)] += n
                    max_size = max(max_size, size)
                bold_chars += n if bold else 0
                italic_chars += n if italic else 0
                fonts[font] += n
                if bold or italic or sup:
                    styles.append(StyleRange(start, len(text), bold, italic, sup))
            stripped = text.strip()
            if not stripped:
                continue
            lead = len(text) - len(text.lstrip())
            text = text.strip()
            styles = [StyleRange(max(0, s.start - lead), min(len(text), s.end - lead), s.bold, s.italic,
                                 s.superscript) for s in styles if s.end - lead > 0 and s.start - lead < len(text)]
            total = max(1, len(re.sub(r"\s", "", text)))
            size = weighted.most_common(1)[0][0] if weighted else max_size or 10.0
            lines.append(RawLine(
                text=text, bbox=to_page(line["bbox"]), size=float(size), page=pno, block_no=bno,
                styles=styles, bold=bold_chars / total > 0.6, italic=italic_chars / total > 0.6,
                font=fonts.most_common(1)[0][0] if fonts else "",
            ))
    return _merge_same_baseline(lines)


def _continues_line(prev: RawLine, ln: RawLine) -> bool:
    gap = ln.x0 - prev.x1
    size = max(prev.size, ln.size)
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
        prev.styles += [StyleRange(s.start + base, s.end + base, s.bold, s.italic, s.superscript)
                        for s in ln.styles]
        if ln.size < prev.size * 0.85 and not any(s.superscript for s in ln.styles):
            prev.styles.append(StyleRange(base, base + len(ln.text), superscript=True))
        prev.bbox = _union(prev.bbox, ln.bbox)
    out.sort(key=lambda l: (l.y0, l.x0))
    return out


# --------------------------------------------------------------------------- figures

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
            img = render_clip(page, _expand(rect, 2))
        small = (rect[2] - rect[0]) < 40 and (rect[3] - rect[1]) < 40
        # journal logos / "check for updates" badges near the top of the first page
        logo = (page.number == 0 and rect[3] < prect[3] * 0.3 and _area(rect) < 0.05 * parea
                and not has_text)
        img.kind = "decorative" if (small or logo) else "figure"
        figures.append(RawFigure(rect, img))
    return figures


# --------------------------------------------------------------------------- tables

def _tables(page: pymupdf.Page) -> list[RawTable]:
    out: list[RawTable] = []
    try:
        found = page.find_tables()
    except Exception:
        return out
    for tab in found.tables:
        try:
            rows = tab.extract()
        except Exception:
            rows = []
        rect = tuple(tab.bbox)
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
                rp.tables += _caption_tables(page, all_lines, rp.tables)
                table_rects = [t.bbox for t in rp.tables]
                lines = [l for l in all_lines if not any(overlap_ratio(l.bbox, t) > 0.6 for t in table_rects)]
                rp.figures = _figures(page, doc, lines, table_rects, repeated)
                fig_rects = [f.bbox for f in rp.figures]
                rp.lines = [l for l in lines if not any(overlap_ratio(l.bbox, f) > 0.6 for f in fig_rects)]
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
