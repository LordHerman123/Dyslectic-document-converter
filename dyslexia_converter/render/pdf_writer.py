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
from dataclasses import dataclass, replace
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Flowable, Frame, Image, KeepTogether, PageBreak,
                                PageTemplate, Paragraph, Spacer, Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents

from ..fonts import FALLBACK_FAMILY, font_path
from ..settings import FormatSettings
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


def _glyphs(font_name: str) -> dict:
    return pdfmetrics.getFont(font_name).face.charToGlyph


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
    width: float


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

    def _pieces_for(self, text: str, bold: bool, italic: bool, sup: bool) -> list[_Piece]:
        s = self.style
        size = s.size * (0.7 if sup else 1.0)
        rise = s.size * 0.33 if sup else 0.0
        bold = bold or s.bold
        italic = italic or s.italic
        main = self._fonts[(bold, italic)]
        fb = self._fallback[(bold, italic)]
        g_main = _glyphs(main)
        out: list[_Piece] = []
        cur, cur_font = "", main
        for ch in text:
            f = main if (ord(ch) in g_main or ch in " \t") else fb
            if f != cur_font and cur:
                out.append(_Piece(cur, cur_font, size, rise, 0))
                cur = ""
            cur_font = f
            cur += ch
        if cur:
            out.append(_Piece(cur, cur_font, size, rise, 0))
        for p in out:
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
                cur += self._pieces_for(token, r.bold, r.italic, r.superscript)
        if cur:
            words.append(cur)
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

    def wrap(self, availWidth, availHeight):
        self._avail = availWidth
        if self._lines is None or self._lines_width != availWidth:
            if self._lines is None or self._lines_width is not None:
                self._lines = self._break_lines(self._text_width(availWidth))
            self._lines_width = availWidth
        self.width = availWidth
        self.height = len(self._lines) * self.style.leading + self.pad_top + self.pad_bottom
        return availWidth, self.height

    def getSpaceBefore(self):
        return self.style.space_before if self._first else 0

    def getSpaceAfter(self):
        return self.style.space_after if self._last else 0

    def split(self, availWidth, availHeight):
        self.wrap(availWidth, availHeight)
        lead = self.style.leading
        if self.height <= availHeight + 1e-6:
            return [self]
        # the first part keeps the top padding; its bottom padding moves to the second part
        fit = min(len(self._lines) - 1, int((availHeight - self.pad_top) // lead))
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
        for i, line in enumerate(self._lines):
            baseline = top - i * lead - (lead + s.size * 0.62) / 2
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
                t = c.beginText(x, baseline)
                t.setCharSpace(s.char_space)
                for p in word:
                    t.setFont(p.font, p.size)
                    t.setRise(p.rise)
                    t.textOut(p.text)
                if wi < len(line) - 1:
                    t.setRise(0)
                    t.textOut(" ")  # real space so copied text keeps word breaks
                c.drawText(t)
                x += sum(p.width for p in word) + gap
        if s.rule_below is not None and self._last:
            c.setStrokeColor(s.rule_below)
            c.setLineWidth(0.8)
            c.line(x0, 1, x0 + box_w, 1)


# --------------------------------------------------------------------------- document

class _Doc(BaseDocTemplate):
    def afterFlowable(self, flowable):
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


def _table_flowable(item: RItem, s: FormatSettings, col_w: float, max_h: float, printable: bool) -> tuple[Flowable, str]:
    tab = item.table
    rows = tab.rows if tab else []
    n_cols = max((len(r) for r in rows), default=0)
    size = max(9.0, s.font_size * 0.8)
    min_col = 1.6 * cm
    usable = tab is not None and tab.reliable and s.table_mode != "image" and n_cols and n_cols * min_col <= col_w
    reg = register_font(s.font, False, False)
    bold = register_font(s.font, True, False)
    if not usable:
        if tab is not None and tab.fallback_image is not None:
            fake = RItem("image", image=tab.fallback_image, natural_width=item.natural_width)
            return _image_flowable(fake, col_w, max_h), "Table shown as an image of the original."
        return Spacer(1, 1), ""
    ink = s.ink_saving or printable
    cell = ParagraphStyle("cell", fontName=reg, fontSize=size, leading=size * 1.45, alignment=TA_LEFT,
                          textColor=colors.black if ink else colors.HexColor(s.text_color))
    head = ParagraphStyle("head", parent=cell, fontName=bold)
    pad = 12  # cell padding left + right
    lengths = [max((len(r[i]) if i < len(r) else 0) for r in rows) for i in range(n_cols)]

    def longest_word(i: int) -> float:
        return max((pdfmetrics.stringWidth(w, bold if ri == 0 else reg, size)
                     for ri, r in enumerate(rows) if i < len(r) for w in r[i].split()), default=0) + pad

    mins = [max(min_col * 0.6, longest_word(i)) for i in range(n_cols)]
    if sum(mins) > col_w:
        if tab is not None and tab.fallback_image is not None:
            fake = RItem("image", image=tab.fallback_image, natural_width=item.natural_width)
            return _image_flowable(fake, col_w, max_h), "Table shown as an image of the original (too wide)."
        mins = [col_w / n_cols] * n_cols
    weights = [math.sqrt(max(3, l)) for l in lengths]
    spare = col_w - sum(mins)
    widths = [m + spare * w / sum(weights) for m, w in zip(mins, weights)]

    def esc(t: str) -> str:
        return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    data = [[Paragraph(esc(r[i]) if i < len(r) else "", head if ri == 0 else cell) for i in range(n_cols)]
            for ri, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    style = [("GRID", (0, 0), (-1, -1), 0.5, TABLE_GRID if not ink else colors.grey),
             ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]
    if not ink:
        style.append(("BACKGROUND", (0, 0), (-1, 0), TABLE_HEAD))
    t.setStyle(TableStyle(style))
    return t, ""


def build_pdf(result: ComposeResult, s: FormatSettings, title: str = "", author: str = "",
              printable: bool = False) -> bytes:
    """Render the composed document to PDF bytes."""
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
    while i < len(items):
        it = items[i]
        kind = it.kind
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
    return buf.getvalue()
