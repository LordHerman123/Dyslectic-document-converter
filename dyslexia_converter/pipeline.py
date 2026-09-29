"""Conversion pipeline.

    PDF -> type detection -> text / OCR -> structure -> OCR correction
        -> citations (local, optional AI for uncertain cases) -> compose -> PDF / DOCX / TXT / MD

Extraction and structure detection run once per document (:func:`load`).
Everything after that is cheap, so the preview can be re-rendered whenever a
setting changes without restarting the conversion.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable, Iterable, Optional

from . import check
from .extract.ocr import OcrEngine, default_engine
from .extract.pdf_reader import read_pdf
from .extract.structured import is_structured, read_structured
from .model import Correction, Document
from .render.compose import ComposeResult, compose
from .settings import FormatSettings
from .structure.detector import StructureDetector
from .transform.spelling import (CustomWords, Dictionary, OcrCorrector, dehyphenator, detect_language,
                                 word_rejoiner)

# end of a sentence: . ! ? (optionally followed by a closing quote/bracket) and then a space
SENTENCE_END_RE = re.compile(r"[.!?][\"'”’)\]]*\s+")
# a full stop after these is not the end of a sentence
ABBREVIATIONS = {"al", "e.g", "i.e", "cf", "vs", "etc", "fig", "figs", "pp", "p", "vol", "no", "ed", "eds", "dr",
                 "prof", "mr", "mrs", "ms", "st", "ca", "approx", "resp", "z.b", "bzw", "vgl", "bijv", "d.w.z"}


def _sentence_ends(text: str, start: int = 0, end: Optional[int] = None):
    """Positions where a sentence ends in text[start:end] (skips abbreviations and initials)."""
    for m in SENTENCE_END_RE.finditer(text, start, len(text) if end is None else end):
        word = re.search(r"(\S+)$", text[:m.start()])
        w = word.group(1).lower().rstrip(".") if word else ""
        if text[m.start()] == "." and (w in ABBREVIATIONS or (len(w) == 1 and w.isalpha())):
            continue
        yield m

ProgressFn = Callable[[str, float], None]


@dataclass
class Session:
    """A loaded document plus the user's reversible decisions about it."""

    document: Document
    custom_words: CustomWords
    ai_citation_decisions: dict[str, bool] = field(default_factory=dict)
    ai_log: list[str] = field(default_factory=list)
    page_map: dict[int, list[int]] = field(default_factory=dict)  # converted page -> original pages (preview)
    layout_orders: dict[int, list[int]] = field(default_factory=dict)  # page -> reading order from the AI
    # the whole-document AI check: what it found (fixed or not), and how many parts it could not check
    check_findings: list[check.Finding] = field(default_factory=list)
    check_failed: int = 0
    check_reordered: list[int] = field(default_factory=list)  # pages the AI put in order from a finding
    check_run: bool = False  # whether the AI check ran on this document
    # how to build the document again with a reading order from the AI, and the pieces of unusual pages
    _build: Optional[Callable] = field(default=None, repr=False)
    # a Word or EPUB file laid out as pages (PDF) for the Original view; None for a PDF (shown as it is)
    original_pdf: Optional[bytes] = field(default=None, repr=False)
    _layout_pieces: dict = field(default_factory=dict, repr=False)

    # ------------------------------------------------------------ the whole-document AI check
    def view(self) -> Document:
        """The document as it is laid out: with the structure fixes the reader chose from the AI check."""
        return check.view(self.document, self.check_findings)

    def check_parts(self) -> list:
        """The document in the parts the AI check sends (see :func:`check.parts`)."""
        return check.parts(self.view())

    def check_preview(self, assistant) -> tuple[list, int]:
        """What checking now would send: the requests (parts answered before are not sent again) and the number
        of words checked."""
        doc = self.view()
        ps = check.parts(doc)
        requests = assistant.plan_check([[(n, code, page, text) for n, _, code, page, text in p] for p in ps],
                                        doc.language)[0]
        return requests, check.word_count(doc)

    def run_check(self, assistant, progress: Optional[ProgressFn] = None) -> list[check.Finding]:
        """Let the AI read the converted text and point out conversion mistakes. Every finding is checked
        against the text; nothing is changed until the reader fixes it. Findings already fixed are kept."""
        doc = self.view()
        ps = check.parts(doc)
        self.check_run = True
        answers, self.check_failed = assistant.check_parts(
            [[(n, code, page, text) for n, _, code, page, text in p] for p in ps], progress, doc.language)
        kept = [f for f in self.check_findings if f.applied]
        ids = {f.id for f in kept}
        for i, part in enumerate(ps):
            for f in check.findings_from(answers.get(i), part, doc, self.document):
                if f.id not in ids:
                    ids.add(f.id)
                    kept.append(f)
        order = {b.id: n for n, b in enumerate(self.document.blocks)}
        kept.sort(key=lambda f: (order.get(f.block_id.split("~")[0], 0), f.start))
        self.check_findings = kept
        return kept

    def finding(self, finding_id: str) -> Optional[check.Finding]:
        """The finding with this id, or None."""
        return next((f for f in self.check_findings if f.id == finding_id), None)

    def fix_finding(self, finding_id: str) -> bool:
        """Make the fix of one finding (returns False when it cannot: e.g. you already changed that text)."""
        f = self.finding(finding_id)
        if f is None or f.applied or not f.fixable:
            return False
        if f.structural:
            if any(g.applied and g.structural and g.block_id == f.block_id for g in self.check_findings):
                return False  # one change of structure per block
            f.applied = True
            return True
        b = self.document.block(f.block_id)
        if b is None or not (0 <= f.start < f.end <= len(b.text)):
            return False
        c = Correction(id=f"check-{f.id}", block_id=f.block_id, start=f.start, end=f.end,
                       original=b.text[f.start:f.end], replacement=f.replacement, confidence=1.0, status="accepted",
                       source="check")
        if any(u.source in ("user", "check") and u.applied and u.overlaps(c) for u in self.document.corrections):
            return False
        self.document.corrections.append(c)
        f.applied = True
        return True

    def undo_finding(self, finding_id: str) -> None:
        """Undo the fix of one finding: the converted text comes back as it was."""
        f = self.finding(finding_id)
        if f is None:
            return
        self.document.corrections = [c for c in self.document.corrections if c.id != f"check-{f.id}"]
        f.applied = False

    def fix_safe_findings(self) -> int:
        """Fix every broken or joined word (fixes that change only spaces and hyphens); returns how many."""
        return sum(1 for f in self.check_findings if f.safe and not f.applied and self.fix_finding(f.id))

    def undo_all_findings(self, settings: Optional[FormatSettings] = None) -> int:
        """Undo every fix made from the check (with ``settings``: also the pages the AI put in order from a
        finding); returns how many."""
        done = [f for f in self.check_findings if f.applied]
        for f in done:
            self.undo_finding(f.id)
        pages = list(self.check_reordered) if settings is not None else []
        for page in pages:
            self.undo_reorder(page, settings)
        return len(done) + len(pages)

    def check_and_fix(self, assistant, settings: FormatSettings, progress: Optional[ProgressFn] = None
                      ) -> tuple[int, list[int]]:
        """Let the AI go over the whole document: check it, let the AI put every page with text in the wrong place
        in reading order (those pages are then checked again), and make every fix that was found. Everything
        stays undoable. Returns how many fixes were made and which pages were put in order."""
        self.run_check(assistant, progress)
        pages = []
        for f in [f for f in self.check_findings if f.kind == "order"]:
            if f in self.check_findings:  # not already gone with an earlier order of its page
                page = self.reorder_page(f.id, assistant, settings, progress)
                if page is not None:
                    pages.append(page)
        if pages:
            self.run_check(assistant, progress)  # only the parts whose text changed are sent again
        fixed = sum(1 for f in list(self.check_findings) if f.fixable and not f.applied and self.fix_finding(f.id))
        return fixed, pages

    # ------------------------------------------------------------ unusual page layouts
    def layout_pages(self, extra: Iterable[int] = ()) -> dict[int, list]:
        """Pages whose columns are probably mixed up (and have no AI order yet), and the pages in ``extra`` (where
        the AI check found text in the wrong place): page number -> its pieces as the AI layout check sees them
        (place in % of the page, font size, text or None for a picture)."""
        extra = set(extra)
        if extra - set(self._layout_pieces) and self._build is not None:
            # the pieces of these pages were not kept: find them again (the document itself stays as it is)
            self._layout_pieces = self._build(self.layout_orders, extra | set(self._layout_pieces))[1]
        out = {}
        for page in self.document.pages:
            ps = self._layout_pieces.get(page.number)
            if ps and (page.unusual_layout or page.number in extra):
                out[page.number] = [_piece_view(g, page.width, page.height) for g in ps]
        return out

    def apply_layout(self, orders: dict[int, list[int]], settings: FormatSettings) -> int:
        """Build the document again with these reading orders (page -> piece numbers); returns how many pages
        changed. Decisions already made on OCR corrections of the same words are kept, and so are the reader's
        own edits and the fixes chosen from the AI check on text that did not move."""
        if not orders or self._build is None:
            return 0
        self.layout_orders.update(orders)
        self._rebuild(settings)
        return len(orders)

    def reorder_page(self, finding_id: str, assistant, settings: FormatSettings,
                     progress: Optional[ProgressFn] = None) -> Optional[int]:
        """Text in the wrong place, found by the AI check: ask the AI for the reading order of that page's pieces
        (their place, size and first and last words) and read the page in that order. Returns the page number,
        or None when the AI gave no usable order (then nothing changes). :meth:`undo_reorder` goes back."""
        f = self.finding(finding_id)
        b = self.document.block(f.block_id.split("~")[0]) if f is not None else None
        if b is None or self._build is None:
            return None
        pieces = self.layout_pages([b.page]).get(b.page)
        if not pieces or len(pieces) < 2:
            return None
        order = assistant.order_layout({b.page: pieces}, progress).get(b.page)
        if order is None:
            return None
        page = b.page
        self.apply_layout({page: order}, settings)
        if page not in self.check_reordered:
            self.check_reordered.append(page)
        # the findings on this page were about the old order: they go, with any fix made from them
        for f in [f for f in self.check_findings
                  if getattr(self.document.block(f.block_id.split("~")[0]), "page", page) == page]:
            self.undo_finding(f.id)
            self.check_findings.remove(f)
        return page

    def undo_reorder(self, page: int, settings: FormatSettings) -> None:
        """Read a page in the app's own order again (after an order from the AI)."""
        if page in self.check_reordered:
            self.check_reordered.remove(page)
        if self.layout_orders.pop(page, None) is not None:
            self._rebuild(settings)

    def _rebuild(self, settings: FormatSettings) -> None:
        """Build the document again with the reading orders in ``layout_orders``, carrying over what the reader
        decided: OCR decisions on the same words, their own edits and the AI check's fixes and findings on blocks
        whose text did not change (the others pointed at text that moved)."""
        old = self.document
        kept = {(c.original, c.replacement): c.status for c in old.corrections if c.status in ("accepted", "rejected")}
        self.document, self._layout_pieces = self._build(self.layout_orders)
        if self.document.ocr_used:
            self.recompute_corrections(settings)
            for c in self.document.corrections:
                c.status = kept.get((c.original, c.replacement), c.status)
        moved = _block_map(old.blocks, self.document.blocks)
        renamed: dict[str, str] = {}
        findings = []
        for f in self.check_findings:
            base, sep, rest = f.block_id.partition("~")
            if base not in moved:
                continue
            new_id = moved[base] + sep + rest
            renamed[f.id] = new_id + f.id[len(f.block_id):]
            f.id, f.block_id = renamed[f.id], new_id
            findings.append(f)
        self.check_findings = findings
        for c in old.corrections:
            if c.source == "user" and c.block_id in moved:
                self.document.corrections.append(replace(c, block_id=moved[c.block_id]))
            elif c.source == "check" and c.id[6:] in renamed and c.block_id in moved:
                self.document.corrections.append(replace(c, id="check-" + renamed[c.id[6:]],
                                                         block_id=moved[c.block_id]))

    # ------------------------------------------------------------ corrections
    def recompute_corrections(self, settings: FormatSettings) -> None:
        """Re-run OCR correction (e.g. after changing mode or custom words).

        Decisions the user already made on identical corrections are kept.
        """
        doc = self.document
        previous = {(c.block_id, c.start, c.original): c for c in doc.corrections}
        dictionary = Dictionary(_languages(doc, settings), self.custom_words)
        corrector = OcrCorrector(dictionary, settings.ocr_confidence_threshold)
        fresh = corrector.correct_document(doc, settings.ocr_correction, settings.correct_selectable_text)
        for c in fresh:
            old = previous.get((c.block_id, c.start, c.original))
            if old is not None and old.status in ("accepted", "rejected") and old.replacement == c.replacement:
                c.status = old.status
        # text the user typed in themselves, and fixes they chose from the AI check, are always kept
        doc.corrections = fresh + [c for c in doc.corrections if c.source in ("user", "check")]

    def set_correction(self, correction_id: str, status: str) -> None:
        """Set the status of one correction ("accepted", "rejected", ...) by its id."""
        for c in self.document.corrections:
            if c.id == correction_id:
                c.status = status

    def revert_all_corrections(self) -> None:
        """Reject every correction: the text is shown as OCR read it."""
        for c in self.document.corrections:
            c.status = "rejected"

    def pending_corrections(self) -> list[Correction]:
        """Suggestions still waiting for a decision (not those already replaced by the user's own text)."""
        user = [u for u in self.document.corrections if u.source in ("user", "check") and u.applied]
        return [c for c in self.document.corrections
                if c.status == "pending" and not any(c.overlaps(u) for u in user)]

    def replaced_by_user(self, c: Correction) -> bool:
        """Whether a correction is covered by the user's own edit of the same text (then it is not shown for
        review).
        """
        return c.source not in ("user", "check") and any(c.overlaps(u) for u in self.document.corrections
                                                         if u.source in ("user", "check") and u.applied)

    def sentence_span(self, c: Correction) -> tuple[int, int]:
        """Start and end (in the block's original text) of the sentence around a correction."""
        b = self.document.block(c.block_id)
        text = b.text if b else ""
        start = 0
        for m in _sentence_ends(text, 0, c.start):
            start = m.end()
        m = next(_sentence_ends(text, c.end), None)
        end = m.start() + 1 if m else len(text)
        while start < c.start and text[start].isspace():
            start += 1
        return start, max(end, c.end)

    def editable_sentence(self, c: Correction) -> str:
        """The sentence around ``c`` as the user last left it (the scan's text plus their own edits)."""
        b = self.document.block(c.block_id)
        if b is None:
            return c.original
        start, end = self.sentence_span(c)
        text = b.text[start:end]
        for u in sorted((u for u in self.document.corrections
                         if u.source == "user" and u.block_id == c.block_id and start <= u.start and u.end <= end),
                        key=lambda u: u.start, reverse=True):
            text = text[:u.start - start] + u.replacement + text[u.end - start:]
        return text

    def edit_text(self, c: Correction, new_text: str) -> Optional[Correction]:
        """The user retyped the sentence around ``c`` (as read from the scan).

        Only the changed words are stored, as a correction of source "user"; the scanned text itself is kept,
        so the edit can be undone. Returns the new correction, or None if nothing changed.
        """
        b = self.document.block(c.block_id)
        if b is None:
            return None
        start, end = self.sentence_span(c)
        old = b.text[start:end]
        new = new_text.strip()
        if not new or new == old:
            return None
        # keep only the part that differs, widened to whole words
        a = 0
        while a < min(len(old), len(new)) and old[a] == new[a]:
            a += 1
        z = 0
        while z < min(len(old), len(new)) - a and old[-1 - z] == new[-1 - z]:
            z += 1
        while a > 0 and not old[a - 1].isspace():
            a -= 1
        while z > 0 and not old[len(old) - z].isspace():
            z -= 1
        edit = Correction(id=f"user-{uuid.uuid4().hex[:10]}", block_id=c.block_id, start=start + a,
                          end=start + len(old) - z, original=old[a:len(old) - z],
                          replacement=new[a:len(new) - z], confidence=1.0, status="accepted", source="user")
        # an earlier edit of the same words is replaced by this one
        self.document.corrections = [x for x in self.document.corrections
                                     if not (x.source == "user" and x.overlaps(edit))] + [edit]
        return edit

    def remove_user_edit(self, correction_id: str) -> None:
        """Undo text the user typed in; the scan's own text (and any suggestion) comes back."""
        self.document.corrections = [c for c in self.document.corrections
                                     if not (c.id == correction_id and c.source == "user")]

    def correction_sentence(self, c: Correction, limit: int = 220) -> tuple[str, str, str]:
        """(text before, the word, text after) for the whole sentence that contains a correction.

        Very long sentences are shortened at a word boundary (marked with …) so the card stays readable.
        """
        b = self.document.block(c.block_id)
        if b is None:
            return "", c.original, ""
        start, end = self.sentence_span(c)
        before, after = b.text[start:c.start], b.text[c.end:end]
        if len(before) > limit:
            cut = before.find(" ", len(before) - limit)
            before = "…" + before[cut + 1 if cut >= 0 else len(before) - limit:]
        if len(after) > limit:
            cut = after.rfind(" ", 0, limit)
            after = after[:cut if cut > 0 else limit] + "…"
        return before, c.original, after.rstrip()

    # --------------------------------------------------------------------- AI
    def _ai_items(self, assistant, settings: FormatSettings):
        """The uncertain items the AI may be asked about: citation candidates and OCR corrections, each with
        the text they sit in and their position (the assistant sends only a few words around them)."""
        ai = assistant.settings
        cands = []
        if ai.use_for_citations and settings.move_citations:
            result = self.compose(settings)
            seen: set[str] = set()
            for block_id, c in result.uncertain_citations:
                if c.key in seen:
                    continue  # never send the same content twice
                seen.add(c.key)
                b = self.document.block(block_id)
                text = self.document.display_text(b) if b else c.text
                if not b:
                    cands.append((c.key, c.text, 0, len(c.text)))
                else:
                    cands.append((c.key, text, c.start, c.end))
        words = []
        if ai.use_for_ocr:
            for c in self.pending_corrections():
                b = self.document.block(c.block_id)
                if b is not None:
                    words.append((c, b.text, c.start, c.end))
        return cands, words

    def ai_preview(self, assistant, settings: FormatSettings) -> list:
        """The requests that asking the AI now would send (answers known from earlier are not sent again)."""
        cands, words = self._ai_items(assistant, settings)
        requests = []
        pages = self.layout_pages() if getattr(assistant.settings, "use_for_layout", False) else {}
        if pages:
            requests += assistant.plan_layout(pages)[0]
        if cands:
            requests += assistant.plan_citations(cands)[0]
        if words:
            requests += assistant.plan_ocr(words)[0]
        return requests

    def run_ai(self, assistant, settings: FormatSettings, progress: Optional[ProgressFn] = None) -> str:
        """Ask the (optional) AI about items local rules could not decide.

        Only a few words around each uncertain item are sent. Pages with an unusual layout go first (the first
        and last words of each piece of the page), so the other questions are asked about the text in its new
        order. Returns a short summary for the user.
        """
        sent = []
        pages = self.layout_pages() if getattr(assistant.settings, "use_for_layout", False) else {}
        if pages:
            self.apply_layout(assistant.order_layout(pages, progress), settings)
            sent.append(f"{len(pages)} page(s) with an unusual layout")
        cands, words = self._ai_items(assistant, settings)
        if cands:
            self.ai_citation_decisions.update(assistant.classify_citations(cands, progress))
            sent.append(f"{len(cands)} uncertain citation(s)")
        if words:
            assistant.review_ocr_words(words, progress)
            sent.append(f"{len(words)} uncertain OCR word(s)")
        summary = ("Sent to AI: " + ", ".join(sent)) if sent else "Nothing needed AI help."
        self.ai_log.append(summary)
        return summary

    # ------------------------------------------------------------------ render
    def compose(self, settings: FormatSettings) -> ComposeResult:
        """The document laid out for the settings (items ready for any output format), with the fixes chosen from
        the AI check."""
        return compose(self.view(), settings, self.ai_citation_decisions)

    def export(self, fmt: str, settings: FormatSettings) -> bytes:
        """The document in an output format: "pdf", "printable_pdf", "docx", "epub", "txt" or "md" (bytes)."""
        from .render import docx_writer, epub_writer, pdf_writer, text_writer

        result = self.compose(settings)
        doc = self.view()
        if fmt in ("pdf", "printable_pdf"):
            data = pdf_writer.build_pdf(result, settings, doc.title or _first_title(result), doc.author,
                                        printable=fmt == "printable_pdf")
            if fmt == "pdf":
                self.page_map = pdf_writer.last_page_map()  # for the side-by-side preview
            return data
        if fmt == "docx":
            return docx_writer.build_docx(result, settings, doc.title or _first_title(result), doc.author)
        if fmt == "epub":
            return epub_writer.build_epub(result, settings, doc.title or _first_title(result), doc.author)
        if fmt == "txt":
            return text_writer.build_text(result).encode("utf-8")
        if fmt == "md":
            return text_writer.build_markdown(result).encode("utf-8")
        raise ValueError(f"Unknown export format: {fmt}")


def _block_map(old: list, new: list) -> dict[str, str]:
    """Which new block each old block became, for blocks whose text did not change (in order, so a text that
    occurs twice is matched to its own copy)."""
    free: dict[str, list[str]] = {}
    for b in new:
        if b.text:
            free.setdefault(b.text, []).append(b.id)
    out = {}
    for b in old:
        ids = free.get(b.text) if b.text else None
        if ids:
            out[b.id] = ids.pop(0)
    return out


def _first_title(result: ComposeResult) -> str:
    """The text of the first title item, or ""."""
    for it in result.items:
        if it.kind == "title":
            return it.text
    return ""


def _languages(doc: Document, settings: FormatSettings) -> list[str]:
    """The OCR/spelling languages: the one the user chose, or the detected one."""
    if settings.ocr_language != "auto":
        return [settings.ocr_language]
    return [doc.language]


# ----------------------------------------------------------------------------- OCR cache
# Reading scans is slow, so the result of text recognition is kept on this
# device (never uploaded). Bump CACHE_VERSION when extraction changes.

CACHE_VERSION = "1"
CACHE_ENTRIES = 30


def ocr_cache_dir() -> Path:
    """The folder where OCR results are kept, so a scanned document is not read again when reopened."""
    from .settings import app_data_dir

    d = app_data_dir() / "ocr_cache"
    d.mkdir(parents=True, exist_ok=True)
    return d


def clear_ocr_cache() -> int:
    """Delete saved OCR results; returns how many documents were forgotten."""
    n = 0
    for f in ocr_cache_dir().glob("*.pkl"):
        try:
            f.unlink()
            n += 1
        except OSError:
            pass
    return n


def _cache_key(path: str, langs: list[str], engine, options: dict) -> str:
    """The cache key of a document: its content, the languages, the OCR engine, the options and the reader's version
    (a change in any of them reads the document again).
    """
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    h.update(repr((CACHE_VERSION, _extraction_fingerprint(), sorted(langs), getattr(engine, "name", None),
                   sorted(options.items()))).encode())
    return h.hexdigest()


def _extraction_fingerprint() -> str:
    """Changes whenever the extraction code changes, so updates never reuse stale results."""
    import hashlib

    h = hashlib.sha256()
    for f in sorted((Path(__file__).parent / "extract").glob("*.py")):
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def _cache_load(key: str):
    """The saved reading of a document, or None (a damaged file counts as missing)."""
    import pickle

    f = ocr_cache_dir() / f"{key}.pkl"
    try:
        with open(f, "rb") as fh:
            raw = pickle.load(fh)
        f.touch()
        return raw
    except Exception:
        return None


def _cache_store(key: str, raw) -> None:
    """Save the reading of a document (via a temporary file; failing to save is ignored)."""
    import pickle

    d = ocr_cache_dir()
    try:
        tmp = d / f"{key}.tmp"
        with open(tmp, "wb") as fh:
            pickle.dump(raw, fh, protocol=pickle.HIGHEST_PROTOCOL)
        tmp.replace(d / f"{key}.pkl")
        files = sorted(d.glob("*.pkl"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in files[CACHE_ENTRIES:]:
            old.unlink()
    except OSError:
        pass


def _garbled_scanner_pages(raw, dictionary: Dictionary, threshold: float = 0.9) -> list[int]:
    """PDF page numbers (1-based) whose scanner text layer is mostly not real words."""
    import re

    scores: dict[int, list[int]] = {}
    for p in raw.pages:
        if p.info.text_source != "scanner":
            continue
        words = [w for l in p.lines for w in re.findall(r"[A-Za-z]{3,}", l.text)]
        good = sum(1 for w in words if dictionary.known(w))
        s = scores.setdefault(p.info.source_page + 1, [0, 0])
        s[0] += good
        s[1] += len(words)
    return [pg for pg, (good, n) in sorted(scores.items()) if n >= 20 and good / n < threshold]


def _piece_view(group: list, width: float, height: float) -> tuple:
    """A piece of a page as the AI layout check sees it: (x0, y0, x1, y1 in % of the page, font size, its text,
    or None for a picture or table)."""
    x0 = min(it.bbox[0] for it in group)
    y0 = min(it.bbox[1] for it in group)
    x1 = max(it.bbox[2] for it in group)
    y1 = max(it.bbox[3] for it in group)
    texts = [it.text for it in group if isinstance(getattr(it, "text", None), str)]
    sizes = sorted(it.size for it in group if isinstance(getattr(it, "text", None), str))
    w, h = max(1.0, width), max(1.0, height)
    return (100 * x0 / w, 100 * y0 / h, 100 * x1 / w, 100 * y1 / h, round(sizes[len(sizes) // 2]) if sizes else 0,
            " ".join(texts) if texts else None)


def _page_list(pages: list[int]) -> str:
    """[3, 4, 5, 9] -> '3-5, 9'"""
    out, start, prev = [], None, None
    for p in pages + [None]:
        if start is None:
            start = prev = p
        elif p is not None and p == prev + 1:
            prev = p
        else:
            out.append(f"{start}" if start == prev else f"{start}-{prev}")
            start = prev = p
    return ", ".join(out)


def _text_layer_sample(path: str, max_pages: int = 6) -> str:
    """Text of the first pages' text layer (for guessing the language before OCR)."""
    import pymupdf

    try:
        with pymupdf.open(path) as d:
            return " ".join(d[i].get_text() for i in range(min(max_pages, d.page_count)))
    except Exception:
        return ""


def _load_structured(path: str, settings: FormatSettings, progress: Optional[ProgressFn],
                     custom_words: Optional[CustomWords]) -> Session:
    """A Word or EPUB file: its own structure is read directly (no text recognition or layout guessing needed)."""
    if progress:
        progress("Reading the document", 0.2)
    doc, original = read_structured(path)
    if settings.ocr_language != "auto":
        doc.language = settings.ocr_language
    else:
        sample = " ".join(b.text for b in doc.blocks[:80] if b.text)
        if len(sample) > 200:
            doc.language = detect_language(sample)
    session = Session(doc, custom_words or CustomWords(), original_pdf=original)
    session._build = lambda orders=None, extra=(): (doc, {})  # the reading order is the file's own
    if progress:
        progress("Done", 1.0)
    return session


def load(path: str | Path, settings: Optional[FormatSettings] = None, ocr_engine: Optional[OcrEngine] = None,
         progress: Optional[ProgressFn] = None, custom_words: Optional[CustomWords] = None,
         use_ocr: bool = True, pages: Optional[tuple[int, int]] = None) -> Session:
    """Extract and structure a PDF, Word (.docx) or EPUB file. The source file is only read, never written."""
    settings = settings or FormatSettings()
    path = str(path)
    if is_structured(path):
        return _load_structured(path, settings, progress, custom_words)
    engine = (ocr_engine or default_engine()) if use_ocr else None
    ocr_langs = ["en", "nl"] if settings.ocr_language == "auto" else [settings.ocr_language]
    if settings.ocr_language == "auto":
        # a text layer (e.g. from the scanner) tells us the language, so OCR can use just that one
        hint = _text_layer_sample(path)
        if len(hint) > 300:
            ocr_langs = [detect_language(hint)]
    if engine is not None:
        available = engine.languages()
        ocr_langs = [l for l in ocr_langs if l in available] or ["en"]
    options = dict(pages=pages, split_spreads=settings.split_spreads,
                   prefer_text_layer=settings.scan_text_source == "text_layer")
    check_langs = ocr_langs if settings.ocr_language == "auto" else [settings.ocr_language]
    known_word = Dictionary(check_langs, custom_words).known
    cache_key = _cache_key(path, ocr_langs, engine, options)
    raw = _cache_load(cache_key)
    if raw is not None:
        if progress:
            progress("Using the saved text recognition of this document", 0.9)
    else:
        raw = read_pdf(path, engine, ocr_langs, progress, known_word=known_word, **options)
        if any(p.info.ocr_used for p in raw.pages):
            _cache_store(cache_key, raw)

    sample = " ".join(l.text for p in raw.pages[:5] for l in p.lines)
    language = settings.ocr_language if settings.ocr_language != "auto" else detect_language(sample)
    custom = custom_words or CustomWords()
    dictionary = Dictionary([language], custom)

    if progress:
        progress("Detecting document structure", 0.9)
    pictured = sorted({p.info.source_page + 1 for p in raw.pages
                       if any(f.image.kind == "unreadable-text" for f in p.figures)})
    bad = [pg for pg in _garbled_scanner_pages(raw, dictionary) if pg not in pictured]

    def build(orders: Optional[dict[int, list[int]]] = None, extra: Iterable[int] = ()) -> tuple[Document, dict]:
        """The structured document (with the AI's reading order for these pages) and the pieces of every page
        with an unusual layout or an AI order, and of the pages in ``extra``."""
        detector = StructureDetector(dehyphenator(dictionary), word_rejoiner(dictionary))
        doc = detector.detect(raw, path, orders, extra)
        doc.language = language
        if pictured:
            doc.warnings.append(f"The text the scanner stored for page(s) {_page_list(pictured)} of the PDF is "
                                "unreadable, so (parts of) these pages are shown as pictures. Install Tesseract "
                                "OCR to convert them to text.")
        if bad:
            doc.warnings.append(f"The text the scanner stored for page(s) {_page_list(bad)} of the PDF contains "
                                "errors. Install Tesseract OCR for a cleaner result.")
        unusual = sorted({p.info.source_page + 1 for p in raw.pages if p.info.unusual_layout})
        if unusual:
            doc.warnings.append(f"Page(s) {_page_list(unusual)} of the PDF have an unusual layout (a box or "
                                "quote across the columns); the app read them column by column. Compare with the "
                                "original in the Both view.")
        return doc, detector.layout_pieces

    doc, layout_pieces = build()
    session = Session(doc, custom)
    session._build, session._layout_pieces = build, layout_pieces
    if doc.ocr_used:
        if progress:
            progress("Checking OCR text against the dictionary", 0.95)
        session.recompute_corrections(settings)
    if progress:
        progress("Done", 1.0)
    return session
