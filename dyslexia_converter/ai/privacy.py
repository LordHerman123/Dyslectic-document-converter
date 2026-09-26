"""Send as little of the document as possible.

Each uncertain item goes out with only a few words around it, and details the question never needs
(e-mail addresses, web links, long numbers such as phone or account numbers) are masked first.
"""
from __future__ import annotations

import re

MARK_OPEN, MARK_CLOSE = "[[", "]]"  # the item the question is about (plain characters every font can show)

_MASKS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"(?:https?://|www\.)\S*[^\s.,;:)\]]", re.I), "[link]"),
    (re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]){10,30}\b"), "[account]"),  # IBAN-like
    (re.compile(r"(?<![\w.])\+?\d[\d ./-]{6,}\d(?![\w.])"), "[number]"),  # phone numbers, IDs (not years)
]


_YEARS = re.compile(r"\d{4}\s*[-/]\s*\d{2,4}")  # 1914-1918, 2019/20: years, which citations need


def mask(text: str) -> str:
    """Replace personal details the AI never needs by a placeholder."""
    for pattern, placeholder in _MASKS:
        text = pattern.sub(lambda m: m.group() if _YEARS.fullmatch(m.group()) else placeholder, text)
    return text


def window(text: str, start: int, end: int, before: int = 8, after: int = 6) -> str:
    """The item text[start:end], marked, with at most `before` words before it and `after` words after it."""
    head = text[:start].split()
    tail = text[end:].split()
    left = " ".join(head[-before:]) if before else ""
    right = " ".join(tail[:after]) if after else ""
    if len(head) > before:
        left = "…" + left
    if len(tail) > after:
        right = right + "…"
    item = f"{MARK_OPEN}{text[start:end]}{MARK_CLOSE}"
    return mask(" ".join(p for p in (left, item, right) if p))
