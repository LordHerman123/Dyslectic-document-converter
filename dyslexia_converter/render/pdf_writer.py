"""PDF export (A4) with full control over typography.

ReportLab's stock ``Paragraph`` cannot apply letter spacing or extra word
spacing with embedded TrueType fonts, so text is set by :class:`RichParagraph`,
a small line-breaking flowable that supports both, plus per-character font
fallback for Unicode coverage. ReportLab's platypus engine still takes care
of pagination, keep-with-next, tables and the table of contents.

The output keeps real, selectable text and embeds (subsets of) the fonts.
"""
from __future__ import annotations

import io
import math
import re
import threading
from dataclasses import dataclass, replace
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, Image, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from ..fonts import FALLBACK_FAMILY, MATH_FAMILY, font_path
from ..settings import FormatSettings
from ..model import ImageData
from .compose import ComposeResult, RItem, Run
from .labels import label as doc_label

# Palette modelled on the reference conversions
CREAM = colors.HexColor("#FDFCF5")
BLUE_TINT = colors.HexColor("#F4F8FC")
BOX_FILL = colors.HexColor("#F3F0E2")
BOX_BAR = colors.HexColor("#B8AD7F")
RULE = colors.HexColor("#D8D2B8")
TABLE_HEAD = colors.HexColor("#EDE8D5")
TABLE_GRID = colors.HexColor("#D8D2B8")
MUTED = colors.HexColor("#5a5a5a")

_registered: dict[str, str] = {}


def register_font(family: str, bold: bool, italic: bool) -> str:
    path = font_path(family, bold, italic)
    name = _registered.get(path)
    if name is None:
        name = "F" + re.sub(r"\W", "", path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].rsplit(".", 1)[0])
        pdfmetrics.registerFont(TTFont(name, path))
        _registered[path] = name
    return name


_GLYPH_CACHE: dict[str, frozenset] = {}


def _glyphs(font_name: str) -> frozenset:
    """The characters a font can really draw (ReportLab maps missing ones to the empty glyph 0)."""
    found = _GLYPH_CACHE.get(font_name)
    if found is None:
        found = frozenset(c for c, g in pdfmetrics.getFont(font_name).face.charToGlyph.items() if g)
        _GLYPH_CACHE[font_name] = found
    return found


# --------------------------------------------------------------------------- text flowable

@dataclass
class PStyle:
    family: str
    size: float
    leading: float
    color: colors.Color
    align: str = "left"
    char_space: float = 0.0
    word_extra: float = 0.0
    space_before: float = 0.0
    space_after: float = 0.0
    left_indent: float = 0.0
    right_indent: float = 0.0
    marker_width: float = 0.0
    bold: bool = False
    italic: bool = False
    background: Optional[colors.Color] = None
    bar: Optional[colors.Color] = None
    border: Optional[colors.Color] = None
    padding: float = 0.0
    pad_top: Optional[float] = None
    pad_bottom: Optional[float] = None
    rule_below: Optional[colors.Color] = None
    extend_bg_below: bool = False


@dataclass
class _Piece:
    text: str
    font: str
    size: float
    rise: float
    width: float  # how far the pen moves on
    back: float = 0.0  # drawn this far to the left (an index stacked under/over the previous one)
    image: Optional[ImageData] = None  # a small formula picture instead of text
    height: float = 0.0


class RichParagraph(Flowable):
    def __init__(self, runs: list[Run], style: PStyle, marker: str = "", outline: Optional[tuple[int, str]] = None,
                 keep_with_next: bool = False, _lines=None, _first=True, _last=True):
        super().__init__()
        self.runs = runs
        self.style = style
        self.marker = marker
        self.outline = outline
        self.keepWithNext = keep_with_next
        self._lines = _lines
        self._lines_width: Optional[float] = None
        self._first = _first
        self._last = _last
        self._fonts = {(b, i): register_font(style.family, b, i) for b in (False, True) for i in (False, True)}
        self._fallback = {(b, i): register_font(FALLBACK_FAMILY, b, i) for b in (False, True) for i in (False, True)}
        self._math = {(b, i): register_font(MATH_FAMILY, b, i) for b in (False, True) for i in (False, True)}

    def __repr__(self) -> str:
        text = "".join(r.text for r in self.runs)
        return f"<RichParagraph {text[:60]!r} lines={len(self._lines or [])} first={self._first}>"

    def identity(self, maxLen=None) -> str:
        return repr(self)

    # ----------------------------------------------------------- measurement
    @property
    def pad_top(self) -> float:
        s = self.style
        return (s.padding if s.pad_top is None else s.pad_top) if self._first else 0.0

    @property
    def pad_bottom(self) -> float:
        s = self.style
        return (s.padding if s.pad_bottom is None else s.pad_bottom) if self._last else 0.0

    def _pieces_for(self, text: str, bold: bool, italic: bool, sup: bool, sub: bool = False,
                    math: bool = False) -> list[_Piece]:
        s = self.style
        # formulas use a Times-style serif (as in the paper); it looks smaller than a sans at the same size
        base = s.size * (1.06 if math else 1.0)
        size = base * (0.7 if (sup or sub) else 1.0)
        rise = s.size * 0.33 if sup else (-s.size * 0.16 if sub else 0.0)
        bold = bold or s.bold
        italic = italic or (s.italic and not math)
        main = (self._math if math else self._fonts)[(bold, italic)]
        fb = self._fallback[(bold, italic)]
        g_main = _glyphs(main)
        out: list[_Piece] = []
        cur, cur_font = "", main
        images = _render_state.images
        for ch in text:
            img = images.get(ch)
            if img is not None:
                if cur:
                    out.append(_Piece(cur, cur_font, size, rise, 0))
                    cur = ""
                # a little larger than the text scale: text-style fractions are small in the original too
                scale = (s.size / img.text_size if img.text_size else 1.0) * INLINE_FORMULA_BOOST
                w = (img.width_pt or img.width * 72 / 300) * scale
                h = w * img.height / max(1, img.width)
                out.append(_Piece(ch, "", size, -img.descent * scale, w, image=img, height=h))
                continue
            f = main if (ord(ch) in g_main or ch in " \t") else fb
            if f != cur_font and cur:
                out.append(_Piece(cur, cur_font, size, rise, 0))
                cur = ""
            cur_font = f
            cur += ch
        if cur:
            out.append(_Piece(cur, cur_font, size, rise, 0))
        for p in out:
            if p.image is None:
                p.width = pdfmetrics.stringWidth(p.text, p.font, p.size) + s.char_space * len(p.text)
        return out

    def _words(self) -> list[list[_Piece]]:
        words: list[list[_Piece]] = []
        cur: list[_Piece] = []
        for r in self.runs:
            for token in re.split(r"(\s+)", r.text):
                if not token:
                    continue
                if token.isspace():
                    if cur:
                        words.append(cur)
                        cur = []
                    continue
                cur += self._pieces_for(token, r.bold, r.italic, r.superscript, r.subscript, r.math)
        if cur:
            words.append(cur)
        for word in words:
            _stack_indices(word)
        return words

    def _space_width(self) -> float:
        s = self.style
        f = self._fonts[(s.bold, s.italic)]
        return pdfmetrics.stringWidth(" ", f, s.size) + s.char_space + s.word_extra

    @property
    def marker_width(self) -> float:
        s = self.style
        if not self.marker:
            return s.marker_width
        mw = pdfmetrics.stringWidth(self.marker, self._fonts[(s.bold, False)], s.size) + s.size * 0.6
        return max(s.marker_width, mw)

    def _text_width(self, avail: float) -> float:
        s = self.style
        return max(20.0, avail - s.left_indent - s.right_indent - self.marker_width
                   - 2 * (s.padding if s.background or s.border else 0))

    def _break_lines(self, width: float) -> list[list[list[_Piece]]]:
        space = self._space_width()
        lines: list[list[list[_Piece]]] = []
        line: list[list[_Piece]] = []
        line_w = 0.0
        for word in self._words():
            ww = sum(p.width for p in word)
            if ww > width:  # break a very long word (URL, formula) by characters
                for chunk in self._split_long(word, width):
                    if line:
                        lines.append(line)
                    line, line_w = [chunk], sum(p.width for p in chunk)
                continue
            need = ww if not line else line_w + space + ww
            if need <= width + 0.01:
                line.append(word)
                line_w = need
            else:
                lines.append(line)
                line, line_w = [word], ww
        if line:
            lines.append(line)
        return lines or [[]]

    def _split_long(self, word: list[_Piece], width: float) -> list[list[_Piece]]:
        chunks: list[list[_Piece]] = []
        cur: list[_Piece] = []
        cur_w = 0.0
        cs = self.style.char_space
        for p in word:
            if p.image is not None:  # a formula picture is never split
                if cur_w + p.width > width and cur:
                    chunks.append(cur)
                    cur, cur_w = [], 0.0
                cur.append(p)
                cur_w += p.width
                continue
            for ch in p.text:
                w = pdfmetrics.stringWidth(ch, p.font, p.size) + cs
                if cur_w + w > width and cur:
                    chunks.append(cur)
                    cur, cur_w = [], 0.0
                if cur and cur[-1].font == p.font and cur[-1].size == p.size and cur[-1].rise == p.rise:
                    cur[-1].text += ch
                    cur[-1].width += w
                else:
                    cur.append(_Piece(ch, p.font, p.size, p.rise, w))
                cur_w += w
        if cur:
            chunks.append(cur)
        return chunks

    def _line_height(self, line) -> float:
        """Normal leading, or more when a line holds a formula picture taller than the text."""
        s = self.style
        h = s.leading
        for word in line:
            for p in word:
                if p.image is not None:
                    descent = -p.rise
                    h = max(h, 2 * (p.height - descent) - 0.62 * s.size + 2, 2 * descent + 0.62 * s.size + 2)
        return h

    def wrap(self, availWidth, availHeight):
        self._avail = availWidth
        if self._lines is None or self._lines_width != availWidth:
            if self._lines is None or self._lines_width is not None:
                self._lines = self._break_lines(self._text_width(availWidth))
            self._lines_width = availWidth
        self.width = availWidth
        self._heights = [self._line_height(l) for l in self._lines]
        self.height = sum(self._heights) + self.pad_top + self.pad_bottom
        return availWidth, self.height

    def getSpaceBefore(self):
        return self.style.space_before if self._first else 0

    def getSpaceAfter(self):
        return self.style.space_after if self._last else 0

    def split(self, availWidth, availHeight):
        self.wrap(availWidth, availHeight)
        if self.height <= availHeight + 1e-6:
            return [self]
        # the first part keeps the top padding; its bottom padding moves to the second part
        fit, used = 0, self.pad_top
        for h in self._heights:
            if used + h > availHeight + 1e-6:
                break
            used += h
            fit += 1
        fit = min(len(self._lines) - 1, fit)
        total = len(self._lines)
        if fit < 2 or total < 4:
            return []  # avoid orphans: move whole paragraph
        if total - fit < 2:
            fit = total - 2
        a = RichParagraph(self.runs, self.style, self.marker, self.outline, False,
                          self._lines[:fit], self._first, False)
        b = RichParagraph(self.runs, self.style, "", None, self.keepWithNext, self._lines[fit:], False, self._last)
        for p in (a, b):
            p._lines_width = None
        return [a, b]

    # --------------------------------------------------------------- drawing
    def draw(self):
        c = self.canv
        s = self.style
        boxed = s.background or s.border
        pad_x = s.padding if boxed else 0.0
        x0 = s.left_indent
        box_w = self.width - s.left_indent - s.right_indent
        if s.background is not None:
            extra = s.space_after if (self._last and s.extend_bg_below) else 0
            c.setFillColor(s.background)
            c.rect(x0, -extra, box_w, self.height + extra, stroke=0, fill=1)
        if s.border is not None:
            c.setStrokeColor(s.border)
            c.setLineWidth(0.6)
            c.rect(x0, 0, box_w, self.height, stroke=1, fill=0)
        if s.bar is not None:
            extra = s.space_after if (self._last and s.extend_bg_below) else 0
            c.setFillColor(s.bar)
            c.rect(x0, -extra, 3, self.height + extra, stroke=0, fill=1)
        if self.outline is not None and self._first:
            level, title = self.outline
            key = f"h{id(self)}"
            c.bookmarkPage(key)
            try:
                c.addOutlineEntry(title[:120], key, level=level, closed=False)
            except ValueError:
                c.addOutlineEntry(title[:120], key, level=0, closed=False)

        text_x = x0 + pad_x + self.marker_width
        width = self._text_width(self._avail)
        space = self._space_width()
        lead = s.leading
        c.setFillColor(s.color)
        top = self.height - self.pad_top
        heights = getattr(self, "_heights", None) or [lead] * len(self._lines)
        line_top = top
        for i, line in enumerate(self._lines):
            baseline = line_top - (heights[i] + s.size * 0.62) / 2
            line_top -= heights[i]
            if i == 0 and self.marker and self._first:
                mf = self._fonts[(s.bold, False)]
                t = c.beginText(x0 + pad_x, baseline)
                t.setFont(mf, s.size)
                t.setCharSpace(0)
                t.textOut(self.marker)
                c.drawText(t)
            natural = sum(sum(p.width for p in w) for w in line) + space * max(0, len(line) - 1)
            gap = space
            last_line = i == len(self._lines) - 1 and self._last
            if s.align == "justify" and not last_line and len(line) > 1:
                gap = space + (width - natural) / (len(line) - 1)
            x = text_x
            if s.align == "center":
                x = text_x + max(0.0, (width - natural) / 2)
            for wi, word in enumerate(line):
                px = x
                for pi, p in enumerate(word):
                    if p.image is not None:
                        c.drawImage(ImageReader(io.BytesIO(p.image.data)), px, baseline + p.rise, p.width, p.height,
                                    mask="auto")
                        px += p.width
                        continue
                    t = c.beginText(px - p.back, baseline)
                    t.setCharSpace(s.char_space)
                    t.setFont(p.font, p.size)
                    t.setRise(p.rise)
                    t.textOut(p.text)
                    if pi == len(word) - 1 and wi < len(line) - 1:
                        t.setRise(0)
                        t.textOut(" ")  # real space so copied text keeps word breaks
                    c.drawText(t)
                    px += p.width
                x += sum(p.width for p in word) + gap
        if s.rule_below is not None and self._last:
            c.setStrokeColor(s.rule_below)
            c.setLineWidth(0.8)
            c.line(x0, 1, x0 + box_w, 1)


INLINE_FORMULA_BOOST = 1.15


class _RenderState(threading.local):
    images: dict = {}


_render_state = _RenderState()


def _stack_indices(word: list[_Piece]) -> None:
    """A subscript directly followed by a superscript (or the reverse) is drawn stacked, as in x_i^2."""
    for a, b in zip(word, word[1:]):
        if a.image is not None or b.image is not None:
            continue
        if a.rise and b.rise and (a.rise > 0) != (b.rise > 0) and not a.back:
            natural = b.width
            b.back = a.width
            b.width = max(0.0, natural - a.width)


# --------------------------------------------------------------------------- document

class _SourceMark(Flowable):
    """Takes no room: tells the document which page of the original the content that follows comes from."""

    def __init__(self, page: Optional[int]):
        super().__init__()
        self.page = page

    def wrap(self, avail_w, avail_h):
        return 0, 0

    def draw(self):
        pass


class _Doc(BaseDocTemplate):
    def handle_documentBegin(self):
        # every build pass starts afresh: page of the converted PDF -> pages of the original shown on it
        self.page_map: dict[int, set[int]] = {}
        self._source: Optional[int] = None
        super().handle_documentBegin()

    def afterFlowable(self, flowable):
        if isinstance(flowable, _SourceMark):
            self._source = flowable.page
            return
        if self._source is not None and not isinstance(flowable, (Spacer, PageBreak, CondPageBreak)):
            self.page_map.setdefault(self.page - 1, set()).add(self._source)
        if isinstance(flowable, RichParagraph) and flowable.outline is not None and flowable._first:
            level, title = flowable.outline
            if level <= 2:
                key = f"h{id(flowable)}"
                self.notify("TOCEntry", (level, title, self.page, key))


def _styles(s: FormatSettings, printable: bool) -> dict[str, PStyle]:
    ink = s.ink_saving or printable
    color = colors.black if ink else colors.HexColor(s.text_color)
    lead = s.font_size * s.line_spacing
    boxes = s.boxed_sections and not ink
    base = PStyle(s.font, s.font_size, lead, color, s.alignment, s.letter_spacing, s.word_spacing,
                  0, s.paragraph_spacing)
    hs = s.heading_scale
    styles = {
        "paragraph": base,
        "title": replace(base, size=s.font_size * 1.45 * hs, leading=s.font_size * 1.45 * hs * 1.3, bold=True,
                         space_after=s.paragraph_spacing * 0.8, align="left"),
        "authors": replace(base, space_after=s.paragraph_spacing * 0.6, align="left"),
        "small": replace(base, size=max(8.0, s.font_size * 0.78), leading=max(8.0, s.font_size * 0.78) * 1.5,
                         color=color if ink else MUTED, space_after=s.paragraph_spacing * 0.6, align="left"),
        "caption": replace(base, size=max(9.0, s.font_size * 0.85), leading=max(9.0, s.font_size * 0.85) * 1.5,
                           space_after=s.paragraph_spacing, align="left"),
        "list_item": replace(base, marker_width=s.font_size * 1.6, left_indent=s.font_size * 0.4,
                             space_after=s.paragraph_spacing * 0.6),
        "reference": replace(base, size=s.font_size * 0.95, leading=s.font_size * 0.95 * s.line_spacing,
                             space_after=s.paragraph_spacing * 0.6, align="left"),
        "endnote": replace(base, size=s.font_size * 0.92, leading=s.font_size * 0.92 * s.line_spacing,
                           marker_width=s.font_size * 4.4, space_after=s.paragraph_spacing * 0.5, align="left"),
        "footnote": replace(base, size=s.font_size * 0.85, leading=s.font_size * 0.85 * s.line_spacing,
                            space_after=s.paragraph_spacing * 0.5, align="left"),
        "quote": replace(base, left_indent=s.font_size * 1.2, right_indent=s.font_size * 0.6,
                         background=BOX_FILL if boxes else None, bar=BOX_BAR if not printable else None,
                         padding=s.font_size * 0.8, extend_bg_below=False),
        "box_heading": replace(base, bold=True, background=BOX_FILL if boxes else None,
                               bar=BOX_BAR if not ink else None, padding=s.font_size * 0.9,
                               pad_bottom=s.font_size * 0.2, space_after=0, extend_bg_below=True),
        "box_paragraph": replace(base, background=BOX_FILL if boxes else None, bar=BOX_BAR if not ink else None,
                                 padding=s.font_size * 0.9, pad_top=0, pad_bottom=s.font_size * 0.4,
                                 extend_bg_below=True),
        "about": replace(base, size=max(8.5, s.font_size * 0.78), leading=max(8.5, s.font_size * 0.78) * 1.5,
                         color=color if ink else MUTED, space_before=s.paragraph_spacing * 2, align="left",
                         border=RULE if not ink else colors.grey, padding=s.font_size * 0.7),
    }
    for level in range(1, 7):
        factor = {1: 1.15, 2: 1.05, 3: 1.0}.get(level, 1.0) * hs
        size = s.font_size * factor
        styles[f"heading{level}"] = replace(base, size=size, leading=size * 1.35, bold=True, align="left",
                                            space_before=s.paragraph_spacing * (1.6 if level == 1 else 1.1),
                                            space_after=s.paragraph_spacing * 0.7,
                                            rule_below=RULE if (level <= 2 and boxes) else None,
                                            italic=level >= 4)
    return styles


def _image_flowable(item: RItem, col_w: float, max_h: float) -> Optional[Flowable]:
    img = item.image
    if img is None:
        return None
    pw, ph = img.width, img.height
    natural = item.natural_width or pw * 72 / 200
    w = min(col_w, max(natural * 1.35, col_w * 0.6))
    h = w * ph / max(1, pw)
    if h > max_h:
        h = max_h
        w = h * pw / max(1, ph)
    return Image(io.BytesIO(img.data), width=w, height=h, hAlign="LEFT")


def _equation_flowable(item: RItem, s: FormatSettings, col_w: float) -> Optional[Flowable]:
    """A display equation exactly as typeset in the paper, scaled like the text around it."""
    img = item.image
    if img is None:
        return None
    scale = s.font_size / img.text_size if img.text_size else 1.3
    w = (item.natural_width or img.width * 72 / 300) * scale
    w = min(w, col_w)
    h = w * img.height / max(1, img.width)
    fl = Image(io.BytesIO(img.data), width=w, height=h, hAlign="CENTER")
    fl._alt = img.alt  # type: ignore[attr-defined]
    return fl


def _table_flowable(item: RItem, s: FormatSettings, col_w: float, max_h: float, printable: bool) -> tuple[Flowable, str]:
    tab = item.table
    rows = tab.rows if tab else []
    n_cols = max((len(r) for r in rows), default=0)
    usable = tab is not None and tab.reliable and s.table_mode != "image" and n_cols >= 1
    reg = register_font(s.font, False, False)
    bold = register_font(s.font, True, False)

    def picture(note: str) -> tuple[Flowable, str]:
        if tab is not None and tab.fallback_image is not None:
            fake = RItem("image", image=tab.fallback_image, natural_width=item.natural_width)
            return _image_flowable(fake, col_w, max_h), note
        return Spacer(1, 1), ""

    if not usable:
        return picture("Table shown as an image of the original.")
    header_rows = max(1, min(tab.header_rows, len(rows) - 1)) if len(rows) > 1 else 1
    bold_cells = tab.bold_cells or set()
    pad = 10  # cell padding left + right

    def is_bold(ri: int, ci: int) -> bool:
        return ri < header_rows or (ri, ci) in bold_cells

    def longest_word(i: int, size: float) -> float:
        return max((pdfmetrics.stringWidth(w, bold if is_bold(ri, i) else reg, size)
                    for ri, r in enumerate(rows) if i < len(r) for w in r[i].split()), default=0) + pad

    # wide tables (many columns of numbers) get a smaller font before they fall back to a picture
    size = max(9.0, s.font_size * 0.8)
    while True:
        mins = [max(0.9 * cm if n_cols <= 6 else 0.6 * cm, longest_word(i, size)) for i in range(n_cols)]
        if sum(mins) <= col_w or size <= 7.0:
            break
        size -= 0.5
    if sum(mins) > col_w:
        return picture("Table shown as an image of the original (too wide).")
    lengths = [max((len(r[i]) if i < len(r) else 0) for r in rows) for i in range(n_cols)]
    weights = [math.sqrt(max(3, l)) for l in lengths]
    spare = col_w - sum(mins)
    widths = [m + spare * w / sum(weights) for m, w in zip(mins, weights)]
    ink = s.ink_saving or printable
    cell = ParagraphStyle("cell", fontName=reg, fontSize=size, leading=size * 1.45, alignment=TA_LEFT,
                          textColor=colors.black if ink else colors.HexColor(s.text_color))
    strong = ParagraphStyle("strong", parent=cell, fontName=bold)

    def esc(t: str) -> str:
        return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    data = [[Paragraph(esc(r[i]) if i < len(r) else "", strong if is_bold(ri, i) else cell) for i in range(n_cols)]
            for ri, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=header_rows, hAlign="LEFT")
    style = [("GRID", (0, 0), (-1, -1), 0.5, TABLE_GRID if not ink else colors.grey),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
             ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if not ink:
        style.append(("BACKGROUND", (0, 0), (-1, header_rows - 1), TABLE_HEAD))
    t.setStyle(TableStyle(style))
    return t, ""


def build_pdf(result: ComposeResult, s: FormatSettings, title: str = "", author: str = "",
              printable: bool = False) -> bytes:
    """Render the composed document to PDF bytes."""
    _render_state.images = result.inline_images
    buf = io.BytesIO()
    page_w, page_h = A4
    ml, mr, mt, mb = (s.margin_left * cm, s.margin_right * cm, s.margin_top * cm, s.margin_bottom * cm)
    avail = page_w - ml - mr
    col_w = min(avail, s.reading_width * cm)
    frame_x = ml + (avail - col_w) / 2
    frame_h = page_h - mt - mb
    tint = None if (printable or s.ink_saving) else {"cream": CREAM, "blue": BLUE_TINT}.get(s.page_tint)
    pad = 6

    def on_page(canv, doc):
        canv.saveState()
        if tint is not None:
            canv.setFillColor(tint)
            canv.rect(frame_x - pad, mb - pad, col_w + 2 * pad, frame_h + 2 * pad, stroke=0, fill=1)
        if s.page_numbers:
            canv.setFont(register_font(s.font, False, False), 9)
            canv.setFillColor(MUTED if tint is not None else colors.black)
            canv.drawCentredString(page_w / 2, max(0.6 * cm, mb / 2 - 4), str(doc.page))
        canv.restoreState()

    doc = _Doc(buf, pagesize=A4, leftMargin=ml, rightMargin=mr, topMargin=mt, bottomMargin=mb,
               title=title or "Converted document", author=author,
               subject="Reformatted for easier reading", creator="Dyslexia Converter")
    frame = Frame(frame_x, mb, col_w, frame_h, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate("main", [frame], onPage=on_page)])

    styles = _styles(s, printable)
    story: list[Flowable] = []

    if s.include_contents and sum(1 for lvl, _ in result.headings if lvl <= 2) >= 5:
        toc = TableOfContents()
        reg = register_font(s.font, False, False)
        toc.levelStyles = [
            ParagraphStyle(f"toc{i}", fontName=reg, fontSize=s.font_size * (1.0 if i == 0 else 0.92),
                           leading=s.font_size * 1.7, leftIndent=i * s.font_size * 1.4, firstLineIndent=0)
            for i in range(3)]
        toc.dotsMinLevel = -1
        story.append(RichParagraph([Run(doc_label(result.language, "contents"))], styles["heading1"],
                                   keep_with_next=True))
        story.append(toc)
        story.append(PageBreak())

    # normalise heading levels so the PDF outline never skips a level
    prev_level = -1
    items = result.items
    i = 0
    last_source: Optional[int] = None
    while i < len(items):
        it = items[i]
        kind = it.kind
        # moved notes and the converter's own note do not follow the original's page order
        source = None if kind in ("endnote", "about") else result.block_pages.get(it.block_id, last_source)
        if source != last_source:
            story.append(_SourceMark(source))
            last_source = source
        if kind == "image":
            fl = _image_flowable(it, col_w, frame_h * 0.7)
            if fl is not None:
                if i + 1 < len(items) and items[i + 1].kind == "caption":
                    cap = items[i + 1]
                    story.append(KeepTogether([Spacer(1, s.paragraph_spacing * 0.5), fl, Spacer(1, 4),
                                               RichParagraph(cap.runs, styles["caption"])]))
                    i += 2
                    continue
                story += [Spacer(1, s.paragraph_spacing * 0.5), fl, Spacer(1, s.paragraph_spacing)]
            i += 1
            continue
        if kind == "equation":
            fl = _equation_flowable(it, s, col_w)
            if fl is not None:
                story += [Spacer(1, s.paragraph_spacing * 0.35), fl, Spacer(1, s.paragraph_spacing * 0.6)]
            i += 1
            continue
        if kind == "table":
            fl, note = _table_flowable(it, s, col_w, frame_h * 0.8, printable)
            story.append(fl)
            if note:
                story.append(RichParagraph([Run(note)], styles["small"]))
            story.append(Spacer(1, s.paragraph_spacing))
            i += 1
            continue
        if kind in ("heading", "box_heading"):
            level = max(1, it.level or 1)
            outline_level = min(level - 1, prev_level + 1)
            prev_level = outline_level
            st = styles["box_heading"] if kind == "box_heading" else styles[f"heading{min(level, 6)}"]
            prev_is_heading = i > 0 and items[i - 1].kind in ("heading", "box_heading", "title")
            if not prev_is_heading:
                # room for this heading, any headings directly below it, and 3 body lines
                need = st.leading * 2 + st.space_before + styles["paragraph"].leading * 3
                j = i + 1
                while j < len(items) and items[j].kind in ("heading", "box_heading"):
                    need += st.leading * 2 + st.space_before
                    j += 1
                story.append(CondPageBreak(need))
            story.append(RichParagraph(it.runs, st, outline=(outline_level, it.text.strip()),
                                       keep_with_next=True))
            i += 1
            continue
        if kind == "title":
            story.append(RichParagraph(it.runs, styles["title"], outline=(0, it.text.strip()), keep_with_next=True))
            prev_level = 0
            i += 1
            continue
        st = styles.get(kind, styles["paragraph"])
        if kind == "caption" and it.keep_with_next and i + 1 < len(items) and items[i + 1].kind == "table":
            fl, note = _table_flowable(items[i + 1], s, col_w, frame_h * 0.8, printable)
            group = [RichParagraph(it.runs, st), fl]
            if note:
                group.append(RichParagraph([Run(note)], styles["small"]))
            story.append(KeepTogether(group))
            story.append(Spacer(1, s.paragraph_spacing))
            i += 2
            continue
        if kind == "box_paragraph":
            last = i + 1 >= len(items) or items[i + 1].kind != "box_paragraph"
            st = replace(st, pad_bottom=s.font_size * 0.9 if last else st.pad_bottom,
                         extend_bg_below=not last, space_after=s.paragraph_spacing * (1.4 if last else 0.6))
        elif kind == "quote":
            # consecutive quote paragraphs (a quotation and its "-Author" line) share one box
            first = i == 0 or items[i - 1].kind != "quote"
            last = i + 1 >= len(items) or items[i + 1].kind != "quote"
            st = replace(st, pad_top=None if first else s.font_size * 0.2,
                         pad_bottom=None if last else s.font_size * 0.2, extend_bg_below=not last,
                         space_after=s.paragraph_spacing * (1.2 if last else 0.4))
        marker = it.marker
        story.append(RichParagraph(it.runs, st, marker=marker, keep_with_next=it.keep_with_next))
        i += 1

    if not story:
        story.append(RichParagraph([Run(doc_label(result.language, "no_text"))], styles["paragraph"]))
    doc.multiBuild(story)
    _render_state.page_map = {page: sorted(src) for page, src in doc.page_map.items()}
    return buf.getvalue()


def last_page_map() -> dict[int, list[int]]:
    """For the PDF just built on this thread: each converted page -> the original pages its content is from."""
    return dict(getattr(_render_state, "page_map", {}) or {})
