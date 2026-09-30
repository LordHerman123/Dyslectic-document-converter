"""Deterministic document-structure detection.

Turns positioned lines into an ordered list of blocks (title, headings,
paragraphs, lists, captions, footnotes, references, figures, tables) using
font size, weight, position, white space, numbering and repeated patterns.
No AI is used here.
"""
from __future__ import annotations

import re
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional, Union

from rapidfuzz import fuzz

from ..extract.layout import column_order, interleaved, pieces, reading_order, untangle
from ..extract.pdf_reader import CAPTION_RE, RawDocument, RawFigure, RawLine, RawPage, RawTable, overlap_ratio
from ..model import Block, BlockKind, Document, OcrWordConfidence, StyleRange

TERMINAL = tuple('.!?:;"”’)')
LIST_RE = re.compile(r"^\s*(?:[\u2022\u2023\u25e6\u2043\u2219\u25aa\u25cf\u25cb\u2013\u2014\-\*\u00b7"
                     r"\u25a0\u25ba\u27a2\uf0b7\uf0a7\uf0d8\uf076]|\.(?=\s+\w)"
                     r"|\(?\d{1,2}[.)]|\(?[a-z][.)]|\(?(?:i{1,3}|iv|v|vi{1,3}|ix|x)[.)])\s+")
NUMBERED_HEADING_RE = re.compile(r"^((?:\d+\.)*\d+\.?|[A-Z]\.|[IVX]{1,5}\.)\s+\S")
PAGE_NUMBER_RE = re.compile(r"^(?:page\s*|pagina\s*|p\.\s*)?[-–(]?\s*\d{1,4}\s*[-–)]?"
                            r"(?:\s*(?:of|/|van)\s*\d{1,4})?$", re.I)
FOOTNOTE_START_RE = re.compile(r"^\s*([\d]{1,3}|[*\u2020\u2021\u00a7\u00b6]+|[a-z])(?=\s|[.)\]]\s|[A-Z])")
REF_BRACKET_RE = re.compile(r"^\s*\[\d{1,4}\]\s")
REFERENCE_HEADINGS = re.compile(
    r"^\s*(?:\d+\.?\s*)?(references|reference list|bibliography|works cited|literature cited|literature|"
    r"sources|referenties|literatuur|literatuurlijst|bronnen|bronvermelding)\s*$", re.I)
RUNNING_HEAD_RE = re.compile(r"^(?:\d{1,4}\s+\S.*|.*\S\s+\d{1,4})$")
CONTINUED_RE = re.compile(r"^\s*\(?\s*(?:cont|cont'd|contd|continued|vervolg|suite|fortsetzung|continua)\s*\.?\s*\)?"
                          r"[\s.:;]*$", re.I)
SUBSECTION_RE = re.compile(r"^\d+(?:\.\d+)+\.?\s+[A-Z]")  # "1.1. Responsibility...": a new section
MARKER_RE = re.compile(r"[a-z](?:,[a-z])*|\d{1,2}|[\u2217*\u2020\u2021\u00a7\u00b6]")  # affiliation marks
FIGURE_DOI_RE = re.compile(r"^(?:doi:\s?|https?://(?:dx\.)?doi\.org/)10\.\S+\.[gt]\d{3}$", re.I)
# a publisher's masthead on the first page, and the journal line "Research Policy 42 (2013) 1568–1580"
MASTHEAD_RE = re.compile(r"^(?:contents lists available at\b|journal homepage:|available online at\b|"
                         r"www\.sciencedirect\.com$|sciencedirect$)", re.I)
JOURNAL_LINE_RE = re.compile(r"^[A-Z][\w&.,:'’ -]{2,80}\s\d{1,4}\s\((?:19|20)\d{2}\)\s[A-Za-z]?\d+(?:\s?[–-]\s?\d+)?$")
SPECIAL_HEADINGS = re.compile(
    r"^\s*(abstract|samenvatting|summary|keywords|key words|trefwoorden|introduction|inleiding|"
    r"conclusions?|conclusie|discussion|discussie|methods?|methode|results|resultaten|"
    r"acknowledg(e)?ments?|dankwoord|appendix|bijlage|contents|inhoud|inhoudsopgave|highlights|article info|"
    r"graphical abstract)\b[\s:.]*$", re.I)

Item = Union[RawLine, RawFigure, RawTable]
# run-in headings of theorem-like blocks
RUN_IN_RE = re.compile(r"^\s*(theorem|lemma|proposition|corollary|definition|remark|example|proof|claim|conjecture|"
                       r"assumption|question|exercise|note|stelling|bewijs|definitie|opmerking|voorbeeld|satz|beweis|"
                       r"théorème|lemme|preuve|démonstration|teorema|lema|prueba|dimostrazione)\b", re.I)


def _caption_start(text: str) -> bool:
    """A caption label ("Fig. 4.", "Table 2:") and not a sentence about a figure ("Fig. 4 shows ...")."""
    m = CAPTION_RE.match(text)
    if not m:
        return False
    return not re.match(r"\s*(?:[,;)]\s*|and\s|&\s|to\s|[-–]\s*\d)?\s*[a-z]", text[m.end():])



@dataclass

class _Para:
    """Lines being gathered into one paragraph during structure detection."""
    lines: list[RawLine] = field(default_factory=list)

    @property
    def text(self) -> str:
        """The paragraph's text (lines joined with spaces, before hyphen repair)."""
        return " ".join(l.text for l in self.lines)

    @property
    def bbox(self):
        """The rectangle around all its lines."""
        return (min(l.x0 for l in self.lines), min(l.y0 for l in self.lines),
                max(l.x1 for l in self.lines), max(l.y1 for l in self.lines))

    @property
    def size(self) -> float:
        """The font size of most of its text."""
        c = Counter()
        for l in self.lines:
            c[l.size] += len(l.text)
        return c.most_common(1)[0][0]

    @property
    def bold(self) -> bool:
        """Whether most of its text is bold."""
        n = sum(len(l.text) for l in self.lines)
        return sum(len(l.text) for l in self.lines if l.bold) > 0.6 * n

    @property
    def page(self) -> int:
        """The page it starts on."""
        return self.lines[0].page


# ----------------------------------------------------------------------------- helpers

def _norm_furniture(text: str) -> str:
    """A header/footer line without its numbers and punctuation, so "Page 3" and "Page 4" count as the same, and so do
    "290 B. Wynne" and "B. Wynne", "CHAPTER 6 « Science" and "CHAPTER 6 » Science" (OCR reads such marks
    differently), or "NEWS FEATURE" and "FEATURE NEWS" (left and right pages)."""
    return " ".join(sorted(re.sub(r"[^\w\s]|\d", " ", text.strip().lower()).split())) or "0"


def body_font_size(lines: list[RawLine]) -> float:
    """The font size of most of the text (the body text), rounded to half points."""
    c = Counter()
    for l in lines:
        c[round(l.size * 2) / 2] += len(l.text)
    return c.most_common(1)[0][0] if c else 10.0


def _is_upper_heading(text: str) -> bool:
    """Whether a short line is all capitals (often a heading in older documents and scans)."""
    letters = [ch for ch in text if ch.isalpha()]
    return len(letters) >= 4 and all(ch.isupper() for ch in letters) and len(text.split()) <= 10


# ----------------------------------------------------------------------------- detector

class StructureDetector:
    """Turns the lines read from a PDF into a :class:`Document` of typed blocks.

    It finds page furniture (running headers, footers, page numbers), footnotes, paragraphs (joining lines and
    repairing hyphenation), list items, captions, headings with their levels (from font size, boldness, numbering
    and the PDF's bookmarks), the title and authors, and the reference list. Everything is rule-based; no AI is
    used.
    """
    def __init__(self, dehyphenate: Optional[Callable[[str, str], bool]] = None,
                 rejoin: Optional[Callable[[str, str], bool]] = None):
        """``dehyphenate(left, right)`` decides whether ``left-`` + ``right``
        at a line break is one hyphenated word that should be joined.
        ``rejoin(left, right)`` does the same for OCR text where the hyphen was lost."""
        self.dehyphenate = dehyphenate or (lambda a, b: False)
        self.rejoin = rejoin or (lambda a, b: False)
        self._counter = 0

    def _id(self) -> str:
        """A new block id (b1, b2, ...)."""
        self._counter += 1
        return f"b{self._counter}"

    # --------------------------------------------------------------------- main
    def detect(self, raw: RawDocument, source_path: str = "", orders: Optional[dict[int, list[int]]] = None,
               extra: Iterable[int] = ()) -> Document:
        """Build the structured document from what was read (``source_path`` is kept for reference).

        ``orders``: for pages with an unusual layout (or where the AI check found text in the wrong place), the
        reading order of their pieces from the optional AI layout check; every other page is read in the local
        order. The pieces of each unusual page, and of the pages in ``extra`` (to ask the AI about), are kept in
        ``layout_pieces``.
        """
        extra = set(extra)
        self.layout_pieces: dict[int, list[list[Item]]] = {}
        doc = Document(source_path=source_path, pages=[p.info for p in raw.pages],
                       title=raw.title, author=raw.author, toc=raw.toc, warnings=list(raw.warnings))
        all_lines = [l for p in raw.pages for l in p.lines]
        for l in all_lines:
            doc.inline_images.update(l.inline_images)
        text_lines = [l for l in all_lines if l.source == "text"]
        ocr_lines = [l for l in all_lines if l.source == "ocr"]
        body = {"text": body_font_size(text_lines), "ocr": body_font_size(ocr_lines)}

        furniture = self._find_furniture(raw)
        in_references = False
        blocks: list[Block] = []
        for page in raw.pages:
            page_body = [l for l in page.lines if id(l) not in furniture]
            b_size = body[page.lines[0].source] if page.lines else body["text"]
            footnote_lines = [] if in_references else self._find_footnotes(page, page_body, b_size)
            fn_ids = {id(l) for l in footnote_lines}
            items: list[Item] = [l for l in page_body if id(l) not in fn_ids]
            items += page.figures + page.tables
            ordered = reading_order(items)
            # a page whose columns are probably mixed up (a box or quote across the column gap) is read column by
            # column from its pieces instead, or in the order the optional AI layout check gave; every other page
            # keeps the order above
            page.info.unusual_layout, page.info.ai_layout = interleaved(ordered), False
            number = page.info.number
            order = (orders or {}).get(number)
            if page.info.unusual_layout or order is not None or number in extra:
                ps = pieces(items)
                self.layout_pieces[number] = ps
                if order is not None and sorted(order) == list(range(len(ps))):
                    page.info.unusual_layout, page.info.ai_layout = False, True
                    ordered = [it for n in order for it in ps[n]]
                elif page.info.unusual_layout:
                    ordered = [it for n in column_order(ps) for it in ps[n]]
                else:
                    ordered = untangle(ordered)
            else:
                ordered = untangle(ordered)  # a pull quote inside a column, with the text wrapped around it
            page_blocks = self._build_blocks(ordered, b_size, page)
            for l in page.lines:
                if id(l) in furniture:
                    page_blocks.append(Block(self._id(), BlockKind.FURNITURE, l.text, l.page, l.bbox,
                                             source=l.source, font_size=l.size))
            page_blocks += self._footnote_blocks(footnote_lines, b_size)
            blocks += page_blocks
            in_references = in_references or any(
                b.kind == BlockKind.HEADING and REFERENCE_HEADINGS.match(b.text) for b in page_blocks)

        blocks = self._merge_across_breaks(blocks, body)
        blocks = self._join_markers(blocks)
        self._classify_headings(blocks, body)
        self._apply_toc(blocks, raw.toc)
        heights = {p.info.number: p.info.height for p in raw.pages}
        self._detect_title_authors(blocks, max(body["text"], body["ocr"]) if not text_lines else body["text"],
                                   heights)
        self._detect_quotes(blocks, body)
        self._mark_references(blocks)
        self._split_references(blocks)
        blocks = self._attach_captions(blocks)
        doc.blocks = blocks
        return doc

    # --------------------------------------------------------------- furniture
    def _find_furniture(self, raw: RawDocument) -> set[int]:
        """Lines near the top or bottom that repeat on many pages (headers, footers, page numbers): their ids, to
        leave them out.
        """
        n = len(raw.pages)
        counts: Counter = Counter()
        candidates = []
        for page in raw.pages:
            h = page.info.height
            seen = set()
            for l in page.lines:
                if l.y1 < h * 0.09 or l.y0 > h * 0.91:
                    key = _norm_furniture(l.text)
                    candidates.append((l, key))
                    if key not in seen:
                        counts[key] += 1
                        seen.add(key)
        result = set()
        for l, key in candidates:
            text = l.text.strip()
            tokens = text.split()
            if PAGE_NUMBER_RE.match(text):
                result.add(id(l))
            elif n >= 2 and counts[key] >= max(2, 0.4 * n) and len(text) > 2 and key != "0":
                result.add(id(l))  # (a line of only numbers and marks, like an equation number "(12)", is no header)
            elif RUNNING_HEAD_RE.match(text) and len(tokens) <= 10 and counts[key] >= 2:
                # book running heads: "12 CHAPTER TITLE" / "Section title 13", repeated
                result.add(id(l))
            elif len(tokens) >= 8 and sum(len(t) == 1 for t in tokens) >= 0.6 * len(tokens) \
                    and re.search(r"(?:\b[A-Za-z0-9] ){5,}[A-Za-z0-9]\b", text):
                # a letter-spaced journal line ("4 2 6 | N A T U R E | V O L 4 9 5"), even where each page words
                # it differently
                result.add(id(l))
            elif text.count(" | ") >= 2 and re.search(r"\d", text) and len(tokens) <= 16:
                result.add(id(l))  # "Nature | Vol 520 | 23 April 2015"
        for page in raw.pages:
            result |= self._page_number_lines(page, result)
            result |= self._masthead_lines(page)
            # "(cont)." / "(continued)" at the top of a page: a box going on from the page before
            result |= {id(l) for l in page.lines if l.y0 < 0.15 * page.info.height and CONTINUED_RE.match(l.text)}
        return result

    @staticmethod
    def _page_number_lines(page: RawPage, known: set[int]) -> set[int]:
        """A page number printed a little inside the margin (book scans often have wide margins): a bare number
        that is the first or last thing on the page, well apart from the text, in the outer fifth of the page."""
        h = page.info.height
        lines = [l for l in page.lines if id(l) not in known]
        if len(lines) < 3:
            return set()
        out = set()
        items = [l.bbox for l in lines] + [f.bbox for f in page.figures] + [t.bbox for t in page.tables]
        for l, lowest in ((max(lines, key=lambda l: l.y1), True), (min(lines, key=lambda l: l.y0), False)):
            if not re.fullmatch(r"[-–]?\s*\d{1,4}\s*[-–]?", l.text.strip()):
                continue
            if lowest and (l.y0 < 0.8 * h or any(b[3] > l.y1 + 1 for b in items)):
                continue
            if not lowest and (l.y1 > 0.2 * h or any(b[1] < l.y0 - 1 for b in items)):
                continue
            others = [b for b in items if b != l.bbox]
            gap = min((l.y0 - b[3] if lowest else b[1] - l.y1) for b in others) if others else 0
            if gap >= 0.8 * max(1.0, l.y1 - l.y0):
                out.add(id(l))
        return out

    @staticmethod
    def _masthead_lines(page: RawPage) -> set[int]:
        """A publisher's masthead above the title ("Contents lists available at ScienceDirect", the journal
        name, "journal homepage: ...", "Research Policy 42 (2013) 1568-1580"): page furniture, not the title."""
        h = page.info.height
        top = [l for l in page.lines if l.y1 < 0.25 * h]
        out = {id(l) for l in top if MASTHEAD_RE.match(l.text.strip())
               or (l.y1 < 0.12 * h and JOURNAL_LINE_RE.match(l.text.strip()))}
        start = [l for l in top if l.text.strip().lower().startswith("contents lists available")]
        end = [l for l in top if l.text.strip().lower().startswith("journal homepage")]
        if start and end:  # the journal's name sits between the two
            y0, y1 = start[0].y0, end[0].y1
            out |= {id(l) for l in top if y0 <= l.y0 and l.y1 <= y1}
        return out

    # --------------------------------------------------------------- footnotes
    def _find_footnotes(self, page: RawPage, lines: list[RawLine], body_size: float) -> list[RawLine]:
        """The footnote lines at the bottom of a page: smaller than the body text with no body text below them."""
        if not lines:
            return []
        h = page.info.height
        normal = [l for l in lines if l.size >= body_size * 0.92 and len(l.text) > 3]
        if not normal:
            return []
        def below_body(l: RawLine) -> bool:
            # no normal-size text further down in the same column
            """Whether no normal-size text follows further down in the same column."""
            return not any(n.y0 > l.y0 + 1 and min(n.x1, l.x1) - max(n.x0, l.x0) > 5 for n in normal)

        zone = [l for l in lines if l.size < body_size * 0.92 and l.y0 > h * 0.55 and below_body(l)]
        if not zone:
            return []
        ref_heads = [r for r in lines if REFERENCE_HEADINGS.match(r.text)]
        # reference lists (below a References heading in the same column) are not notes
        zone = [l for l in zone if not any(r.y1 <= l.y0 and min(r.x1 + 200, l.x1) - max(r.x0, l.x0) > 0
                                           for r in ref_heads)]
        if not zone:
            return []
        # keep only the block of small lines at the very bottom of the page
        zone.sort(key=lambda l: l.y1, reverse=True)
        kept = [zone[0]]
        for l in zone[1:]:
            if min(k.y0 for k in kept) - l.y1 < 3.2 * max(l.height, 1):
                kept.append(l)
            else:
                break
        zone = sorted(kept, key=lambda l: (l.y0, l.x0))
        bottom = max(l.y1 for l in zone)
        ids = {id(l) for l in zone}
        if any(id(o) not in ids and o.y0 > bottom and min(o.x1, l.x1) - max(o.x0, l.x0) > 5
               for o in lines for l in zone):
            return []  # more text follows below it: not the notes at the foot of the page
        # print only a little smaller than the text (9 pt in 10 pt) counts as notes only with a note
        # marker; otherwise it is more likely a quotation set in smaller type
        if min(l.size for l in zone) >= body_size * 0.88 and not any(
                FOOTNOTE_START_RE.match(l.text) or l.text[:1] in "∗⋆†‡§¶*⋄" or
                any(s.superscript and s.start == 0 for s in l.styles) for l in zone):
            return []
        first = zone[0]
        if CAPTION_RE.match(first.text) or REF_BRACKET_RE.match(first.text):
            return []
        if sum(1 for l in zone if REF_BRACKET_RE.match(l.text)) >= 2:
            return []  # the end of a reference list ("[17] ...", "[18] ..."), not notes
        # Small print below the body text: real footnotes (with markers) or
        # page notes such as affiliations and licence statements.
        return zone

    def _footnote_blocks(self, lines: list[RawLine], body_size: float) -> list[Block]:
        """Group footnote lines into one block per note (a new note starts with its number)."""
        if not lines:
            return []
        ordered = reading_order(lines)
        groups: list[list[RawLine]] = []
        for l in ordered:
            is_start = bool(FOOTNOTE_START_RE.match(l.text)) or any(s.superscript and s.start == 0 for s in l.styles)
            prev = groups[-1][-1] if groups else None
            separated = prev is not None and (l.y0 - prev.y1 > 0.6 * l.height or l.y0 < prev.y0 - 2)
            if not groups or separated or (is_start and (l.x0 <= groups[-1][0].x0 + 2 or l.y0 > prev.y1 + 1)):
                groups.append([l])
            else:
                groups[-1].append(l)
        out = []
        for g in groups:
            text, styles, conf = self._join_lines(g)
            m = FOOTNOTE_START_RE.match(text)
            label = m.group(1) if m else None
            b = Block(self._id(), BlockKind.FOOTNOTE, text, g[0].page, _bbox(g), styles=styles,
                      footnote_label=label, source=g[0].source, ocr_confidence=conf,
                      font_size=g[0].size)
            out.append(b)
        return out

    # ------------------------------------------------------------- paragraphs
    def _build_blocks(self, ordered: list[Item], body_size: float, page: RawPage) -> list[Block]:
        """Blocks of one page from its items in reading order: lines become paragraphs; figures, tables and
        formulas become their own blocks.
        """
        blocks: list[Block] = []
        paras: list[_Para] = []
        lines_seq = [it for it in ordered if isinstance(it, RawLine)]
        gaps = [b.y0 - a.y1 for a, b in zip(lines_seq, lines_seq[1:])
                if 0 <= b.y0 - a.y1 < 1.5 * a.size and abs(a.x0 - b.x0) < 3 * a.size]
        typical_gap = statistics.median(gaps) if gaps else body_size * 0.25

        def flush():
            """Turn the paragraphs gathered so far into blocks."""
            for p in paras:
                blocks.append(self._para_block(p, body_size))
            paras.clear()

        for idx, it in enumerate(ordered):
            if isinstance(it, RawFigure):
                flush()
                blocks.append(Block(self._id(), BlockKind.IMAGE, "", page.info.number, it.bbox, image=it.image))
                continue
            if isinstance(it, RawTable):
                flush()
                blocks.append(Block(self._id(), BlockKind.TABLE, "", page.info.number, it.bbox, table=it.table))
                continue
            nxt = ordered[idx + 1] if idx + 1 < len(ordered) and isinstance(ordered[idx + 1], RawLine) else None
            if paras and self._continues(paras[-1], it, nxt, typical_gap):
                paras[-1].lines.append(it)
            else:
                paras.append(_Para([it]))
        flush()
        return blocks

    def _continues(self, para: _Para, c: RawLine, nxt: Optional[RawLine], typical_gap: float) -> bool:
        """Whether line ``c`` continues paragraph ``para`` (same size and style, normal line gap, not a new list
        item or heading); ``nxt`` is the line after.
        """
        p = para.lines[-1]
        size = max(p.size, c.size)
        if (c.source == "ocr" and c.text[:1].islower() and not p.text.rstrip().endswith(TERMINAL)
                and not (c.y0 < p.y0 - 2 or c.x0 > p.x1) and c.y0 - p.y1 < typical_gap + 0.6 * size):
            return True  # a sentence running on to the next line, whatever OCR thinks its size is
        tolerance = 0.22 * size if c.source == "ocr" else 1.0  # OCR size estimates are noisy
        if abs(p.size - c.size) > tolerance:
            return False
        if p.bold != c.bold and (len(p.text) < 120 or len(c.text) < 120):
            return False
        # "(b) a bar chart and" + "(c) a scatter plot": a sentence running on, not a new list item
        running_on = bool(re.match(r"^\s*\((?:[a-z]|[ivx]{1,4}|\d{1,2})\)\s", c.text)) and \
            not p.text.rstrip().endswith(TERMINAL) and abs(c.x0 - p.x0) < 2 and \
            not LIST_RE.match(para.lines[0].text) and len(para.lines) >= 1
        # "cli-" + "- mate deniers": OCR read the line-end hyphen twice; not a new "- " list item
        hyphen_run = c.source == "ocr" and bool(re.search(r"[A-Za-z][-–][^\w\s]{0,2}$", p.text.rstrip())) \
            and bool(re.match(r"^\s*[-–]\s?[a-z]", c.text))
        # "...1.8 million articles" + "— an average revenue per article...": a dash in a sentence, at a line start
        # (an en dash only when the aside closes with a second one: "– based on some criteria – that..."; after a
        # comma a dash starts a list: "we conclude that," + "– if τ = 1, then:")
        dash_on = _dash_goes_on(" ".join(l.text for l in para.lines), c.text) \
            and not p.text.rstrip().endswith(TERMINAL + (",",)) \
            and min(l.x0 for l in para.lines) - 2 <= c.x0 <= p.x0 + 2 and not LIST_RE.match(para.lines[0].text)
        if (LIST_RE.match(c.text) and not running_on and not hyphen_run and not dash_on) \
                or REF_BRACKET_RE.match(c.text):
            return False
        if re.search(r" … \S+\s*$", p.text):
            return False  # an entry of a printed table of contents
        if p.text.rstrip().endswith(TERMINAL) and RUN_IN_RE.match(c.text) and any(
                (st.bold or st.italic) and st.start == 0 for st in c.styles):
            return False  # "Lemma 3.2. ..." or "Proof. ...": a new block right after a sentence ends
        if _caption_start(c.text) and (p.text.rstrip().endswith(TERMINAL) or abs(p.size - c.size) > 0.3):
            return False  # "... presented in" + "Fig. 2. When ..." is one sentence running on
        if p.font and c.font and _family(p.font) != _family(c.font) and len(para.lines) == 1 \
                and (p.x1 - p.x0) < 0.5 * (c.x1 - c.x0) and not (p.italic or c.italic):
            return False  # e.g. a heading set in a different typeface
        moved_column = c.y0 < p.y0 - 2 or c.x0 > p.x1
        if moved_column and (SPECIAL_HEADINGS.match(c.text) or SPECIAL_HEADINGS.match(p.text)):
            return False  # "article info" and "abstract" side by side: two labels
        if moved_column:
            return not p.text.rstrip().endswith(TERMINAL) and not c.text[:1].isupper()
        gap = c.y0 - p.y1
        if gap > typical_gap + 0.45 * size:
            return False
        if p.source == "ocr" and c.block_no // 1000 != p.block_no // 1000 and gap > typical_gap + 0.2 * size:
            return False
        first_x = para.lines[0].x0
        indent = c.x0 - p.x0
        if len(para.lines) >= 2:
            body_x = para.lines[1].x0
            if indent > 0.8 * size and abs(p.x0 - body_x) < 2:
                return False  # first-line indent of a new paragraph
            if indent < -0.8 * size and abs(p.x0 - body_x) < 2 and body_x > first_x + 0.5 * size:
                return False  # new hanging-indent entry (references)
            if indent < -0.8 * size and abs(first_x - body_x) < 2:
                return False
        # previous line ends a sentence clearly short of the column edge
        if p.text.rstrip().endswith((".", "!", "?", ":")):
            right = max(max(l.x1 for l in para.lines), c.x1)
            if right > p.x1 + 2.5 * size:
                return False
        return True

    def _join_lines(self, lines: list[RawLine]) -> tuple[str, list[StyleRange], list[OcrWordConfidence]]:
        """Join a paragraph's lines into one text, repairing words hyphenated at line ends (and junk hyphens from
        OCR), with the style ranges and OCR confidences moved along.
        """
        text = ""
        styles: list[StyleRange] = []
        conf: list[OcrWordConfidence] = []
        for l in lines:
            skip = 0  # characters of junk at the start of this line to drop
            if text:
                last_word = re.search(r"(\w+)[-­]$", text)
                first_word = re.match(r"(\w+)", l.text)
                junk = self._junk_hyphen(text, l.text) if l.source == "ocr" else None
                if text.endswith("­"):
                    text = text[:-1]
                elif junk is not None:
                    text, skip = junk  # "mecha-" + "“nisms", "mal--." + "function": OCR junk around the hyphen
                elif last_word and first_word and l.text[:1].islower() and \
                        self.dehyphenate(last_word.group(1), first_word.group(1)):
                    text = text[:-1]
                elif text.endswith(("-", "/", "–")) and not text.endswith(" -"):
                    pass  # keep compound hyphen, no space
                elif l.source == "ocr" and self._lost_hyphen(text, l.text) is not None:
                    text = self._lost_hyphen(text, l.text)  # "describ" + "ing": OCR lost the hyphen
                else:
                    text += " "
            base = len(text) - skip
            text += l.text[skip:]
            styles += [s.moved(base) for s in l.styles]
            conf += [OcrWordConfidence(c.start + base, c.end + base, c.confidence) for c in l.conf]
            if l.bold and not any(s.bold for s in l.styles):
                styles.append(StyleRange(base, base + len(l.text), bold=True))
        return text, styles, conf

    def _junk_hyphen(self, text: str, nxt: str) -> Optional[tuple[str, int]]:
        """A word hyphenated at a line end with stray OCR marks next to the hyphen ("mal--." + "function",
        "mecha-" + "“nisms", "cli-" + "- mate"). Returns (text without hyphen and junk, number of junk
        characters to drop from the next line), or None."""
        m = re.search(r"([A-Za-z]+)-([-.,:~·'’“”‘\"]{0,2})\s*$", text)
        r = re.match(r"([-–.,:·'’“”‘\"]{0,2}\s?)([a-z]+)", nxt)
        if not m or not r or not (m.group(2) or r.group(1)):
            return None  # no junk: the normal hyphen handling applies
        if not self.dehyphenate(m.group(1), r.group(2)):
            return None
        return text[: m.end(1)], len(r.group(1))

    def _lost_hyphen(self, text: str, nxt: str) -> Optional[str]:
        """If OCR lost or misread a line-end hyphen ("describ" / "singu." + "larly"),
        return ``text`` ready to be joined without a space; otherwise None."""
        m = re.search(r"([A-Za-z]+)([.,:~=\u00bb]?)$", text)
        right = re.match(r"([a-z]+)", nxt)
        if m and right and self.rejoin(m.group(1), right.group(1)):
            return text[: len(text) - len(m.group(2))]
        return None

    def _para_block(self, p: _Para, body_size: float) -> Block:
        """A block for a paragraph: a caption, list item or plain paragraph (headings are decided later)."""
        text, styles, conf = self._join_lines(p.lines)
        kind = BlockKind.PARAGRAPH
        if _caption_start(text):
            kind = BlockKind.CAPTION
        elif LIST_RE.match(text) and not self._heading_like(p, text, body_size):
            kind = BlockKind.LIST_ITEM
        b = Block(self._id(), kind, text, p.page, p.bbox, styles=styles, source=p.lines[0].source,
                  ocr_confidence=conf, font_size=p.size)
        b._bold = p.bold  # type: ignore[attr-defined]
        fonts = Counter()
        for l in p.lines:
            fonts[l.font] += len(l.text)
        b._font = fonts.most_common(1)[0][0] if fonts else ""  # type: ignore[attr-defined]
        b._italic = all(l.italic for l in p.lines)  # type: ignore[attr-defined]
        b._nlines = len(p.lines)  # type: ignore[attr-defined]
        return b

    @staticmethod
    def _heading_like(p: _Para, text: str, body_size: float) -> bool:
        """Whether a short paragraph looks like a heading (bold or larger, one or two lines, no closing
        punctuation).
        """
        return len(p.lines) <= 2 and len(text) < 120 and (p.bold or p.size > body_size * 1.1) \
            and not text.rstrip().endswith((".", ",", ";"))

    # ----------------------------------------------------- cross-page merging
    def _merge_across_breaks(self, blocks: list[Block], body: Optional[dict] = None) -> list[Block]:
        """Join a paragraph split by a column or page break (``body``: the body text size of text and OCR
        pages)."""
        body = body or {}
        first = min((b.page for b in blocks), default=0)
        out: list[Block] = []
        last_para: Optional[Block] = None
        floats_between = False
        for i, b in enumerate(blocks):
            if b.kind in (BlockKind.FURNITURE, BlockKind.FOOTNOTE):
                out.append(b)
                continue
            if _is_equation(b):
                # a display equation is part of the running text: what follows it comes after it
                out.append(b)
                last_para = None
                floats_between = False
                continue
            if b.kind in (BlockKind.IMAGE, BlockKind.TABLE, BlockKind.CAPTION) or (
                    last_para is not None and b.kind == BlockKind.PARAGRAPH
                    and b.font_size < last_para.font_size - 1 and len(b.text) < 200
                    and not (len(b.text) >= 80 and b.font_size >= body.get(b.source, 0) - 0.5 and b.page > first)):
                # figures/tables (and their notes, labels) can interrupt a running paragraph; running text in the
                # body size after a larger line (a heading not recognised yet) is no such note (but on the first
                # page, the author lines under the title stay apart)
                out.append(b)
                floats_between = True
                continue
            adjacent = last_para is not None and (last_para is out[-1 - _trailing(out)] or floats_between)
            if floats_between and not b.text[:1].islower():
                adjacent = False
            dash_on = last_para is not None and adjacent and self._dash_continues(last_para, b, blocks[i + 1:])
            if ((b.kind == BlockKind.PARAGRAPH or dash_on) and last_para is not None and adjacent
                    and last_para.kind == BlockKind.PARAGRAPH
                    and abs(last_para.font_size - b.font_size) <= 1.0
                    and not last_para.text.rstrip().endswith(TERMINAL)
                    and not re.search(r" … \S+\s*$", last_para.text)
                    and not b.text[:1].isupper() and (dash_on or not LIST_RE.match(b.text))
                    and not SPECIAL_HEADINGS.match(b.text) and not SPECIAL_HEADINGS.match(last_para.text)
                    and not SUBSECTION_RE.match(b.text)):
                sep = " "
                left = re.search(r"([A-Za-z]+)-$", last_para.text)
                right = re.match(r"([a-z]+)", b.text)
                if left and right and self.dehyphenate(left.group(1), right.group(1)):
                    last_para.text = last_para.text[:-1]  # word hyphenated across a page break
                    sep = ""
                elif b.source == "ocr" and self._lost_hyphen(last_para.text, b.text) is not None:
                    last_para.text = self._lost_hyphen(last_para.text, b.text)
                    sep = ""
                base = len(last_para.text) + len(sep)
                last_para.text += sep + b.text
                last_para.styles += [s.moved(base) for s in b.styles]
                last_para.ocr_confidence += [OcrWordConfidence(c.start + base, c.end + base, c.confidence)
                                             for c in b.ocr_confidence]
                last_para._nlines += getattr(b, "_nlines", 1)  # type: ignore[attr-defined]
                continue
            out.append(b)
            last_para = b
            floats_between = False
        return out

    @staticmethod
    def _dash_continues(para: Block, b: Block, rest: list[Block]) -> bool:
        """"— an average revenue per article…" at the top of the next column or page, right after a sentence
        that broke off: the paragraph goes on after a dash; it is no list item (unless more items follow)."""
        if b.kind != BlockKind.LIST_ITEM or not _dash_goes_on(para.text, b.text) or para.text.rstrip().endswith(","):
            return False
        if not (b.page != para.page or b.bbox[1] < para.bbox[3] - 2):
            return False  # no column or page break between them
        nxt = next((x for x in rest if x.kind not in (BlockKind.FURNITURE, BlockKind.FOOTNOTE)), None)
        return not (nxt is not None and nxt.kind == BlockKind.LIST_ITEM and nxt.text[:1] == b.text[:1])

    def _join_markers(self, blocks: list[Block]) -> list[Block]:
        """Put a lone superscript marker back in front of its line: the "b" of an affiliation "b University
        of…", printed a little higher and smaller, is read as a line of its own. Figure DOIs printed under a
        caption ("doi:10.1371/journal.pone.0127502.g001") join the caption."""
        out: list[Block] = []
        for i, b in enumerate(blocks):
            prev = out[-1] if out else None
            if b.kind == BlockKind.PARAGRAPH and FIGURE_DOI_RE.match(b.text.strip()):
                cap = next((x for x in reversed(out) if x.kind not in (BlockKind.FURNITURE, BlockKind.FOOTNOTE)),
                           None)
                if cap is not None and cap.kind == BlockKind.CAPTION and cap.page == b.page:
                    cap.text = cap.text.rstrip() + " " + b.text.strip()
                    continue
            if prev is not None and prev.kind == BlockKind.PARAGRAPH and MARKER_RE.fullmatch(prev.text.strip()) \
                    and b.kind == BlockKind.PARAGRAPH and b.page == prev.page and prev.font_size < b.font_size \
                    and 0 <= b.bbox[0] - prev.bbox[2] < 2 * b.font_size \
                    and abs(b.bbox[1] - prev.bbox[1]) < max(b.font_size, 4.0):
                mark = prev.text.strip()
                shift = len(mark) + 1
                b.text = mark + " " + b.text
                b.styles = [StyleRange(0, len(mark), superscript=True)] + [st.moved(shift) for st in b.styles]
                b.ocr_confidence = [OcrWordConfidence(c.start + shift, c.end + shift, c.confidence)
                                    for c in b.ocr_confidence]
                b.bbox = (prev.bbox[0], min(prev.bbox[1], b.bbox[1]), b.bbox[2], max(prev.bbox[3], b.bbox[3]))
                out[-1] = b
                continue
            out.append(b)
        return out

    # --------------------------------------------------------------- headings
    def _classify_headings(self, blocks: list[Block], body: dict) -> None:
        """Decide which paragraphs are headings and give them levels (by size, boldness, font, numbering and
        capitals).
        """
        font_chars: Counter = Counter()
        for b in blocks:
            if b.kind == BlockKind.PARAGRAPH and getattr(b, "_font", ""):
                font_chars[_family(b._font)] += len(b.text)  # type: ignore[attr-defined]
        body_font = font_chars.most_common(1)[0][0] if font_chars else ""
        for b in blocks:
            if b.kind not in (BlockKind.PARAGRAPH, BlockKind.LIST_ITEM):
                continue
            bs = body.get(b.source, 10.0)
            text = b.text.strip()
            words = text.split()
            nlines = getattr(b, "_nlines", 1)
            bold = getattr(b, "_bold", False)
            if not words or nlines > 3 or len(words) > 18:
                continue
            special = SPECIAL_HEADINGS.match(text) or REFERENCE_HEADINGS.match(text)
            if sum(ch.isalpha() for ch in text) < 3 or (text[:1].islower() and not special):
                continue  # fragments and sentence continuations are never headings ("abstract" set in small
                # capitals is a label)
            if _looks_garbled(text):
                continue  # OCR noise is never a heading
            if text[:1] in "“\"‘" and text[-1:] in "”\"’" and len(words) >= 5 and (b.font_size > bs * 1.1 or bold):
                b.kind = BlockKind.QUOTE  # a pull quote set large ("“Simplicity is a virtue...”"), not a heading
                continue
            ends_sentence = text.endswith((".", ",", ";")) and not NUMBERED_HEADING_RE.match(text + " x")
            bigger = b.font_size >= bs * (1.25 if b.source == "ocr" else 1.12) or (
                b.source == "text" and b.font_size >= bs * 1.07 and nlines == 1 and len(words) <= 10)
            font = _family(getattr(b, "_font", ""))
            distinct_font = bool(font and body_font and font != body_font and not getattr(b, "_italic", False)
                                 and b.font_size >= bs * 0.95 and nlines == 1 and len(words) <= 10
                                 and font_chars[font] < 0.1 * sum(font_chars.values()))
            numbered = NUMBERED_HEADING_RE.match(text)
            if special and (bold or bigger or distinct_font or _is_upper_heading(text) or len(words) <= 3):
                b.kind = BlockKind.HEADING
            elif ends_sentence or text.endswith(","):
                continue
            elif bigger and nlines <= 3:
                b.kind = BlockKind.HEADING
            elif (bold or distinct_font) and len(text) <= 120 and nlines <= 2:
                b.kind = BlockKind.HEADING
            elif _is_upper_heading(text) and nlines == 1 and b.source == "ocr" or \
                    _is_upper_heading(text) and nlines == 1 and b.font_size >= bs:
                b.kind = BlockKind.HEADING
            elif numbered and b.source == "ocr" and len(words) <= 8 and not text.endswith("."):
                b.kind = BlockKind.HEADING
            elif b.source == "ocr" and nlines == 1 and _title_case(text) and b.font_size >= bs * 0.93 \
                    and not text.endswith((".", ":", ";", ",")):
                # scans carry no bold/italic information: a short, isolated Title Case line
                b.kind = BlockKind.HEADING
                b._title_case = True  # type: ignore[attr-defined]
            if b.kind == BlockKind.HEADING:
                m = NUMBERED_HEADING_RE.match(text)
                if m and re.match(r"^\d", m.group(1)):
                    b.level = m.group(1).rstrip(".").count(".") + 1
        # size-ranked levels for headings without numbering
        heads = [b for b in blocks if b.kind == BlockKind.HEADING]
        numbered_sizes: dict[float, list[int]] = {}
        for h in heads:
            if h.level:
                numbered_sizes.setdefault(round(h.font_size), []).append(h.level)
        sizes = sorted({round(h.font_size) for h in heads}, reverse=True)
        for h in heads:
            if h.level:
                continue
            if getattr(h, "_title_case", False) and h.font_size <= body.get(h.source, 10) * 1.15:
                h.level = 2  # section heading inside a chapter
                continue
            key = round(h.font_size)
            if key in numbered_sizes:
                h.level = min(numbered_sizes[key])
            else:
                h.level = min(4, sizes.index(key) + 1)
                if not getattr(h, "_bold", False) and h.font_size <= body.get(h.source, 10) + 0.5:
                    h.level = max(h.level, 3)

    def _apply_toc(self, blocks: list[Block], toc: list[tuple[int, str, int]]) -> None:
        """Use the PDF's own bookmarks: the block that best matches each bookmark title becomes a heading of that
        level.
        """
        if not toc:
            return
        for level, title, page in toc:
            best, best_score = None, 0.0
            for b in blocks:
                if b.page not in (page - 1, page - 2, page) or b.kind in (BlockKind.IMAGE, BlockKind.TABLE,
                                                                           BlockKind.FURNITURE):
                    continue
                if len(b.text) > len(title) * 2 + 20:
                    continue
                score = fuzz.ratio(b.text.lower(), title.lower())
                if score > best_score:
                    best, best_score = b, score
            if best is not None and best_score >= 85:
                best.kind = BlockKind.HEADING
                best.level = max(1, min(6, level))

    # -------------------------------------------------------- title / authors
    def _detect_title_authors(self, blocks: list[Block], body_size: float, heights: dict[int, float]) -> None:
        """Find the document title (the largest text high on the first page) and the author line under it."""
        page0 = min((b.page for b in blocks), default=0)
        # book scans: the title page is often the right-hand page of the first spread
        first_page = [b for b in blocks if b.page in (page0, page0 + 1) and b.kind in (BlockKind.HEADING, BlockKind.PARAGRAPH)]
        if not first_page:
            return
        biggest = max(first_page, key=lambda b: b.font_size)
        if biggest.page != page0 and any(b.kind == BlockKind.HEADING and NUMBERED_HEADING_RE.match(b.text)
                                         for b in blocks if b.page == biggest.page):
            return  # the second page already starts a chapter
        page_h = heights.get(biggest.page, 842)
        if biggest.font_size < body_size * 1.25 or biggest.bbox[1] > 0.5 * page_h:
            return
        if REFERENCE_HEADINGS.match(biggest.text) or SPECIAL_HEADINGS.match(biggest.text):
            return
        biggest.kind = BlockKind.TITLE
        biggest.level = 0
        idx = blocks.index(biggest)
        found = 0
        for b in blocks[idx + 1: idx + 7]:
            if b.kind in (BlockKind.FURNITURE, BlockKind.IMAGE, BlockKind.FOOTNOTE):
                continue
            if b.kind not in (BlockKind.PARAGRAPH, BlockKind.HEADING) or b.page != biggest.page or found >= 3:
                break
            if b.font_size < body_size * 0.9:
                continue  # journal metadata printed small next to the title
            t = b.text.strip()
            if SPECIAL_HEADINGS.match(t) or len(t) > 250 or t.endswith("."):
                break
            if b.kind == BlockKind.HEADING and re.match(r"^\d+(\.\d+)*\.?\s+\S", t):
                break  # "1 Introduction": the text has begun ("E. Edge" is an author with an initial)
            n_words = len(t.split())
            if n_words > 15 and t.count(",") < n_words / 8:
                break  # running text (a list of names has a comma every few words)
            if re.search(r",|\band\b|\ben\b|&|\d|@", t) or len(t.split()) <= 6:
                b.kind = BlockKind.AUTHORS
                b.level = 0
                found += 1
            else:
                break

    # ----------------------------------------------------------------- quotes
    def _detect_quotes(self, blocks: list[Block], body: dict) -> None:
        """Block quotations and epigraphs: set smaller and/or indented, often with a "—Author" line."""
        by_page: dict[int, list[Block]] = {}
        for b in blocks:
            if b.kind == BlockKind.PARAGRAPH:
                by_page.setdefault(b.page, []).append(b)
        for page_blocks in by_page.values():
            wide = [b for b in page_blocks if len(b.text) > 200]
            if not wide:
                continue
            left = sorted(b.bbox[0] for b in wide)[len(wide) // 2]
            right = sorted(b.bbox[2] for b in wide)[len(wide) // 2]
            for i, b in enumerate(page_blocks):
                bs = body.get(b.source, 10.0)
                t = b.text.strip()
                attribution = t[:1] in "\u2014\u2013-" and len(t.split()) <= 18
                indented = b.bbox[0] > left + 1.2 * bs and b.bbox[2] < right - 1.2 * bs
                smaller = b.font_size <= bs * 0.9
                nxt = page_blocks[i + 1] if i + 1 < len(page_blocks) else None
                followed_by_attr = nxt is not None and nxt.text.strip()[:1] in "\u2014\u2013" and \
                    len(nxt.text.split()) <= 18
                if attribution and (smaller or indented or i > 0 and page_blocks[i - 1].kind == BlockKind.QUOTE):
                    b.kind = BlockKind.QUOTE
                elif (indented and (smaller or followed_by_attr)) or (smaller and followed_by_attr):
                    b.kind = BlockKind.QUOTE

    # ------------------------------------------------------------- references
    def _mark_references(self, blocks: list[Block]) -> None:
        """Mark the paragraphs under a References/Bibliography heading as reference entries."""
        ref_level: Optional[int] = None
        for b in blocks:
            if b.kind in (BlockKind.HEADING, BlockKind.TITLE):
                if REFERENCE_HEADINGS.match(b.text):
                    ref_level = b.level or 1
                    continue
                if ref_level is not None and (b.level or 1) <= ref_level:
                    ref_level = None
            elif ref_level is not None and b.kind in (BlockKind.PARAGRAPH, BlockKind.LIST_ITEM):
                b.kind = BlockKind.REFERENCE

    def _split_references(self, blocks: list[Block]) -> None:
        """Split reference paragraphs that contain several ``[n]`` entries."""
        i = 0
        while i < len(blocks):
            b = blocks[i]
            if b.kind == BlockKind.REFERENCE:
                cuts = [m.start() for m in re.finditer(r"(?<=\s)\[\d{1,4}\]\s", b.text)]
                if cuts:
                    pieces = []
                    prev = 0
                    for c in cuts + [len(b.text)]:
                        pieces.append((prev, c))
                        prev = c
                    new_blocks = []
                    for s, e in pieces:
                        seg = b.text[s:e]
                        strip = len(seg) - len(seg.lstrip())
                        seg_text = seg.strip()
                        if not seg_text:
                            continue
                        start = s + strip
                        nb = Block(self._id(), BlockKind.REFERENCE, seg_text, b.page, b.bbox,
                                   styles=_slice_styles(b.styles, start, start + len(seg_text)),
                                   source=b.source, font_size=b.font_size,
                                   ocr_confidence=[OcrWordConfidence(c.start - start, c.end - start, c.confidence)
                                                   for c in b.ocr_confidence
                                                   if c.start >= start and c.end <= start + len(seg_text)])
                        new_blocks.append(nb)
                    blocks[i:i + 1] = new_blocks
                    i += len(new_blocks)
                    continue
            i += 1

    # --------------------------------------------------------------- captions
    def _attach_captions(self, blocks: list[Block]) -> list[Block]:
        """Link captions to the nearest figure/table on the same page and keep them adjacent."""
        # book-style captions ("1. Mixed forest ...") directly below a picture
        for i, b in enumerate(blocks[:-1]):
            nxt = blocks[i + 1]
            if (b.kind == BlockKind.IMAGE and nxt.page == b.page and not _is_equation(b)
                    and nxt.kind in (BlockKind.PARAGRAPH, BlockKind.LIST_ITEM) and len(nxt.text) < 300
                    and 0 <= nxt.bbox[1] - b.bbox[3] < 40):
                nxt.kind = BlockKind.CAPTION
        targets = [b for b in blocks if b.kind in (BlockKind.IMAGE, BlockKind.TABLE) and not _is_equation(b)]
        for cap in [b for b in blocks if b.kind == BlockKind.CAPTION]:
            is_table = bool(re.match(r"^\s*(table|tab\.?|tabel)", cap.text, re.I))
            best, best_d = None, 1e9
            for t in targets:
                if t.page != cap.page or t.id in {c.caption_for for c in blocks if c.caption_for}:
                    continue
                horiz = overlap_ratio((cap.bbox[0], 0, cap.bbox[2], 1), (t.bbox[0], 0, t.bbox[2], 1))
                below_target = cap.bbox[1] >= t.bbox[3] - 3
                d = abs(cap.bbox[1] - t.bbox[3]) if below_target else abs(t.bbox[1] - cap.bbox[3])
                if horiz < 0.2:
                    d += 200
                if is_table == (t.kind == BlockKind.TABLE):
                    d -= 20
                # figure captions usually sit below their figure, table captions above their table
                if not is_table and not below_target:
                    d += 40
                if is_table and below_target:
                    d += 15
                if d < best_d:
                    best, best_d = t, d
            if best is not None and best_d < 150:
                cap.caption_for = best.id
        # move each caption next to its target: figures -> caption after, tables -> caption before
        # a figure caption that already follows its figure (and its other panels) stays where it is
        position = {b.id: i for i, b in enumerate(blocks)}
        by_id = {b.id: b for b in blocks}
        staying = set()
        for cap in [b for b in blocks if b.kind == BlockKind.CAPTION and b.caption_for]:
            t = by_id.get(cap.caption_for)
            if t is not None and t.kind == BlockKind.IMAGE and position[cap.id] > position[t.id] \
                    and cap.bbox[1] >= t.bbox[3] - 3 and cap.page == t.page \
                    and all(b.page == cap.page and b.kind != BlockKind.HEADING
                            for b in blocks[position[t.id]:position[cap.id]]):
                staying.add(cap.id)
        out = [b for b in blocks if not (b.kind == BlockKind.CAPTION and b.caption_for) or b.id in staying]
        for cap in [b for b in blocks if b.kind == BlockKind.CAPTION and b.caption_for and b.id not in staying]:
            idx = next(i for i, b in enumerate(out) if b.id == cap.caption_for)
            target = out[idx]
            if target.kind == BlockKind.TABLE:
                out.insert(idx, cap)
            else:
                j = idx + 1
                while j < len(out) and out[j].kind == BlockKind.CAPTION and out[j].caption_for == target.id:
                    j += 1
                out.insert(j, cap)
        return out


def _dash_goes_on(before: str, line: str) -> bool:
    """Whether a line starting with a dash goes on with the sentence before it (a dash in running text, not a list
    bullet): an em dash, or an en dash that opens an aside closed later on the line ("– based on some criteria –
    that...") or closes one opened before ("... – makes little sense")."""
    line = line.lstrip()
    if re.match(r"\u2014\s", line):
        return True
    if re.match(r"\u2013\s", line):
        return bool(re.search(r"\s\u2013\s", line[2:])) or before.count(" \u2013 ") % 2 == 1
    return False


def _is_equation(b: Block) -> bool:
    """Whether a block is a display formula kept as a picture."""
    return b.kind == BlockKind.IMAGE and b.image is not None and b.image.kind == "equation"


def _looks_garbled(text: str) -> bool:
    """Text full of stray symbols or letter salad, as produced by bad OCR."""
    if not text:
        return True
    odd = sum(1 for ch in text if not (ch.isalnum() or ch.isspace() or ch in ".,;:'\"()-\u2013\u2014\u2018\u2019\u201c\u201d?!&/"))
    if odd / len(text) > 0.04 or "^" in text:
        return True
    words = re.findall(r"[A-Za-z]+", text)
    # very long 'words' mean spaces were lost: "monotonicschemesofcentralized"
    return any(len(w) > 22 for w in words)


def _title_case(text: str) -> bool:
    """Whether text is in Title Case (most longer words capitalised): a sign of a heading."""
    words = re.findall(r"[A-Za-z\u00C0-\u024F][\w'\u2019-]*", text)
    if not 2 <= len(words) <= 12 or not text.lstrip("\"'\u201c\u2018(")[:1].isupper():
        return False
    content = [w for w in words if len(w) > 3]
    if not content:
        return False
    return sum(w[0].isupper() for w in content) / len(content) >= 0.75


def _family(font: str) -> str:
    """Font family name without style suffixes (Times-Bold -> times)."""
    f = re.sub(r"^[A-Z]{6}\+", "", font)  # subset prefix
    f = re.split(r"[-,]", f)[0]
    return re.sub(r"(bold|italic|oblique|regular|roman|medium|light|semibold|black|mt|ps)+$", "", f,
                  flags=re.I).lower()


def _trailing(out: list[Block]) -> int:
    """Number of furniture/footnote blocks at the end of ``out``."""
    n = 0
    for b in reversed(out):
        if b.kind in (BlockKind.FURNITURE, BlockKind.FOOTNOTE):
            n += 1
        else:
            break
    return n


def _bbox(lines: list[RawLine]):
    """The rectangle around some lines."""
    return (min(l.x0 for l in lines), min(l.y0 for l in lines), max(l.x1 for l in lines), max(l.y1 for l in lines))


def _slice_styles(styles: list[StyleRange], start: int, end: int) -> list[StyleRange]:
    """The style ranges that fall within text[start:end], moved to count from ``start``."""
    out = []
    for s in styles:
        a, b = max(s.start, start), min(s.end, end)
        if a < b:
            out.append(s.moved(-start, a, b))
    return out
