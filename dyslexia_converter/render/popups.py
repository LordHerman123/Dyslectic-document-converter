"""What the citations and note markers in the converted document point to, so a tap on one can show it.

Built while the document is laid out (see :func:`dyslexia_converter.render.compose.compose`): the reference
list by number, the notes by their marker ("[Note 2]"), and author-date citations left in the text
("(Smith, 2019)") with the references they match. :meth:`Popups.at` finds the marker around a place in some
text and returns what it points to.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

REF_NUMBER = re.compile(r"^\s*\[?(\d{1,4})[\].)]\s*")  # "[12] Smith ..." / "12. Smith ..."
BRACKETS = re.compile(r"\[(\d{1,4}(?:\s*[-–,]\s*\d{1,4})*)\]")  # [3] [3, 5] [3-5]


@dataclass
class Popup:
    """What a tapped marker points to: a reference or a note, the marker as shown, and its entries (a
    citation can name several references)."""
    kind: str  # "reference" or "note"
    label: str  # the marker as shown ("[3]", "[Note 2]", "(Smith, 2019)")
    entries: list[str]


@dataclass
class Popups:
    """The references and notes of a laid-out document, by the markers that point to them."""
    references: dict[int, str] = field(default_factory=dict)  # number -> reference text
    notes: dict[str, str] = field(default_factory=dict)  # marker ("[Note 2]") -> note text
    citations: dict[str, list[str]] = field(default_factory=dict)  # "(Smith, 2019)" -> reference texts

    def __bool__(self) -> bool:
        return bool(self.references or self.notes or self.citations)

    def add_reference(self, number: int, text: str) -> None:
        """A reference by its number (the number at its start, if it has one, is left out)."""
        self.references.setdefault(number, REF_NUMBER.sub("", text, count=1).strip())

    def at(self, text: str, pos: int) -> Optional[Popup]:
        """The marker in ``text`` that covers position ``pos`` (or starts or ends there), and what it points to;
        None when there is none, or it points to nothing known."""
        def covers(s: int, e: int) -> bool:
            return s <= pos <= e

        for marker, note in self.notes.items():
            for m in re.finditer(re.escape(marker), text):
                if covers(m.start(), m.end()):
                    return Popup("note", marker, [note])
        for cite, refs in self.citations.items():  # a citation left in the text (it may break over lines)
            pattern = r"\s+".join(re.escape(w) for w in cite.split())
            for m in re.finditer(pattern, text):
                if covers(m.start(), m.end()) and refs:
                    return Popup("reference", cite, refs)
        for m in BRACKETS.finditer(text):
            if not covers(m.start(), m.end()):
                continue
            numbers: list[int] = []
            for part in re.split(r"\s*,\s*", m.group(1)):
                r = re.fullmatch(r"(\d+)\s*[-\u2013]\s*(\d+)", part)
                if r:
                    lo, hi = int(r.group(1)), int(r.group(2))
                    numbers += list(range(lo, hi + 1)) if 0 < hi - lo < 30 else [lo, hi]
                else:
                    numbers.append(int(part))
            entries = [f"[{n}] {self.references[n]}" for n in numbers if n in self.references]
            if entries:
                return Popup("reference", m.group(0), entries)
        return None
