"""Turn a :class:`Document` plus user settings into a neutral render model.

All presentation-level transformations happen here, at render time, so they
can be switched on and off without re-running extraction:

* applying accepted OCR corrections
* moving citations to a numbered list
* moving footnotes to the end
* bolding the first part of words
* hiding running headers/footers

The text of every block is carried through unchanged apart from these
explicit, user-controlled transformations.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Optional

from ..model import Block, BlockKind, Document, ImageData, TableData, map_styles
from ..settings import FormatSettings
from ..transform.bionic import bold_ranges
from ..transform.citations import Citation, find_citations, match_reference
from ..structure.detector import LIST_RE, FOOTNOTE_START_RE
from .labels import label as doc_label


@dataclass
class Run:
    text: str
    bold: bool = False
    italic: bool = False
    superscript: bool = False
    marker: bool = False  # inserted marker such as [3] or [Note 1]
    subscript: bool = False
    math: bool = False  # part of a formula: shown in a serif maths font


@dataclass
class RItem:
    kind: str
    runs: list[Run] = field(default_factory=list)
    level: int = 0
    marker: str = ""  # list marker / reference number shown in the margin
    image: Optional[ImageData] = None
    table: Optional[TableData] = None
    block_id: str = ""
    keep_with_next: bool = False
    note: str = ""  # small print (e.g. "table shown as image")
    natural_width: float = 0.0  # width in the original PDF (points)

    @property
    def text(self) -> str:
        return "".join(r.text for r in self.runs)


@dataclass
class ComposeResult:
    items: list[RItem]
    headings: list[tuple[int, str]]  # (level, text) for the document map
    citation_count: int = 0
    uncertain_citations: list[tuple[str, Citation]] = field(default_factory=list)
    language: str = "en"  # language of the words the converter adds (Contents, Notes, ...)
    inline_images: dict[str, ImageData] = field(default_factory=dict)  # small formulas inside the text
    block_pages: dict[str, int] = field(default_factory=dict)  # block id -> page of the original it came from


# -------------------------------------------------------------------- helpers

def _runs_from(text: str, styles, bold_spans: list[tuple[int, int]],
               replacements: list[tuple[int, int, str]], keep_italic: bool = True) -> list[Run]:
    """Split ``text`` into runs honouring styles, bionic bold and replacements."""
    cuts = {0, len(text)}
    for s in styles:
        cuts |= {max(0, min(len(text), s.start)), max(0, min(len(text), s.end))}
    for a, b in bold_spans:
        cuts |= {a, b}
    for a, b, _ in replacements:
        cuts |= {a, b}
    points = sorted(cuts)
    runs: list[Run] = []
    rep_at = {a: (b, r) for a, b, r in replacements}
    skip_until = -1
    for a, b in zip(points, points[1:]):
        if a < skip_until:
            continue
        if a in rep_at:
            end, rep = rep_at[a]
            runs.append(Run(rep, marker=True))
            skip_until = end
            continue
        seg = text[a:b]
        if not seg:
            continue
        bold = any(s.bold and s.start <= a and b <= s.end for s in styles)
        italic = keep_italic and any(s.italic and s.start <= a and b <= s.end for s in styles)
        sup = any(s.superscript and s.start <= a and b <= s.end for s in styles)
        sub = any(s.subscript and s.start <= a and b <= s.end for s in styles)
        math = any(s.math and s.start <= a and b <= s.end for s in styles)
        bb = any(x <= a and b <= y for x, y in bold_spans)
        runs.append(Run(seg, bold=bold or bb, italic=italic, superscript=sup, subscript=sub and not sup, math=math))
    # merge neighbours with identical style
    merged: list[Run] = []
    for r in runs:
        if merged and not r.marker and not merged[-1].marker and \
                _style(merged[-1]) == _style(r):
            merged[-1].text += r.text
        else:
            merged.append(r)
    return merged


def _style(r: Run) -> tuple:
    return r.bold, r.italic, r.superscript, r.subscript, r.math


def _math_spans(styles) -> list[tuple[int, int]]:
    return [(s.start, s.end) for s in styles if s.math]


def _strip_marker(text: str) -> tuple[str, str]:
    m = LIST_RE.match(text)
    if not m:
        return "", text
    return text[:m.end()].strip(), text[m.end():]


def _superscript_spans(text: str, styles) -> list[tuple[int, int]]:
    # superscripts inside formulas (x², W^Q) are never note markers or citations
    return [(s.start, s.end) for s in styles if s.superscript and not s.math and 0 <= s.start < s.end <= len(text)]


# -------------------------------------------------------------------- compose

def compose(doc: Document, settings: FormatSettings, ai_citation_decisions: Optional[dict[str, bool]] = None,
            citation_threshold: float = 0.9) -> ComposeResult:
    ai_citation_decisions = ai_citation_decisions or {}
    lang = doc.language or "en"
    blocks = [b for b in doc.blocks if not (b.kind == BlockKind.FURNITURE and settings.remove_headers_footers)]
    references = [b for b in doc.blocks if b.kind == BlockKind.REFERENCE]
    ref_texts = [doc.display_text(b) for b in references]
    n_refs = len(references)

    # ---- footnotes
    footnotes = [b for b in blocks if b.kind == BlockKind.FOOTNOTE]
    note_numbers: dict[str, int] = {}  # footnote block id -> number
    labels_by_page: dict[tuple[int, str], Block] = {}
    for fn in footnotes:
        if fn.footnote_label:
            labels_by_page.setdefault((fn.page, fn.footnote_label), fn)

    # ---- citation numbering (only when relocating)
    citation_numbers: dict[str, int] = {}
    citation_list: list[tuple[int, str, Optional[int]]] = []  # (number, original item text, ref index)
    next_extra = n_refs + 1
    uncertain: list[tuple[str, Citation]] = []

    def citation_number(item: str) -> int:
        nonlocal next_extra
        key = re.sub(r"^\s*(see(?:\s+also)?|e\.\s?g\.|cf\.|i\.\s?e\.|also|for example|zie(?:\s+ook)?)\s*,?\s*", "",
                     item, flags=re.I).strip()
        if key in citation_numbers:
            return citation_numbers[key]
        ref_idx = match_reference(key, ref_texts)
        if ref_idx >= 0:
            num = ref_idx + 1
        else:
            num = next_extra
            next_extra += 1
        citation_numbers[key] = num
        citation_list.append((num, key, ref_idx if ref_idx >= 0 else None))
        return num

    items: list[RItem] = []
    headings: list[tuple[int, str]] = []
    note_counter = 0
    size_chars: dict[float, int] = {}
    for b in blocks:
        if b.kind == BlockKind.PARAGRAPH:
            size_chars[round(b.font_size)] = size_chars.get(round(b.font_size), 0) + len(b.text)
    body_size = max(size_chars, key=size_chars.get) if size_chars else 0

    for b in blocks:
        text = doc.display_text(b)
        styles = map_styles(b.styles, b.text, doc.corrections_for(b.id))

        if b.kind == BlockKind.IMAGE and b.image is not None and b.image.kind == "equation":
            items.append(RItem("equation", image=b.image, block_id=b.id, natural_width=b.bbox[2] - b.bbox[0]))
            continue
        if b.kind == BlockKind.IMAGE:
            if b.image and (b.image.kind != "decorative"
                            or (settings.show_decorative_images and not settings.ink_saving)):
                items.append(RItem("image", image=b.image, block_id=b.id,
                                   natural_width=b.bbox[2] - b.bbox[0]))
                if b.image.kind == "unreadable-text":
                    items.append(RItem("small", [Run(doc_label(lang, "unreadable"))]))
            continue
        if b.kind == BlockKind.TABLE:
            items.append(RItem("table", table=b.table, block_id=b.id, natural_width=b.bbox[2] - b.bbox[0]))
            continue
        if b.kind == BlockKind.FOOTNOTE and settings.move_footnotes:
            continue  # collected at the end

        replacements: list[tuple[int, int, str]] = []
        is_ref = b.kind == BlockKind.REFERENCE

        # footnote markers in body text
        if b.kind not in (BlockKind.FOOTNOTE, BlockKind.REFERENCE) and settings.move_footnotes:
            for s, e in _superscript_spans(text, styles):
                label = text[s:e].strip()
                fn = labels_by_page.get((b.page, label)) or labels_by_page.get((b.page + 1, label))
                if fn is None:
                    continue
                if fn.id not in note_numbers:
                    note_counter += 1
                    note_numbers[fn.id] = note_counter
                replacements.append((s, e, f" [{doc_label(lang, 'note', n=note_numbers[fn.id])}]"))

        # citations
        if settings.move_citations and not is_ref and b.kind not in (BlockKind.TITLE, BlockKind.HEADING):
            sup = [sp for sp in _superscript_spans(text, styles) if not any(r[0] == sp[0] for r in replacements)]
            for c in find_citations(text, n_refs, sup):
                if c.kind != "author_date":
                    continue  # numbered citations are already compact
                decision = ai_citation_decisions.get(c.key)
                accepted = c.confidence >= citation_threshold if decision is None else decision
                if not accepted:
                    if c.confidence >= 0.5 and decision is None:
                        uncertain.append((b.id, c))
                    continue
                marks = "".join(f"[{citation_number(it)}]" for it in c.items)
                # keep the space before the citation, drop the parentheses only
                replacements.append((c.start, c.end, marks))
        replacements.sort()
        # drop overlapping replacements
        clean: list[tuple[int, int, str]] = []
        for r in replacements:
            if not clean or r[0] >= clean[-1][1]:
                clean.append(r)

        bionic_ok = settings.bold_word_start and (not is_ref or settings.bold_in_references) \
            and b.kind not in (BlockKind.TITLE,)
        bold_spans = bold_ranges(text, settings.bold_amount) if bionic_ok else []
        if bold_spans and clean:
            bold_spans = [(a, e) for a, e in bold_spans if not any(r0 <= a < r1 for r0, r1, _ in clean)]
        # formulas are never bolded
        if bold_spans:
            maths = _math_spans(styles)
            bold_spans = [(a, e) for a, e in bold_spans if not any(m0 <= a < m1 for m0, m1 in maths)]
        # never bionic-bold inside citations
        if bold_spans and not settings.bold_in_references:
            cites = [(c.start, c.end) for c in find_citations(text, n_refs)]
            bold_spans = [(a, e) for a, e in bold_spans if not any(c0 <= a < c1 for c0, c1 in cites)]

        kind = b.kind.value
        marker, rest = "", text
        if b.kind == BlockKind.LIST_ITEM:
            marker, rest = _strip_marker(text)
        runs = _runs_from(text, styles, bold_spans, clean)
        if marker:
            runs = _drop_prefix(runs, len(text) - len(rest))
        item = RItem(kind, runs, level=b.level, marker=marker, block_id=b.id)
        if b.kind in (BlockKind.HEADING, BlockKind.TITLE):
            item.keep_with_next = True
            if b.kind == BlockKind.HEADING:
                headings.append((b.level or 1, text))
        if b.kind == BlockKind.CAPTION and b.caption_for:
            # tables: caption precedes the table; keep them together
            target = doc.block(b.caption_for)
            if target is not None and target.kind == BlockKind.TABLE:
                item.keep_with_next = True
        if b.kind == BlockKind.FURNITURE:
            item.kind = "small"
        elif b.kind == BlockKind.PARAGRAPH and body_size and b.font_size < body_size * 0.85:
            # small print in the original: table/figure notes, journal metadata
            after_float = items and items[-1].kind in ("table", "image", "caption")
            item.kind = "caption" if after_float else "small"
        items.append(item)

    # images keep with a following caption
    for i, it in enumerate(items[:-1]):
        if it.kind == "image" and items[i + 1].kind == "caption":
            it.keep_with_next = True

    # ---- abstract box: paragraphs directly after an "Abstract" heading
    for i, it in enumerate(items):
        if it.kind == "heading" and re.match(r"^\s*(abstract|samenvatting|summary)\b", it.text, re.I):
            it.kind = "box_heading"
            j = i + 1
            while j < len(items) and items[j].kind == "paragraph":
                items[j].kind = "box_paragraph"
                j += 1

    # ---- numbered references when citations were converted
    if settings.move_citations and citation_numbers:
        for i, it in enumerate(it for it in items if it.kind == "reference"):
            if not re.match(r"^\s*\[?\d+[\].]", it.text):
                it.marker = f"{i + 1}."

    # ---- endnotes
    if settings.move_footnotes and footnotes:
        numbered = sorted(footnotes, key=lambda f: note_numbers.get(f.id, 10 ** 6))
        items.append(RItem("heading", [Run(doc_label(lang, "notes"))], level=1, keep_with_next=True))
        headings.append((1, doc_label(lang, "notes")))
        extra = note_counter
        for fn in numbered:
            n = note_numbers.get(fn.id)
            if n is None and fn.footnote_label:
                extra += 1
                n = extra
            text = doc.display_text(fn)
            styles = map_styles(fn.styles, fn.text, doc.corrections_for(fn.id))
            m = FOOTNOTE_START_RE.match(text) if fn.footnote_label else None
            body_start = m.end() if m else 0
            runs = _drop_prefix(_runs_from(text, styles, [], []), body_start)
            while runs and not runs[0].text.strip():
                runs.pop(0)
            if runs:
                runs[0].text = runs[0].text.lstrip(" .)")
            # page notes without a marker (affiliations, licences) keep a plain bullet
            marker = f"[{doc_label(lang, 'note', n=n)}]" if n else "\u2013"
            items.append(RItem("endnote", runs, marker=marker, block_id=fn.id))

    extra_citations = [c for c in citation_list if c[2] is None]
    if extra_citations:
        items.append(RItem("heading", [Run(doc_label(lang, "unmatched"))], level=2, keep_with_next=True))
        headings.append((2, doc_label(lang, "unmatched")))
        for num, item_text, _ in sorted(extra_citations):
            items.append(RItem("endnote", [Run(item_text + ".")], marker=f"[{num}]"))

    if settings.about_note:
        items.append(RItem("about", [Run(_about_text(doc, settings, bool(citation_numbers)))]))

    return ComposeResult(items, headings, len(citation_numbers), uncertain, lang, dict(doc.inline_images),
                         {b.id: _physical_page(doc, b.page) for b in doc.blocks})


def _physical_page(doc: Document, page: int) -> int:
    """Page of the original PDF (both halves of a scanned two-page spread come from one PDF page)."""
    if 0 <= page < len(doc.pages) and doc.pages[page].source_page >= 0:
        return doc.pages[page].source_page
    return page


def _drop_prefix(runs: list[Run], n: int) -> list[Run]:
    out = []
    for r in runs:
        if n <= 0:
            out.append(r)
        elif len(r.text) <= n:
            n -= len(r.text)
        else:
            out.append(replace(r, text=r.text[n:]))
            n = 0
    return out


def _about_text(doc: Document, s: FormatSettings, citations_moved: bool) -> str:
    from pathlib import Path

    lang = doc.language or "en"
    parts = [doc_label(lang, "about_source", file=Path(doc.source_path).name, font=s.font,
                       size=f"{s.font_size:g}", spacing=f"{s.line_spacing:g}")]
    parts.append(doc_label(lang, "about_wording"))
    if doc.ocr_used:
        n = sum(1 for c in doc.corrections if c.applied)
        parts.append(doc_label(lang, "about_ocr", n=n))
    if citations_moved:
        parts.append(doc_label(lang, "about_citations"))
    if s.move_footnotes and any(b.kind == BlockKind.FOOTNOTE for b in doc.blocks):
        parts.append(doc_label(lang, "about_notes"))
    return " ".join(parts)
