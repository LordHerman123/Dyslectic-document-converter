"""First-part-of-word bolding ("bionic" style).

Only presentation changes: the text itself is never modified. Punctuation,
URLs, e-mail addresses, numbers and technical identifiers are left alone.
"""
from __future__ import annotations

import math
import re

WORD_RE = re.compile(r"[^\W\d_]+(?:['’][^\W\d_]+)*", re.UNICODE)
SKIP_TOKEN_RE = re.compile(
    r"((?i:https?://|www\.|doi:)|\S+@\S+\.\w+|\S*[_/\\]\S*|\S*\d\S*|\b[a-z]+[A-Z]\w*|\b\w+\.\w+\.\w+)")


def bold_length(word_len: int, amount: str) -> int:
    if word_len <= 0:
        return 0
    if amount == "first_letter":
        return 1
    if amount in ("25", "40"):
        return max(1, math.ceil(word_len * int(amount) / 100))
    # automatic: short words get one letter, longer words about 40%
    if word_len <= 3:
        return 1
    if word_len <= 5:
        return 2
    return math.ceil(word_len * 0.4)


def bold_ranges(text: str, amount: str = "auto") -> list[tuple[int, int]]:
    """Return ``(start, end)`` character ranges to show in bold."""
    protected: list[tuple[int, int]] = []
    for tok in re.finditer(r"\S+", text):
        if SKIP_TOKEN_RE.search(tok.group()):
            protected.append((tok.start(), tok.end()))
    ranges = []
    for m in WORD_RE.finditer(text):
        if any(a <= m.start() < b for a, b in protected):
            continue
        word = m.group()
        if word.isupper() and len(word) > 1:  # acronyms
            continue
        n = bold_length(len(word), amount)
        ranges.append((m.start(), m.start() + n))
    return ranges
