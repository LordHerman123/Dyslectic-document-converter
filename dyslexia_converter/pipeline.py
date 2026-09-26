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
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from .extract.ocr import OcrEngine, default_engine
from .extract.pdf_reader import read_pdf
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
        # text the user typed in themselves is always kept
        doc.corrections = fresh + [c for c in doc.corrections if c.source == "user"]

    def set_correction(self, correction_id: str, status: str) -> None:
        for c in self.document.corrections:
            if c.id == correction_id:
                c.status = status

    def revert_all_corrections(self) -> None:
        for c in self.document.corrections:
            c.status = "rejected"

    def pending_corrections(self) -> list[Correction]:
        """Suggestions still waiting for a decision (not those already replaced by the user's own text)."""
        user = [u for u in self.document.corrections if u.source == "user" and u.applied]
        return [c for c in self.document.corrections
                if c.status == "pending" and not any(c.overlaps(u) for u in user)]

    def replaced_by_user(self, c: Correction) -> bool:
        return c.source != "user" and any(c.overlaps(u) for u in self.document.corrections
                                           if u.source == "user" and u.applied)

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
            result = compose(self.document, settings, self.ai_citation_decisions)
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
        if cands:
            requests += assistant.plan_citations(cands)[0]
        if words:
            requests += assistant.plan_ocr(words)[0]
        return requests

    def run_ai(self, assistant, settings: FormatSettings, progress: Optional[ProgressFn] = None) -> str:
        """Ask the (optional) AI about items local rules could not decide.

        Only a few words around each uncertain item are sent. Returns a short summary for the user.
        """
        sent = []
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
        return compose(self.document, settings, self.ai_citation_decisions)

    def export(self, fmt: str, settings: FormatSettings) -> bytes:
        from .render import docx_writer, pdf_writer, text_writer

        result = self.compose(settings)
        doc = self.document
        if fmt in ("pdf", "printable_pdf"):
            data = pdf_writer.build_pdf(result, settings, doc.title or _first_title(result), doc.author,
                                        printable=fmt == "printable_pdf")
            if fmt == "pdf":
                self.page_map = pdf_writer.last_page_map()  # for the side-by-side preview
            return data
        if fmt == "docx":
            return docx_writer.build_docx(result, settings, doc.title or _first_title(result), doc.author)
        if fmt == "txt":
            return text_writer.build_text(result).encode("utf-8")
        if fmt == "md":
            return text_writer.build_markdown(result).encode("utf-8")
        raise ValueError(f"Unknown export format: {fmt}")


def _first_title(result: ComposeResult) -> str:
    for it in result.items:
        if it.kind == "title":
            return it.text
    return ""


def _languages(doc: Document, settings: FormatSettings) -> list[str]:
    if settings.ocr_language != "auto":
        return [settings.ocr_language]
    return [doc.language]


# ----------------------------------------------------------------------------- OCR cache
# Reading scans is slow, so the result of text recognition is kept on this
# device (never uploaded). Bump CACHE_VERSION when extraction changes.

CACHE_VERSION = "1"
CACHE_ENTRIES = 30


def ocr_cache_dir() -> Path:
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
    import pymupdf

    try:
        with pymupdf.open(path) as d:
            return " ".join(d[i].get_text() for i in range(min(max_pages, d.page_count)))
    except Exception:
        return ""


def load(path: str | Path, settings: Optional[FormatSettings] = None, ocr_engine: Optional[OcrEngine] = None,
         progress: Optional[ProgressFn] = None, custom_words: Optional[CustomWords] = None,
         use_ocr: bool = True, pages: Optional[tuple[int, int]] = None) -> Session:
    """Extract and structure a PDF. The source file is only read, never written."""
    settings = settings or FormatSettings()
    path = str(path)
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
    doc = StructureDetector(dehyphenator(dictionary), word_rejoiner(dictionary)).detect(raw, path)
    doc.language = language

    pictured = sorted({p.info.source_page + 1 for p in raw.pages
                       if any(f.image.kind == "unreadable-text" for f in p.figures)})
    if pictured:
        doc.warnings.append(f"The text the scanner stored for page(s) {_page_list(pictured)} of the PDF is "
                            "unreadable, so (parts of) these pages are shown as pictures. Install Tesseract OCR "
                            "to convert them to text.")
    bad = [pg for pg in _garbled_scanner_pages(raw, dictionary) if pg not in pictured]
    if bad:
        doc.warnings.append(f"The text the scanner stored for page(s) {_page_list(bad)} of the PDF contains "
                            "errors. Install Tesseract OCR for a cleaner result.")

    session = Session(doc, custom)
    if doc.ocr_used:
        if progress:
            progress("Checking OCR text against the dictionary", 0.95)
        session.recompute_corrections(settings)
    if progress:
        progress("Done", 1.0)
    return session
