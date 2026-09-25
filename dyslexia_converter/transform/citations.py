"""Deterministic citation detection.

Recognises author-date citations such as ``(Smith, 2020; Jones & Brown, 2021)``,
numbered citations such as ``[3]``, ``[2, 5, 8]`` and ``[3-7]``, and
superscript numeric citations. Anything that only *looks* like a citation is
reported with a lower confidence so it can be left alone or, if the user has
enabled AI assistance, double-checked by the AI.

Automated citation detection can make mistakes; the original citation text is
always preserved.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

NAME = r"(?:(?i:van|von|de|der|den|du|da|di|la|le|ten|ter|d')\s+)*[A-ZÀ-Þ][\wÀ-ɏ'’\-]+"
AUTHORS = (rf"{NAME}(?:\s*(?:,\s*(?!\d)|\s+(?:and|&|en)\s+|,\s*(?:and|&)\s+){NAME})*"
           r"(?:,?\s+et\s+al\.?)?")
YEAR = r"(?:(?:1[5-9]|20)\d{2}[a-z]?|n\.\s?d\.|in press|forthcoming)"
YEARS = rf"{YEAR}(?:\s*,\s*{YEAR})*"
LOCATOR = r"(?:\s*[,:]\s*(?:pp?\.\s*|p\s|chap\.\s*|ch\.\s*)?\d+(?:\s*[-–]\s*\d+)?)?"
PREFIX = r"(?:(?:see(?:\s+also)?|e\.\s?g\.|cf\.|i\.\s?e\.|also|for example|for a review,?\s*see|zie(?:\s+ook)?|bijv\.)\s*,?\s*)?"
ITEM = rf"{PREFIX}{AUTHORS},?\s+{YEARS}{LOCATOR}"
AUTHOR_DATE_RE = re.compile(rf"\(\s*({ITEM}(?:\s*;\s*{ITEM})*)\s*\)")
ITEM_RE = re.compile(ITEM)
LOOSE_PAREN_RE = re.compile(r"\(([^()]{3,200}?\b(?:1[5-9]|20)\d{2}[a-z]?\b[^()]{0,60})\)")
NUMERIC_RE = re.compile(r"\[(\d{1,4}(?:\s*[-–]\s*\d{1,4})?(?:\s*[,;]\s*\d{1,4}(?:\s*[-–]\s*\d{1,4})?)*)\]")


@dataclass
class Citation:
    start: int
    end: int
    text: str
    kind: str  # author_date / numeric / superscript
    items: list[str] = field(default_factory=list)
    confidence: float = 0.0

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.text}"


def _expand_numbers(spec: str) -> list[int]:
    nums: list[int] = []
    for part in re.split(r"\s*[,;]\s*", spec):
        m = re.match(r"(\d+)\s*[-–]\s*(\d+)", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2))
            if 0 < b - a < 50:
                nums += list(range(a, b + 1))
            else:
                nums += [a, b]
        elif part.strip().isdigit():
            nums.append(int(part))
    return nums


def find_citations(text: str, n_references: int = 0, superscripts: list[tuple[int, int]] = ()) -> list[Citation]:
    out: list[Citation] = []
    taken: list[tuple[int, int]] = []

    def free(s: int, e: int) -> bool:
        return all(e <= a or s >= b for a, b in taken)

    for m in AUTHOR_DATE_RE.finditer(text):
        items = [i.strip() for i in re.split(r"\s*;\s*", m.group(1))]
        if all(ITEM_RE.fullmatch(i) for i in items):
            out.append(Citation(m.start(), m.end(), m.group(), "author_date", items, 0.97))
            taken.append((m.start(), m.end()))

    for m in LOOSE_PAREN_RE.finditer(text):
        if not free(m.start(), m.end()):
            continue
        inner = m.group(1)
        if re.search(r"[A-Z][a-z]+", inner) and not re.search(r"[=<>%]", inner):
            items = [i.strip() for i in re.split(r"\s*;\s*", inner)]
            out.append(Citation(m.start(), m.end(), m.group(), "author_date", items, 0.55))
            taken.append((m.start(), m.end()))

    for m in NUMERIC_RE.finditer(text):
        if not free(m.start(), m.end()):
            continue
        nums = _expand_numbers(m.group(1))
        if not nums:
            continue
        conf = 0.7
        if min(nums) < 1:
            conf = 0.3
        elif n_references and max(nums) <= n_references:
            conf = 0.97
        elif n_references and max(nums) > n_references:
            conf = 0.4  # probably an interval or something else
        out.append(Citation(m.start(), m.end(), m.group(), "numeric", [str(n) for n in nums], conf))
        taken.append((m.start(), m.end()))

    for s, e in superscripts:
        seg = text[s:e].strip()
        if re.fullmatch(r"\d{1,4}(?:\s*[-–,]\s*\d{1,4})*", seg) and free(s, e):
            nums = _expand_numbers(seg)
            conf = 0.9 if n_references and nums and max(nums) <= n_references else 0.6
            out.append(Citation(s, e, text[s:e], "superscript", [str(n) for n in nums], conf))
    out.sort(key=lambda c: c.start)
    return out


def match_reference(item: str, references: list[str]) -> int:
    """Index of the reference entry matching an author-date item, or -1."""
    m = re.search(rf"({NAME})", re.sub(PREFIX, "", item, count=1))
    year = re.search(YEAR, item)
    if not m or not year:
        return -1
    surname = m.group(1).split()[-1]
    yr = year.group()
    candidates = [i for i, r in enumerate(references)
                  if re.search(rf"\b{re.escape(surname)}\b", r[:120]) and yr in r]
    if len(candidates) == 1:
        return candidates[0]
    # prefer the entry that starts with the surname
    starts = [i for i in candidates if re.match(rf"\W*(?:\[\d+\]\s*|\d+\.\s*)?{re.escape(surname)}\b", references[i])]
    return starts[0] if len(starts) == 1 else -1
