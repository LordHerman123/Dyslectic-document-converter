"""Tagged PDF: the structure screen readers and read-aloud tools follow.

While the PDF is drawn, every piece of content is wrapped in marked content with an id (``/P <</MCID 3>>
BDC ... EMC``); page furniture (the page tint, page numbers) is marked as an artifact, so it is not read out.
After ReportLab has written the file, the structure tree is added: a Document element with the headings
(H1-H6), paragraphs, figures and formulas (with their text as /Alt), tables, captions and notes, in reading
order, plus the document language and the "this PDF is tagged" flag. Inline formulas carry their text as
/ActualText, so they are read out instead of skipped.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import pymupdf


@dataclass
class _Elem:
    kind: str  # structure type: H1..H6, P, Figure, Formula, Table, Caption, Note, BlockQuote, TOC
    alt: str = ""
    kids: list[tuple[int, int]] = field(default_factory=list)  # (page index, MCID)


class Tagger:
    """Collects the structure elements and the marked content drawn for each of them."""

    def __init__(self):
        self.elems: list[_Elem] = []
        self._next: dict[int, int] = {}

    def new(self, kind: str, alt: str = "") -> int:
        self.elems.append(_Elem(kind, alt))
        return len(self.elems) - 1

    def reset(self) -> None:
        """A new build pass: nothing has been drawn yet."""
        self._next = {}
        for e in self.elems:
            e.kids = []

    def mark(self, elem: int, page: int) -> int:
        mcid = self._next.get(page, 0)
        self._next[page] = mcid + 1
        self.elems[elem].kids.append((page, mcid))
        return mcid


def tag(flowable, tagger: Tagger, kind: str, alt: str = ""):
    """Give a flowable (and the parts it may be split into) a structure element."""
    flowable._pdf_tag = (tagger.new(kind, alt), kind)
    return flowable


def tagged_draw_on(orig):
    """Wrap a flowable class's drawOn so what it draws becomes marked content of its element."""

    if getattr(orig, "_tagged", False):
        return orig  # already wrapped (module imported twice)

    def drawOn(self, canvas, x, y, _sW=0):
        t = getattr(self, "_pdf_tag", None)
        tagger = getattr(canvas, "_tagger", None)
        if t is None or tagger is None:
            return orig(self, canvas, x, y, _sW)
        elem, kind = t
        mcid = tagger.mark(elem, canvas.getPageNumber() - 1)
        canvas._code.append(f"/{kind} <</MCID {mcid}>> BDC")
        try:
            return orig(self, canvas, x, y, _sW)
        finally:
            canvas._code.append("EMC")

    drawOn._tagged = True
    return drawOn


def pdf_text(s: str) -> str:
    """A PDF text string (UTF-16 so any language works)."""
    return "<FEFF" + s.encode("utf-16-be").hex().upper() + ">"


def begin_artifact(canvas) -> None:
    canvas._code.append("/Artifact BMC")


def end_artifact(canvas) -> None:
    canvas._code.append("EMC")


def begin_actual_text(canvas, text: str) -> None:
    canvas._code.append(f"/Span <</ActualText {pdf_text(text)}>> BDC")


def add_structure(data: bytes, tagger: Tagger, language: str = "") -> bytes:
    """Add the structure tree, language and tagged flag to a PDF drawn with a Tagger."""
    elems = [e for e in tagger.elems if e.kids]
    if not elems:
        return data
    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        page_xrefs = [doc[i].xref for i in range(doc.page_count)]
        root = doc.get_new_xref()
        top = doc.get_new_xref()
        tree = doc.get_new_xref()
        refs = [doc.get_new_xref() for _ in elems]
        by_page: dict[int, dict[int, int]] = {}
        for e, x in zip(elems, refs):
            kids = " ".join(f"<</Type/MCR/Pg {page_xrefs[p]} 0 R/MCID {m}>>" for p, m in e.kids
                            if p < len(page_xrefs))
            alt = f"/Alt {pdf_text(e.alt)}" if e.alt else ""
            first_page = page_xrefs[e.kids[0][0]] if e.kids[0][0] < len(page_xrefs) else page_xrefs[0]
            doc.update_object(x, f"<</Type/StructElem/S/{e.kind}/P {top} 0 R/Pg {first_page} 0 R{alt}/K [{kids}]>>")
            for p, m in e.kids:
                by_page.setdefault(p, {})[m] = x
        doc.update_object(top, f"<</Type/StructElem/S/Document/P {root} 0 R/K [{' '.join(f'{x} 0 R' for x in refs)}]>>")
        nums = []
        for p in sorted(by_page):
            marks = by_page[p]
            arr = " ".join(f"{marks[m]} 0 R" if m in marks else "null" for m in range(max(marks) + 1))
            nums.append(f"{p} [{arr}]")
        doc.update_object(tree, f"<</Nums [{' '.join(nums)}]>>")
        doc.update_object(root, f"<</Type/StructTreeRoot/K {top} 0 R/ParentTree {tree} 0 R"
                                f"/ParentTreeNextKey {len(page_xrefs)}>>")
        for i, x in enumerate(page_xrefs):
            doc.xref_set_key(x, "StructParents", str(i))
            doc.xref_set_key(x, "Tabs", "/S")
        cat = doc.pdf_catalog()
        doc.xref_set_key(cat, "MarkInfo", "<</Marked true>>")
        doc.xref_set_key(cat, "StructTreeRoot", f"{root} 0 R")
        doc.xref_set_key(cat, "ViewerPreferences", "<</DisplayDocTitle true>>")
        if language:
            doc.xref_set_key(cat, "Lang", pdf_text(language))
        return doc.tobytes(garbage=0, deflate=True)
    finally:
        doc.close()


def read_structure(data: bytes) -> list[tuple[str, str, int]]:
    """The structure elements of a tagged PDF in order: (type, alt text, number of content pieces).
    For tests and checks."""
    out = []
    doc = pymupdf.open(stream=data, filetype="pdf")
    try:
        cat = doc.pdf_catalog()
        kind, val = doc.xref_get_key(cat, "StructTreeRoot")
        if kind != "xref":
            return out
        root = int(val.split()[0])
        top = int(doc.xref_get_key(root, "K")[1].split()[0])
        kids = doc.xref_get_key(top, "K")[1]
        for ref in kids.strip("[]").split(" R"):
            ref = ref.strip()
            if not ref:
                continue
            x = int(ref.split()[0])
            s = doc.xref_get_key(x, "S")[1].lstrip("/")
            alt_kind, alt = doc.xref_get_key(x, "Alt")
            if alt_kind == "string":
                pass
            elif alt_kind == "null":
                alt = ""
            n = doc.xref_get_key(x, "K")[1].count("/MCR")
            out.append((s, alt, n))
        return out
    finally:
        doc.close()
