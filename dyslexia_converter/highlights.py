"""Coloured highlights (with notes) the reader adds in focus mode, kept per document on this device.

A highlight is a run of words in reading order (word numbers counted through the whole converted
document), with a colour. Storing word numbers instead of page positions keeps highlights on the same
words when the layout changes (a bigger font moves words to other pages). The highlighted words are kept
too, so a highlight finds its words again when the text itself shifts a little (a citation turned into
a number, for example); a highlight whose words cannot be found any more is simply not shown.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Optional

from .settings import app_data_dir
from .speech import Sentence

Rect = tuple[float, float, float, float]

COLOURS = {  # name -> RGBA of the marker (see-through, so the text stays readable)
    "yellow": (255, 214, 0, 110),
    "green": (80, 200, 120, 105),
    "blue": (80, 160, 255, 100),
    "pink": (255, 120, 180, 105),
}
SEARCH_WINDOW = 400  # words around the stored position searched when the text has shifted


@dataclass
class Highlight:
    """One highlight: a run of words in reading order with a marker colour and, optionally, a note."""
    start: int  # first word number
    end: int  # last word number (inclusive)
    colour: str
    words: str = ""  # the words highlighted, to find them again after changes
    note: str = ""  # the reader's own comment on these words


@dataclass
class PageWord:
    """A word on one page: its number in the whole document, its text and where it is (PDF points)."""
    number: int  # word number in the whole document
    text: str
    rects: list[Rect]


def document_words(sentences: list[Sentence]) -> list[tuple[int, str, list[Rect]]]:
    """Every word of the converted document in reading order: (page, text, rectangles)."""
    return [(w.page, w.text, w.rects) for s in sentences for w in s.words]


def words_on_page(words: list[tuple[int, str, list[Rect]]], page: int) -> list[PageWord]:
    """The words of one page, with their numbers in the whole document (for finding the word tapped)."""
    return [PageWord(i, text, rects) for i, (p, text, rects) in enumerate(words) if p == page]


def word_at(page_words: list[PageWord], x: float, y: float) -> Optional[int]:
    """Number of the word nearest to a point on the page."""
    best, best_d = None, None
    for w in page_words:
        for x0, y0, x1, y1 in w.rects:
            dx = max(x0 - x, 0.0, x - x1)
            dy = max(y0 - y, 0.0, y - y1)
            d = dx * dx + (dy * 3) ** 2
            if best_d is None or d < best_d:
                best, best_d = w.number, d
    return best


def _text(words: list[tuple[int, str, list[Rect]]], a: int, b: int) -> str:
    """Words a..b (inclusive) joined with spaces: what a highlight stores to find its words again."""
    return " ".join(t for _, t, _ in words[a:b + 1])


def resolve(h: Highlight, words: list[tuple[int, str, list[Rect]]]) -> Optional[tuple[int, int]]:
    """Where a highlight's words are now: its stored place, or the nearest place with the same words."""
    n = h.end - h.start
    if 0 <= h.start and h.end < len(words) and (not h.words or _text(words, h.start, h.end) == h.words):
        return h.start, h.end
    if not h.words:
        return None
    lo = max(0, h.start - SEARCH_WINDOW)
    hi = min(len(words) - n - 1, h.start + SEARCH_WINDOW)
    for delta in range(0, SEARCH_WINDOW + 1):  # nearest first
        for a in (h.start - delta, h.start + delta):
            if lo <= a <= hi and _text(words, a, a + n) == h.words:
                return a, a + n
    return None


def bands(rects: Iterable[Rect], gap: float = 12.0) -> list[Rect]:
    """Join the rectangles of neighbouring words on the same line into one band, like a marker stroke."""
    out: list[list[float]] = []
    for x0, y0, x1, y1 in sorted(rects, key=lambda r: (round((r[1] + r[3]) / 2), r[0])):
        if out:
            b = out[-1]
            same_line = abs((b[1] + b[3]) / 2 - (y0 + y1) / 2) < (y1 - y0) * 0.5
            if same_line and x0 - b[2] <= gap:
                b[0], b[1], b[2], b[3] = min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)
                continue
        out.append([x0, y0, x1, y1])
    return [tuple(b) for b in out]


def page_marks(highlights: list[Highlight], words: list[tuple[int, str, list[Rect]]],
               page: int) -> list[tuple[Rect, tuple[int, int, int, int]]]:
    """The coloured bands to draw on a page: (rectangle, colour)."""
    out = []
    for h in highlights:
        where = resolve(h, words)
        if where is None:
            continue
        a, b = where
        rects = [r for p, _, rs in words[a:b + 1] if p == page for r in rs]
        colour = COLOURS.get(h.colour, COLOURS["yellow"])
        out += [(r, colour) for r in bands(rects)]
    return out


def add(highlights: list[Highlight], a: int, b: int, colour: str,
        words: list[tuple[int, str, list[Rect]]], note: str = "") -> list[Highlight]:
    """Mark words a..b with a colour (replacing other colours there); a note on a highlight that is
    covered completely carries over."""
    a, b = min(a, b), max(a, b)
    if not note:
        for h in highlights:
            where = resolve(h, words)
            if h.note and where and a <= where[0] and where[1] <= b:
                note = h.note
                break
    out = erase(highlights, a, b, words)
    out.append(Highlight(a, b, colour, _text(words, a, b), note))
    return sorted(out, key=lambda h: h.start)


def erase(highlights: list[Highlight], a: int, b: int,
          words: list[tuple[int, str, list[Rect]]]) -> list[Highlight]:
    """Remove highlighting from words a..b (a highlight partly covered keeps its other words)."""
    a, b = min(a, b), max(a, b)
    out = []
    for h in highlights:
        where = resolve(h, words)
        if where is None:
            out.append(h)  # not placed now: keep it, it may be found again later
            continue
        s, e = where
        if e < a or s > b:
            out.append(Highlight(s, e, h.colour, h.words, h.note))
            continue
        note = h.note  # a note stays with the first part that is left
        if s < a:
            out.append(Highlight(s, a - 1, h.colour, _text(words, s, a - 1), note))
            note = ""
        if e > b:
            out.append(Highlight(b + 1, e, h.colour, _text(words, b + 1, e), note))
    return out


def at(highlights: list[Highlight], n: int, words: list[tuple[int, str, list[Rect]]]) -> Optional[int]:
    """Which highlight (its index in the list) covers word ``n``."""
    for k, h in enumerate(highlights):
        where = resolve(h, words)
        if where and where[0] <= n <= where[1]:
            return k
    return None


def set_note(highlights: list[Highlight], k: int, note: str) -> list[Highlight]:
    """A copy of the highlights with the note of highlight ``k`` replaced (an empty note removes it)."""
    out = list(highlights)
    h = out[k]
    out[k] = Highlight(h.start, h.end, h.colour, h.words, note.strip())
    return out


def recolour(highlights: list[Highlight], k: int, colour: str) -> list[Highlight]:
    """A copy of the highlights with highlight ``k`` in another marker colour (its note stays)."""
    out = list(highlights)
    h = out[k]
    out[k] = Highlight(h.start, h.end, colour, h.words, h.note)
    return out


def note_marks(highlights: list[Highlight], words: list[tuple[int, str, list[Rect]]],
               page: int) -> list[tuple[float, float]]:
    """Where to show the note sign of each highlight with a note: the top right of its first band."""
    out = []
    for h in highlights:
        where = resolve(h, words) if h.note else None
        if where is None:
            continue
        first = next((p for p, _, rs in words[where[0]:where[1] + 1] if rs), None)
        rects = [r for p, _, rs in words[where[0]:where[1] + 1] if p == first for r in rs]
        if first == page and rects:
            band = bands(rects)[0]
            out.append((band[2], band[1]))
    return out


def lines_on_page(words: list[tuple[int, str, list[Rect]]], page: int) -> list[tuple[float, float]]:
    """The lines of text on a page, top to bottom, as (top, bottom) in points (for the reading ruler)."""
    lines: list[list[float]] = []
    for r in sorted((r for p, _, rs in words if p == page for r in rs), key=lambda r: (r[1] + r[3]) / 2):
        mid = (r[1] + r[3]) / 2
        if lines and abs((lines[-1][0] + lines[-1][1]) / 2 - mid) < (r[3] - r[1]) * 0.5:
            lines[-1][0], lines[-1][1] = min(lines[-1][0], r[1]), max(lines[-1][1], r[3])
        else:
            lines.append([r[1], r[3]])
    return [tuple(x) for x in lines]


def apply_to_pdf(pdf: bytes, highlights: list[Highlight], skip_pages: frozenset = frozenset()) -> bytes:
    """The PDF with the highlights added as highlight annotations: every PDF reader shows them in colour,
    and they can be removed or changed there. ``skip_pages`` must be the pages left out when the
    highlights were made (the contents pages), so the words are counted the same way."""
    import pymupdf

    from .speech import reading_units

    words = document_words(reading_units(pdf, skip_pages=skip_pages))
    doc = pymupdf.open(stream=bytes(pdf), filetype="pdf")
    try:
        pages = [doc[p] for p in range(doc.page_count)]  # kept while their annotations are made
        for h in highlights:
            where = resolve(h, words)
            if where is None:
                continue
            r, g, b, a = COLOURS.get(h.colour, COLOURS["yellow"])
            # the see-through marker colour as it looks over white paper (highlights multiply)
            colour = tuple(1 - a / 255 * (1 - c / 255) for c in (r, g, b))
            note = h.note
            for pno in sorted({p for p, _, rs in words[where[0]:where[1] + 1] if rs}):
                rects = [rr for p, _, rs in words[where[0]:where[1] + 1] if p == pno for rr in rs]
                for band in bands(rects):
                    annot = pages[pno].add_highlight_annot(pymupdf.Rect(band))
                    annot.set_colors(stroke=colour)
                    if note:  # the note becomes the highlight's comment, shown by PDF readers
                        annot.set_info(content=note, title="Note")
                        note = ""
                    annot.update()
        return doc.tobytes(garbage=0, deflate=True)
    finally:
        doc.close()


# ------------------------------------------------------------------------------------------ storage

def document_key(path: str | Path) -> str:
    """The same PDF gets the same key, wherever it is stored."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:32]


class HighlightStore:
    """The highlights of every document, in one JSON file in the app's data folder.

    Keyed by :func:`document_key`, so the same PDF finds its highlights wherever it is stored. A damaged
    or unreadable file is treated as empty; failing to write is ignored (highlights are a convenience).
    """
    def __init__(self, path: Optional[Path] = None):
        """``path``: where to keep the file (tests use a temporary one); by default in the app's data folder."""
        self.path = path or (app_data_dir() / "highlights.json")

    def _read(self) -> dict:
        """Everything stored, or an empty dict when the file is missing or damaged."""
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def load(self, key: str) -> list[Highlight]:
        """The highlights of one document; entries that cannot be read are skipped."""
        out = []
        for d in self._read().get(key, []):
            try:
                out.append(Highlight(int(d["start"]), int(d["end"]), str(d["colour"]), str(d.get("words", "")),
                                     str(d.get("note", ""))))
            except (KeyError, TypeError, ValueError):
                continue
        return out

    def save(self, key: str, highlights: list[Highlight]) -> None:
        """Store the highlights of one document (an empty list removes the document from the file)."""
        data = self._read()
        if highlights:
            data[key] = [asdict(h) for h in highlights]
        else:
            data.pop(key, None)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
