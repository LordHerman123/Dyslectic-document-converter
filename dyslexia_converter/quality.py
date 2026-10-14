"""How much to trust a conversion: a rating for the whole document and for each page (Excellent, High, Medium,
Low or Very low), the reasons in plain words, and the words the converter is unsure about, so the reader can check
and correct them.

Only what the converter itself knows is used: where the text came from (the PDF's own text, the scanner's stored
text or text recognition), how sure text recognition was of each word, whether the dictionary knows a recognised
word, sentences that seem to be split over two paragraphs, formulas and unusual layouts.

The limits were set on documents whose correct text is known: the benchmark's papers and test documents, scanned
as they are and in two worse ways (lower resolution, blur, noise), 63 scanned copies. On the realistic copies, 6 in
10 of the words marked to check were indeed misread, and 6 in 10 misread words were marked; the levels follow the
real quality closely (rank correlation 0.90, and 0.94 on held-out papers never used to set them).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

from .model import BlockKind, Document

EXCELLENT, HIGH, MEDIUM, LOW, VERY_LOW = 5, 4, 3, 2, 1
LEVEL_NAMES = {EXCELLENT: "Excellent", HIGH: "High", MEDIUM: "Medium", LOW: "Low", VERY_LOW: "Very low"}

UNCLEAR_CONF = 50  # a recognised word below this confidence is probably wrong
UNKNOWN_CONF = 95  # a recognised word the dictionary does not know, below this confidence
# share of uncertain recognised words above which a page or document drops to Medium, Low, Very low
UNSURE_SHARES = (0.05, 0.12, 0.30)
FORMULAS_PER_PAGE = 3  # many formulas: text and formula pictures alternate, sentences break more often
SPLIT_SHARE = 0.15  # share of paragraph breaks that seem to split a sentence
TERMINAL = (".", "!", "?", ":", ";", "”", '"', "’", ")", "]")
TEXT_KINDS = (BlockKind.PARAGRAPH, BlockKind.LIST_ITEM, BlockKind.QUOTE, BlockKind.HEADING, BlockKind.TITLE,
              BlockKind.CAPTION, BlockKind.FOOTNOTE, BlockKind.REFERENCE, BlockKind.AUTHORS)


@dataclass
class Rating:
    """A level (1 Very low .. 5 Excellent) with its reasons: (code, number) pairs such as ("ocr", 0) or
    ("unsure", 4) for 4% uncertain words; the app words them in the reader's language."""
    level: int
    reasons: list[tuple[str, float]] = field(default_factory=list)

    @property
    def name(self) -> str:
        """The level in English ("High")."""
        return LEVEL_NAMES[self.level]


@dataclass
class Quality:
    """The ratings of a conversion and the words to check.

    ``pages``: page of the document (a scanned spread gives two) -> its rating (pages without text have none);
    ``by_source``: page of the original PDF -> the lowest rating of its pages; ``unsure``: block id -> the
    (start, end, reason) ranges of its text to check, reason "unclear" (text recognition was unsure), "unknown"
    (a recognised word the dictionary does not know) or "split" (the sentence may go on in the next paragraph).
    """
    document: Rating
    pages: dict[int, Rating] = field(default_factory=dict)
    unsure: dict[str, list[tuple[int, int, str]]] = field(default_factory=dict)
    by_source: dict[int, Rating] = field(default_factory=dict)

    def page_rating(self, source_pages: list[int]) -> Optional[Rating]:
        """The rating of a converted page showing these pages of the original PDF: the lowest of theirs."""
        found = [self.by_source[p] for p in source_pages if p in self.by_source]
        return min(found, key=lambda r: r.level) if found else None


def _words(text: str) -> list[tuple[int, int]]:
    """(start, end) of the words of a text."""
    out, start = [], None
    for i, ch in enumerate(text + " "):
        if ch.isspace():
            if start is not None:
                out.append((start, i))
                start = None
        elif start is None:
            start = i
    return out


def _fixed(doc: Document, block_id: str) -> list[tuple[int, int]]:
    """Ranges of a block's text the reader corrected (or chose a fix for): no longer uncertain."""
    return [(c.start, c.end) for c in doc.corrections_for(block_id) if c.applied and c.source in ("user", "check")]


def _level(ocr_words: int, unsure: int, ocr: bool, formulas: float, split: float, unusual: bool) -> Rating:
    """The level for the signals of a page or a document."""
    reasons: list[tuple[str, float]] = []
    level = EXCELLENT
    if ocr:
        level = HIGH
        reasons.append(("ocr", 0))
        share = unsure / ocr_words if ocr_words else 0.0
        drops = sum(share > s for s in UNSURE_SHARES)
        if drops:
            level -= drops
        if unsure:
            reasons.append(("unsure", round(100 * share)))
    if formulas >= FORMULAS_PER_PAGE:
        level -= 1
        reasons.append(("formulas", round(formulas)))
    if split >= SPLIT_SHARE:
        level -= 1
        reasons.append(("split", round(100 * split)))
    if unusual:
        level -= 1
        reasons.append(("layout", 0))
    return Rating(max(VERY_LOW, level), reasons)


def assess(doc: Document, known_word: Callable[[str], bool]) -> Quality:
    """Rate a conversion and find the words to check (see :class:`Quality`)."""
    unsure: dict[str, list[tuple[int, int, str]]] = {}
    per_page: dict[int, dict] = {}

    def page_stats(p: int) -> dict:
        return per_page.setdefault(p, {"words": 0, "ocr_words": 0, "unsure": 0, "formulas": 0, "breaks": 0,
                                       "split": 0, "unreadable": 0})

    # words recognised by OCR that may be wrong
    for b in doc.blocks:
        if b.kind not in TEXT_KINDS:
            if b.kind == BlockKind.IMAGE and b.image is not None:
                if b.image.kind == "equation":
                    page_stats(b.page)["formulas"] += 1
                elif b.image.kind == "unreadable-text":
                    page_stats(b.page)["unreadable"] += 1
            continue
        st = page_stats(b.page)
        st["words"] += len(_words(b.text))
        if not b.ocr_confidence:
            continue
        fixed = _fixed(doc, b.id)
        for c in b.ocr_confidence:
            if c.confidence < 0:
                continue
            st["ocr_words"] += 1
            word = b.text[c.start:c.end].strip(".,;:!?()[]\"'“”‘’")
            if c.confidence < UNCLEAR_CONF:
                reason = "unclear"
            elif (c.confidence < UNKNOWN_CONF and len(word) >= 3 and word.isalpha()
                  and not known_word(word)):
                reason = "unknown"
            else:
                continue
            if any(a < c.end and c.start < e for a, e in fixed):
                continue
            unsure.setdefault(b.id, []).append((c.start, c.end, reason))
            st["unsure"] += 1

    # sentences that seem to be split over two paragraphs
    paras = [b for b in doc.blocks if b.kind == BlockKind.PARAGRAPH and b.text.strip()]
    for a, b in zip(paras, paras[1:]):
        page_stats(a.page)["breaks"] += 1
        if a.text.rstrip().endswith(TERMINAL) or not b.text.lstrip()[:1].islower():
            continue
        page_stats(a.page)["split"] += 1
        wa, wb = _words(a.text), _words(b.text)
        if wa and not any(x < wa[-1][1] and wa[-1][0] < y for x, y in _fixed(doc, a.id)):
            unsure.setdefault(a.id, []).append((wa[-1][0], wa[-1][1], "split"))
        if wb and not any(x < wb[0][1] and wb[0][0] < y for x, y in _fixed(doc, b.id)):
            unsure.setdefault(b.id, []).append((wb[0][0], wb[0][1], "split"))

    pages: dict[int, Rating] = {}
    info = {i: p for i, p in enumerate(doc.pages)}
    for p, st in per_page.items():
        pi = info.get(p)
        if st["words"] == 0:
            if st["unreadable"]:
                pages[p] = Rating(VERY_LOW, [("pictured", 0)])
            continue
        ocr = bool(pi and (pi.ocr_used or pi.text_source in ("ocr", "scanner")))
        pages[p] = _level(st["ocr_words"], st["unsure"], ocr, st["formulas"],
                          st["split"] / st["breaks"] if st["breaks"] else 0.0, bool(pi and pi.unusual_layout))

    # the document: the same signals over all its pages
    n = max(1, sum(1 for st in per_page.values() if st["words"]))
    total = {k: sum(st[k] for st in per_page.values()) for k in ("ocr_words", "unsure", "formulas", "breaks", "split")}
    ocr_pages = sum(1 for p in doc.pages if p.ocr_used or p.text_source in ("ocr", "scanner"))
    document = _level(total["ocr_words"], total["unsure"], ocr_pages * 2 >= max(1, len(doc.pages)),
                      total["formulas"] / n, total["split"] / total["breaks"] if total["breaks"] else 0.0,
                      sum(p.unusual_layout for p in doc.pages) * 2 > max(1, len(doc.pages)))
    unreadable = sum(1 for r in pages.values() if r.reasons and r.reasons[0][0] == "pictured")
    if unreadable and unreadable * 4 >= max(1, len(pages)):
        document = Rating(min(document.level, LOW), document.reasons + [("pictured", unreadable)])
    weak = sum(1 for r in pages.values() if r.level <= LOW)
    if weak and weak * 10 >= len(pages) and document.level > MEDIUM:  # a few poor pages among good ones
        document = Rating(MEDIUM, document.reasons + [("weak_pages", weak)])
    for spans in unsure.values():
        spans.sort()
    by_source: dict[int, Rating] = {}
    for p, r in pages.items():
        src = info[p].source_page if p in info and info[p].source_page >= 0 else p
        if src not in by_source or r.level < by_source[src].level:
            by_source[src] = r
    return Quality(document, pages, unsure, by_source)


def parts_on_pages(words: list, marks: list) -> dict[int, list[tuple[int, int, str]]]:
    """The words to check as places in the converted document's words, page by page: (first word, last word,
    reason) of each part, in reading order. ``words``: (page, text, boxes) of every word of the converted PDF, as
    focus mode reads them; ``marks``: where the PDF writer drew the words to check, (page, x0, y0, x1, y1, reason)."""
    by_page: dict[int, list] = {}
    for m in marks:
        by_page.setdefault(m[0], []).append(m)
    reason: dict[int, str] = {}
    for n, (page, _text, boxes) in enumerate(words):
        on_page = by_page.get(page)
        if not on_page:
            continue
        for x0, y0, x1, y1 in boxes:
            h = max(0.1, y1 - y0)
            hit = next((why for _, a, b, c, d, why in on_page
                        if min(x1, c) - max(x0, a) > 1.0 and min(y1, d) - max(y0, b) > 0.3 * h), None)
            if hit:
                reason[n] = hit
                break
    parts: dict[int, list[tuple[int, int, str]]] = {}
    for n in sorted(reason):
        page_parts = parts.setdefault(words[n][0], [])
        if page_parts and page_parts[-1][1] == n - 1 and page_parts[-1][2] == reason[n]:
            page_parts[-1] = (page_parts[-1][0], n, reason[n])
        else:
            page_parts.append((n, n, reason[n]))
    return parts
