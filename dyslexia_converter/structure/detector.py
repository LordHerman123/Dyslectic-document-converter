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
from typing import Callable, Optional, Union

from rapidfuzz import fuzz

from ..extract.layout import reading_order
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
SPECIAL_HEADINGS = re.compile(
    r"^\s*(abstract|samenvatting|summary|keywords|key words|trefwoorden|introduction|inleiding|"
    r"conclusions?|conclusie|discussion|discussie|methods?|methode|results|resultaten|"
    r"acknowledg(e)?ments?|dankwoord|appendix|bijlage|contents|inhoud|inhoudsopgave)\b[\s:.]*$", re.I)

Item = Union[RawLine, RawFigure, RawTable]


@dataclass
class _Para:
    lines: list[RawLine] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(l.text for l in self.lines)

    @property
    def bbox(self):
        return (min(l.x0 for l in self.lines), min(l.y0 for l in self.lines),
                max(l.x1 for l in self.lines), max(l.y1 for l in self.lines))

    @property
    def size(self) -> float:
        c = Counter()
        for l in self.lines:
            c[l.size] += len(l.text)
        return c.most_common(1)[0][0]

    @property
    def bold(self) -> bool:
        n = sum(len(l.text) for l in self.lines)
        return sum(len(l.text) for l in self.lines if l.bold) > 0.6 * n

    @property
    def page(self) -> int:
        return self.lines[0].page


# ----------------------------------------------------------------------------- helpers

def _norm_furniture(text: str) -> str:
    return re.sub(r"\d+", "#", text.strip().lower())


def body_font_size(lines: list[RawLine]) -> float:
    c = Counter()
    for l in lines:
        c[round(l.size * 2) / 2] += len(l.text)
    return c.most_common(1)[0][0] if c else 10.0


def _is_upper_heading(text: str) -> bool:
    letters = [ch for ch in text if ch.isalpha()]
    return len(letters) >= 4 and all(ch.isupper() for ch in letters) and len(text.split()) <= 10


# ----------------------------------------------------------------------------- detector

class StructureDetector:
    def __init__(self, dehyphenate: Optional[Callable[[str, str], bool]] = None,
                 rejoin: Optional[Callable[[str, str], bool]] = None):
        """``dehyphenate(left, right)`` decides whether ``left-`` + ``right``
        at a line break is one hyphenated word that should be joined.
        ``rejoin(left, right)`` does the same for OCR text where the hyphen was lost."""
        self.dehyphenate = dehyphenate or (lambda a, b: False)
        self.rejoin = rejoin or (lambda a, b: False)
        self._counter = 0

    def _id(self) -> str:
        self._counter += 1
        return f"b{self._counter}"

    # --------------------------------------------------------------------- main
    def detect(self, raw: RawDocument, source_path: str = "") -> Document:
        doc = Document(source_path=source_path, pages=[p.info for p in raw.pages],
                       title=raw.title, author=raw.author, toc=raw.toc, warnings=list(raw.warnings))
        all_lines = [l for p in raw.pages for l in p.lines]
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
            page_blocks = self._build_blocks(ordered, b_size, page)
            for l in page.lines:
                if id(l) in furniture:
                    page_blocks.append(Block(self._id(), BlockKind.FURNITURE, l.text, l.page, l.bbox,
                                             source=l.source, font_size=l.size))
            page_blocks += self._footnote_blocks(footnote_lines, b_size)
            blocks += page_blocks
            in_references = in_references or any(
                b.kind == BlockKind.HEADING and REFERENCE_HEADINGS.match(b.text) for b in page_blocks)

        blocks = self._merge_across_breaks(blocks)
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
            if PAGE_NUMBER_RE.match(text):
                result.add(id(l))
            elif n >= 2 and counts[key] >= max(2, 0.4 * n) and len(key) > 2:
                result.add(id(l))
            elif RUNNING_HEAD_RE.match(text) and len(text.split()) <= 10 and counts[key] >= 2:
                # book running heads: "12 CHAPTER TITLE" / "Section title 13", repeated
                result.add(id(l))
        return result

    # --------------------------------------------------------------- footnotes
    def _find_footnotes(self, page: RawPage, lines: list[RawLine], body_size: float) -> list[RawLine]:
        if not lines:
            return []
        h = page.info.height
        normal = [l for l in lines if l.size >= body_size * 0.92 and len(l.text) > 3]
        if not normal:
            return []
        def below_body(l: RawLine) -> bool:
            # no normal-size text further down in the same column
            return not any(n.y0 > l.y0 + 1 and min(n.x1, l.x1) - max(n.x0, l.x0) > 5 for n in normal)

        zone = [l for l in lines if l.size < body_size * 0.88 and l.y0 > h * 0.55 and below_body(l)]
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
        first = zone[0]
        if CAPTION_RE.match(first.text) or REF_BRACKET_RE.match(first.text):
            return []
        # Small print below the body text: real footnotes (with markers) or
        # page notes such as affiliations and licence statements.
        return zone

    def _footnote_blocks(self, lines: list[RawLine], body_size: float) -> list[Block]:
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
        blocks: list[Block] = []
        paras: list[_Para] = []
        lines_seq = [it for it in ordered if isinstance(it, RawLine)]
        gaps = [b.y0 - a.y1 for a, b in zip(lines_seq, lines_seq[1:])
                if 0 <= b.y0 - a.y1 < 1.5 * a.size and abs(a.x0 - b.x0) < 3 * a.size]
        typical_gap = statistics.median(gaps) if gaps else body_size * 0.25

        def flush():
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
        if LIST_RE.match(c.text) or CAPTION_RE.match(c.text) or REF_BRACKET_RE.match(c.text):
            return False
        if p.font and c.font and _family(p.font) != _family(c.font) and len(para.lines) == 1 \
                and (p.x1 - p.x0) < 0.5 * (c.x1 - c.x0) and not (p.italic or c.italic):
            return False  # e.g. a heading set in a different typeface
        moved_column = c.y0 < p.y0 - 2 or c.x0 > p.x1
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
        text = ""
        styles: list[StyleRange] = []
        conf: list[OcrWordConfidence] = []
        for l in lines:
            if text:
                last_word = re.search(r"(\w+)[-­]$", text)
                first_word = re.match(r"(\w+)", l.text)
                if text.endswith("­"):
                    text = text[:-1]
                elif last_word and first_word and l.text[:1].islower() and \
                        self.dehyphenate(last_word.group(1), first_word.group(1)):
                    text = text[:-1]
                elif text.endswith(("-", "/", "–")) and not text.endswith(" -"):
                    pass  # keep compound hyphen, no space
                elif l.source == "ocr" and self._lost_hyphen(text, l.text) is not None:
                    text = self._lost_hyphen(text, l.text)  # "describ" + "ing": OCR lost the hyphen
                else:
                    text += " "
            base = len(text)
            text += l.text
            styles += [StyleRange(s.start + base, s.end + base, s.bold, s.italic, s.superscript) for s in l.styles]
            conf += [OcrWordConfidence(c.start + base, c.end + base, c.confidence) for c in l.conf]
            if l.bold and not any(s.bold for s in l.styles):
                styles.append(StyleRange(base, base + len(l.text), bold=True))
        return text, styles, conf

    def _lost_hyphen(self, text: str, nxt: str) -> Optional[str]:
        """If OCR lost or misread a line-end hyphen ("describ" / "singu." + "larly"),
        return ``text`` ready to be joined without a space; otherwise None."""
        m = re.search(r"([A-Za-z]+)([.,:~=\u00bb]?)$", text)
        right = re.match(r"([a-z]+)", nxt)
        if m and right and self.rejoin(m.group(1), right.group(1)):
            return text[: len(text) - len(m.group(2))]
        return None

    def _para_block(self, p: _Para, body_size: float) -> Block:
        text, styles, conf = self._join_lines(p.lines)
        kind = BlockKind.PARAGRAPH
        if CAPTION_RE.match(text):
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
        return len(p.lines) <= 2 and len(text) < 120 and (p.bold or p.size > body_size * 1.1) \
            and not text.rstrip().endswith((".", ",", ";"))

    # ----------------------------------------------------- cross-page merging
    def _merge_across_breaks(self, blocks: list[Block]) -> list[Block]:
        """Join a paragraph split by a column or page break."""
        out: list[Block] = []
        last_para: Optional[Block] = None
        floats_between = False
        for b in blocks:
            if b.kind in (BlockKind.FURNITURE, BlockKind.FOOTNOTE):
                out.append(b)
                continue
            if b.kind in (BlockKind.IMAGE, BlockKind.TABLE, BlockKind.CAPTION) or (
                    last_para is not None and b.kind == BlockKind.PARAGRAPH
                    and b.font_size < last_para.font_size - 1 and len(b.text) < 200):
                # figures/tables (and their notes) can interrupt a running paragraph
                out.append(b)
                floats_between = True
                continue
            adjacent = last_para is not None and (last_para is out[-1 - _trailing(out)] or floats_between)
            if floats_between and not b.text[:1].islower():
                adjacent = False
            if (b.kind == BlockKind.PARAGRAPH and last_para is not None and adjacent
                    and last_para.kind == BlockKind.PARAGRAPH
                    and abs(last_para.font_size - b.font_size) <= 1.0
                    and not last_para.text.rstrip().endswith(TERMINAL)
                    and not b.text[:1].isupper() and not LIST_RE.match(b.text)):
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
                last_para.styles += [StyleRange(s.start + base, s.end + base, s.bold, s.italic, s.superscript)
                                     for s in b.styles]
                last_para.ocr_confidence += [OcrWordConfidence(c.start + base, c.end + base, c.confidence)
                                             for c in b.ocr_confidence]
                last_para._nlines += getattr(b, "_nlines", 1)  # type: ignore[attr-defined]
                continue
            out.append(b)
            last_para = b
            floats_between = False
        return out

    # --------------------------------------------------------------- headings
    def _classify_headings(self, blocks: list[Block], body: dict) -> None:
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
            if sum(ch.isalpha() for ch in text) < 3 or text[:1].islower():
                continue  # fragments and sentence continuations are never headings
            if _looks_garbled(text):
                continue  # OCR noise is never a heading
            ends_sentence = text.endswith((".", ",", ";")) and not NUMBERED_HEADING_RE.match(text + " x")
            bigger = b.font_size >= bs * (1.25 if b.source == "ocr" else 1.12) or (
                b.source == "text" and b.font_size >= bs * 1.07 and nlines == 1 and len(words) <= 10)
            font = _family(getattr(b, "_font", ""))
            distinct_font = bool(font and body_font and font != body_font and not getattr(b, "_italic", False)
                                 and b.font_size >= bs * 0.95 and nlines == 1 and len(words) <= 10
                                 and font_chars[font] < 0.1 * sum(font_chars.values()))
            numbered = NUMBERED_HEADING_RE.match(text)
            special = SPECIAL_HEADINGS.match(text) or REFERENCE_HEADINGS.match(text)
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
            if (b.kind == BlockKind.IMAGE and nxt.page == b.page
                    and nxt.kind in (BlockKind.PARAGRAPH, BlockKind.LIST_ITEM) and len(nxt.text) < 300
                    and 0 <= nxt.bbox[1] - b.bbox[3] < 40):
                nxt.kind = BlockKind.CAPTION
        targets = [b for b in blocks if b.kind in (BlockKind.IMAGE, BlockKind.TABLE)]
        for cap in [b for b in blocks if b.kind == BlockKind.CAPTION]:
            is_table = bool(re.match(r"^\s*(table|tab\.?|tabel)", cap.text, re.I))
            best, best_d = None, 1e9
            for t in targets:
                if t.page != cap.page or t.id in {c.caption_for for c in blocks if c.caption_for}:
                    continue
                horiz = overlap_ratio((cap.bbox[0], 0, cap.bbox[2], 1), (t.bbox[0], 0, t.bbox[2], 1))
                d = min(abs(cap.bbox[1] - t.bbox[3]), abs(t.bbox[1] - cap.bbox[3]))
                if horiz < 0.2:
                    d += 200
                if is_table == (t.kind == BlockKind.TABLE):
                    d -= 20
                if d < best_d:
                    best, best_d = t, d
            if best is not None and best_d < 150:
                cap.caption_for = best.id
        # move each caption next to its target: figures -> caption after, tables -> caption before
        out = [b for b in blocks if not (b.kind == BlockKind.CAPTION and b.caption_for)]
        for cap in [b for b in blocks if b.kind == BlockKind.CAPTION and b.caption_for]:
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
    return (min(l.x0 for l in lines), min(l.y0 for l in lines), max(l.x1 for l in lines), max(l.y1 for l in lines))


def _slice_styles(styles: list[StyleRange], start: int, end: int) -> list[StyleRange]:
    out = []
    for s in styles:
        a, b = max(s.start, start), min(s.end, end)
        if a < b:
            out.append(StyleRange(a - start, b - start, s.bold, s.italic, s.superscript))
    return out
