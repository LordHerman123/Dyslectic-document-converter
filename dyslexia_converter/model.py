"""Core data model.

The extracted text stored on each :class:`Block` is treated as immutable.
Everything that changes what the reader *sees* (OCR corrections, citation
relocation, footnote relocation, bionic bolding) is stored separately and
applied at render time, so every transformation can be reversed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BlockKind(str, Enum):
    TITLE = "title"
    AUTHORS = "authors"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST_ITEM = "list_item"
    QUOTE = "quote"
    CAPTION = "caption"
    FOOTNOTE = "footnote"
    REFERENCE = "reference"
    TABLE = "table"
    IMAGE = "image"
    FURNITURE = "furniture"  # running headers/footers, page numbers


Rect = tuple[float, float, float, float]  # x0, y0, x1, y1 in PDF points


@dataclass
class StyleRange:
    """Inline style over ``text[start:end]`` of a block."""

    start: int
    end: int
    bold: bool = False
    italic: bool = False
    superscript: bool = False


@dataclass
class ImageData:
    data: bytes
    ext: str  # "png" or "jpeg"
    width: int  # pixels
    height: int
    kind: str = "figure"  # figure / page-region / decorative


@dataclass
class TableData:
    rows: list[list[str]]
    # Rendered picture of the table region. Used when the table cannot be
    # reconstructed reliably, so contents are never corrupted.
    fallback_image: Optional[ImageData] = None
    reliable: bool = True


@dataclass
class OcrWordConfidence:
    start: int
    end: int
    confidence: float  # 0..100 as reported by the OCR engine


@dataclass
class Block:
    id: str
    kind: BlockKind
    text: str = ""
    page: int = 0
    bbox: Rect = (0, 0, 0, 0)
    level: int = 0  # heading level (1 = top) or list depth
    styles: list[StyleRange] = field(default_factory=list)
    image: Optional[ImageData] = None
    table: Optional[TableData] = None
    caption_for: Optional[str] = None  # id of the image/table this caption describes
    footnote_label: Optional[str] = None  # "1", "*", ... for footnote blocks
    source: str = "text"  # "text" or "ocr"
    ocr_confidence: list[OcrWordConfidence] = field(default_factory=list)
    font_size: float = 0.0


@dataclass
class Correction:
    """A proposed replacement of ``block.text[start:end]``.

    The original text is never overwritten; corrections are applied at
    render time when their status is ``accepted`` or ``auto``.
    """

    id: str
    block_id: str
    start: int
    end: int
    original: str
    replacement: str
    confidence: float  # 0..1
    status: str = "pending"  # pending / auto / accepted / rejected
    source: str = "dictionary"  # dictionary / ai / user (typed in by the user)

    @property
    def applied(self) -> bool:
        return self.status in ("auto", "accepted")

    def overlaps(self, other: "Correction") -> bool:
        return self.block_id == other.block_id and self.start < other.end and other.start < self.end


def effective_corrections(corrections: list[Correction]) -> list[Correction]:
    """The corrections to apply: a correction the user typed in replaces any suggestion on the same text."""
    applied = [c for c in corrections if c.applied]
    user = [c for c in applied if c.source == "user"]
    return [c for c in applied if c.source == "user" or not any(c.overlaps(u) for u in user)]


@dataclass
class PageInfo:
    number: int
    width: float
    height: float
    kind: str  # "text", "scanned" or "mixed"
    ocr_used: bool = False
    source_page: int = -1  # page index in the original PDF (a spread gives two pages)
    side: str = "full"  # "full", or "left"/"right" half of a two-page spread
    skew: float = 0.0  # degrees straightened
    text_source: str = ""  # "pdf", "ocr" or "scanner" (text layer stored in the PDF by a scanner)


@dataclass
class Document:
    source_path: str
    pages: list[PageInfo] = field(default_factory=list)
    blocks: list[Block] = field(default_factory=list)
    corrections: list[Correction] = field(default_factory=list)
    title: str = ""
    author: str = ""
    language: str = "en"
    toc: list[tuple[int, str, int]] = field(default_factory=list)  # (level, title, page)
    warnings: list[str] = field(default_factory=list)

    @property
    def ocr_used(self) -> bool:
        return any(p.ocr_used for p in self.pages)

    @property
    def pdf_type(self) -> str:
        kinds = {p.kind for p in self.pages}
        if kinds == {"text"}:
            return "text"
        if kinds <= {"scanned"}:
            return "scanned"
        return "mixed"

    def block(self, block_id: str) -> Optional[Block]:
        for b in self.blocks:
            if b.id == block_id:
                return b
        return None

    def display_text(self, block: Block) -> str:
        """Block text with applied corrections (the original is untouched)."""
        return apply_corrections(block.text, self.corrections_for(block.id))

    def corrections_for(self, block_id: str) -> list[Correction]:
        return [c for c in self.corrections if c.block_id == block_id]


def apply_corrections(text: str, corrections: list[Correction]) -> str:
    out = text
    for c in sorted(effective_corrections(corrections), key=lambda c: c.start, reverse=True):
        if out[c.start:c.end] == c.original:
            out = out[: c.start] + c.replacement + out[c.end:]
    return out


def map_styles(styles: list[StyleRange], text: str, corrections: list[Correction]) -> list[StyleRange]:
    """Shift style ranges so they stay aligned after corrections are applied."""
    applied = sorted((c for c in effective_corrections(corrections) if text[c.start:c.end] == c.original),
                     key=lambda c: c.start)
    if not applied:
        return styles

    def shift(pos: int) -> int:
        delta = 0
        for c in applied:
            if c.end <= pos:
                delta += len(c.replacement) - (c.end - c.start)
            elif c.start < pos:
                return c.start + delta + min(pos - c.start, len(c.replacement))
        return pos + delta

    return [StyleRange(shift(s.start), shift(s.end), s.bold, s.italic, s.superscript) for s in styles]
