"""The whole-document check: the AI reads the converted text and points out where the conversion went wrong.

The AI only *points out*; this module checks every finding against the text before it is shown, and the app
makes a fix only when the reader chooses it:

* a finding must quote text that really is in the block it names, or it is dropped;
* a broken or joined word is fixed only when the fix changes nothing but spaces and hyphens ("safe"); a word
  misread in a scan may change a few letters; any other change of the author's words is dropped;
* a header, footer or page number is removed, a heading run into a paragraph is split off, and a block that is
  not a heading becomes normal text;
* text in the wrong place is only shown (with its page), never moved.

Every fix is undoable: text fixes are corrections (the extracted text itself is never changed) and structure
fixes are applied to a copy of the document when it is laid out (:func:`view`).
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, replace
from typing import Optional

from rapidfuzz.distance import Levenshtein

from .model import Block, BlockKind, Document

PART_WORDS = 1800  # words per request: long enough for context, short enough to read carefully
BLOCK_WORDS = 1500  # a longer block is cut (rare)
KINDS = ("word", "scan", "furniture", "heading", "not_heading", "order")
STRUCTURAL = ("heading", "not_heading", "furniture_block")
_SENT = {BlockKind.TITLE: "T", BlockKind.PARAGRAPH: "P", BlockKind.LIST_ITEM: "L", BlockKind.QUOTE: "Q",
         BlockKind.CAPTION: "C", BlockKind.FOOTNOTE: "N"}  # headings: H1-H3
_BREAKS = re.compile(r"[\s\-‐‑­]")  # what a safe word fix may change: spaces and hyphens


@dataclass
class Finding:
    """One place where the conversion probably went wrong, and how the app can fix it."""
    id: str
    kind: str  # word / scan / furniture / heading / not_heading / order
    block_id: str
    page: int  # page of the original PDF (1 = first)
    quote: str  # the text as it is in the converted document
    fix: str = ""  # word and scan: the corrected text
    reason: str = ""  # the AI's reason, in a few words
    before: str = ""  # a few words of the text around the quote (to show it in context)
    after: str = ""
    start: int = -1  # what the fix replaces in the block's own text (-1: it cannot be fixed)
    end: int = -1
    level: int = 0  # heading: the level of the new heading
    whole: bool = False  # furniture: the whole block is a header or footer
    applied: bool = False

    @property
    def fixable(self) -> bool:
        """Whether the app can fix it (text in the wrong place is only shown)."""
        return self.kind != "order" and self.start >= 0

    @property
    def structural(self) -> bool:
        """A fix of the document's structure (a heading, or a whole block hidden), not of its text."""
        return self.kind in ("heading", "not_heading") or (self.kind == "furniture" and self.whole)

    @property
    def safe(self) -> bool:
        """A fix that changes nothing but spaces and hyphens (a broken or joined word): part of "Fix all"."""
        return self.fixable and self.kind == "word"

    @property
    def replacement(self) -> str:
        """The text that replaces the quote when fixed ("" for a header or footer)."""
        return self.fix if self.kind in ("word", "scan") else ""


# ------------------------------------------------------------------------------------------ what is sent
def kind_code(b: Block) -> Optional[str]:
    """The block's kind as the check sees it (None: not checked, e.g. tables, pictures and references)."""
    if b.kind == BlockKind.HEADING:
        return f"H{min(3, max(1, b.level or 1))}"
    return _SENT.get(b.kind)


def block_text(doc: Document, b: Block) -> str:
    """The block's text as the reader sees it, on one line, formulas shown as [formula]."""
    text = doc.display_text(b)
    for ph in doc.inline_images:
        if ph in text:
            text = text.replace(ph, "[formula]")
    words = text.split()
    if len(words) > BLOCK_WORDS:
        words = words[:BLOCK_WORDS] + ["…"]
    return " ".join(words)


def checked_blocks(doc: Document) -> list[tuple[int, Block, str, int, str]]:
    """Every block the check reads: (number, block, kind code, original page, text)."""
    out = []
    for b in doc.blocks:
        code = kind_code(b)
        if code is None:
            continue
        text = block_text(doc, b)
        if not text.strip():
            continue
        if b.source == "ocr":
            code += " scan"
        out.append((len(out), b, code, physical_page(doc, b), text))
    return out


def parts(doc: Document, words: int = PART_WORDS) -> list[list[tuple[int, Block, str, int, str]]]:
    """The checked blocks in parts of about ``words`` words (a block is never split)."""
    out: list[list] = [[]]
    count = 0
    for item in checked_blocks(doc):
        n = len(item[4].split())
        if out[-1] and count + n > words:
            out.append([])
            count = 0
        out[-1].append(item)
        count += n
    return [p for p in out if p]


def word_count(doc: Document) -> int:
    """How many words the check sends."""
    return sum(len(t.split()) for *_, t in checked_blocks(doc))


def physical_page(doc: Document, b: Block) -> int:
    """The page of the original PDF a block is on (1 = first)."""
    if 0 <= b.page < len(doc.pages) and doc.pages[b.page].source_page >= 0:
        return doc.pages[b.page].source_page + 1
    return b.page + 1


# ------------------------------------------------------------------------------------------ the answers
def locate(text: str, quote: str) -> Optional[tuple[int, int]]:
    """Where ``quote`` is in ``text`` (any whitespace between its words), or None."""
    tokens = quote.split()
    if not tokens:
        return None
    i = text.find(quote)
    if i >= 0:
        return i, i + len(quote)
    m = re.search(r"\s+".join(re.escape(t) for t in tokens), text)
    return (m.start(), m.end()) if m else None


def findings_from(answer, part: list, doc: Document, live: Document) -> list[Finding]:
    """The AI's answer for one part, checked: only findings that quote the text of the block they name, with a
    fix only where it is allowed. ``doc`` is the document as it was sent (with structure fixes), ``live`` the
    session's document (whose text the corrections refer to)."""
    if not isinstance(answer, list):
        return []
    by_number = {n: (b, text) for n, b, _, _, text in part}
    levels = Counter(b.level or 1 for b in doc.blocks if b.kind == BlockKind.HEADING)
    out, seen = [], set()
    for r in answer:
        if not isinstance(r, dict) or not isinstance(r.get("b"), int) or r["b"] not in by_number:
            continue
        kind, quote = str(r.get("t", "")).strip().lower(), " ".join(str(r.get("q", "")).split())
        if kind not in KINDS or not quote:
            continue
        b, _ = by_number[r["b"]]
        f = _finding(kind, quote, " ".join(str(r.get("w", "")).split()), str(r.get("r", "")).strip()[:120], b, doc,
                     live, levels)
        if f is not None and f.id not in seen:
            seen.add(f.id)
            out.append(f)
    return out


def _finding(kind: str, quote: str, fix: str, reason: str, b: Block, doc: Document, live: Document,
             levels: Counter) -> Optional[Finding]:
    """One finding, checked against the block's text (None when it does not hold)."""
    shown = doc.display_text(b)
    where = locate(shown, quote)
    if where is None:
        return None  # the AI quoted text that is not there
    s, e = where
    before = shown[:s].split()
    after = shown[e:].split()
    f = Finding("", kind, b.id, physical_page(doc, b), shown[s:e], fix, reason,
                ("…" if len(before) > 10 else "") + " ".join(before[-10:]),
                " ".join(after[:10]) + ("…" if len(after) > 10 else ""))
    own = live.block(b.id)  # the block in the session's document (None for a heading split off by a fix)
    # where the quote is in the block's own text (a block split by a heading fix keeps the end of its text);
    # None when it cannot be fixed there, e.g. the quote runs over an OCR correction
    offset = len(own.text) - len(b.text) if own is not None and own.text.endswith(b.text) else None
    raw = locate(b.text, quote) if offset is not None else None
    words = len(quote.split())
    if kind in ("word", "scan"):
        if not fix or fix == quote or words > 4 or len(fix.split()) > 4:
            return None
        if _BREAKS.sub("", fix) != _BREAKS.sub("", quote):  # letters change: only a word misread in a scan
            if b.source != "ocr" or " " in quote or " " in fix or \
                    Levenshtein.distance(fix.lower(), quote.lower()) > max(2, len(quote) // 3):
                return None  # never the author's own words
            f.kind = "scan"
        elif kind == "scan":
            f.kind = "word"
        if raw is not None:
            f.start, f.end = raw[0] + offset, raw[1] + offset
    elif kind == "furniture":
        letters = len(re.sub(r"\s", "", shown))
        covered = len(re.sub(r"\s", "", shown[s:e]))
        if covered >= 0.85 * letters:
            if len(shown.split()) > 40 or offset != 0:
                return None  # a long paragraph is no header
            f.whole, f.start, f.end = True, 0, len(b.text)
        elif words > 30 or covered > 0.6 * letters:
            return None
        elif raw is not None:
            a, z = raw[0] + offset, raw[1] + offset
            text = own.text
            if z < len(text) and text[z].isspace():  # take one space along, so no double space is left
                z += 1
            elif a > 0 and text[a - 1].isspace():
                a -= 1
            f.start, f.end = a, z
    elif kind == "heading":
        if b.kind not in (BlockKind.PARAGRAPH, BlockKind.LIST_ITEM) or offset != 0 or raw is None \
                or b.text[:raw[0]].strip() or words > 15 or len(b.text[raw[1]:].split()) < 3:
            return None
        f.start, f.end = raw
        f.level = heading_level(quote, levels)
    elif kind == "not_heading":
        if b.kind != BlockKind.HEADING or offset != 0:
            return None
        f.start, f.end = 0, len(b.text)
    f.id = f"{b.id}:{f.kind}:{f.start if f.start >= 0 else s}"
    return f


def heading_level(text: str, levels: Counter) -> int:
    """The level of a heading split off a paragraph: from its number ("2." 1, "2.1" 2), else the document's most
    common heading level."""
    m = re.match(r"(\d+(?:\.\d+)*)\.?\s", text + " ")
    if m:
        return min(3, m.group(1).count(".") + 1)
    return levels.most_common(1)[0][0] if levels else 1


# ------------------------------------------------------------------------------------------ fixing
def view(doc: Document, findings: list[Finding]) -> Document:
    """The document with the chosen structure fixes (headings split off, blocks that are not headings, headers
    hidden). The session's document is not changed, so each fix can be undone."""
    edits = {f.block_id: f for f in findings if f.applied and f.structural}
    if not edits:
        return doc
    blocks, split = [], {}
    for b in doc.blocks:
        f = edits.get(b.id)
        if f is None:
            blocks.append(b)
        elif f.kind == "not_heading":
            blocks.append(replace(b, kind=BlockKind.PARAGRAPH, level=0))
        elif f.kind == "furniture":
            blocks.append(replace(b, kind=BlockKind.FURNITURE))
        elif 0 < f.end < len(b.text):  # a heading run into the paragraph: split it off
            k = f.end
            r = k + len(b.text[k:]) - len(b.text[k:].lstrip())
            split[b.id] = (k, r)
            blocks.append(replace(b, id=b.id + "~h", kind=BlockKind.HEADING, level=f.level, text=b.text[:k].rstrip(),
                                  styles=_clip(b.styles, 0, k), ocr_confidence=_clip(b.ocr_confidence, 0, k)))
            blocks.append(replace(b, kind=BlockKind.PARAGRAPH if b.kind == BlockKind.LIST_ITEM else b.kind,
                                  text=b.text[r:], styles=_clip(b.styles, r, len(b.text)),
                                  ocr_confidence=_clip(b.ocr_confidence, r, len(b.text))))
    corrections = []
    for c in doc.corrections:
        cut = split.get(c.block_id)
        if cut is None:
            corrections.append(c)
        elif c.end <= cut[0]:
            corrections.append(replace(c, block_id=c.block_id + "~h"))
        elif c.start >= cut[1]:
            corrections.append(replace(c, start=c.start - cut[1], end=c.end - cut[1]))
    return replace(doc, blocks=blocks, corrections=corrections)


def _clip(ranges: list, start: int, end: int) -> list:
    """Style (or OCR confidence) ranges inside text[start:end], moved to start at 0."""
    out = []
    for r in ranges:
        a, z = max(r.start, start), min(r.end, end)
        if a < z:
            out.append(replace(r, start=a - start, end=z - start))
    return out
