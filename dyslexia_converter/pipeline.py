"""Conversion pipeline.

    PDF -> type detection -> text / OCR -> structure -> OCR correction
        -> citations (local, optional AI for uncertain cases) -> compose -> PDF / DOCX / TXT / MD

Extraction and structure detection run once per document (:func:`load`).
Everything after that is cheap, so the preview can be re-rendered whenever a
setting changes without restarting the conversion.
"""
from __future__ import annotations

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

ProgressFn = Callable[[str, float], None]


@dataclass
class Session:
    """A loaded document plus the user's reversible decisions about it."""

    document: Document
    custom_words: CustomWords
    ai_citation_decisions: dict[str, bool] = field(default_factory=dict)
    ai_log: list[str] = field(default_factory=list)

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
        doc.corrections = fresh

    def set_correction(self, correction_id: str, status: str) -> None:
        for c in self.document.corrections:
            if c.id == correction_id:
                c.status = status

    def revert_all_corrections(self) -> None:
        for c in self.document.corrections:
            c.status = "rejected"

    def pending_corrections(self) -> list[Correction]:
        return [c for c in self.document.corrections if c.status == "pending"]

    def correction_context(self, c: Correction, width: int = 40) -> tuple[str, str]:
        """(original snippet, corrected snippet) around a correction."""
        b = self.document.block(c.block_id)
        if b is None:
            return c.original, c.replacement
        a = max(0, c.start - width)
        e = min(len(b.text), c.end + width)
        before, after = b.text[a:c.start], b.text[c.end:e]
        pre = "…" if a > 0 else ""
        post = "…" if e < len(b.text) else ""
        return (f"{pre}{before}{c.original}{after}{post}", f"{pre}{before}{c.replacement}{after}{post}")

    # --------------------------------------------------------------------- AI
    def run_ai(self, assistant, settings: FormatSettings, progress: Optional[ProgressFn] = None) -> str:
        """Ask the (optional) AI about items local rules could not decide.

        Only uncertain snippets are sent. Returns a short summary for the user.
        """
        sent = []
        ai = assistant.settings
        if ai.use_for_citations and settings.move_citations:
            result = compose(self.document, settings, self.ai_citation_decisions)
            cands = []
            seen: set[str] = set()
            for block_id, c in result.uncertain_citations:
                if c.key in seen:
                    continue  # never send the same content twice
                seen.add(c.key)
                b = self.document.block(block_id)
                text = self.document.display_text(b) if b else c.text
                ctx = text[max(0, c.start - 120): c.end + 60]
                cands.append((c.key, c.text, ctx))
            if cands:
                self.ai_citation_decisions.update(assistant.classify_citations(cands, progress))
                sent.append(f"{len(cands)} uncertain citation(s)")
        if ai.use_for_ocr:
            items = []
            for c in self.pending_corrections():
                b = self.document.block(c.block_id)
                if b is not None:
                    items.append((c, b.text[max(0, c.start - 80): c.end + 80]))
            if items:
                assistant.review_ocr_words(items, progress)
                sent.append(f"{len(items)} uncertain OCR word(s)")
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
            return pdf_writer.build_pdf(result, settings, doc.title or _first_title(result), doc.author,
                                        printable=fmt == "printable_pdf")
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
    raw = read_pdf(path, engine, ocr_langs, progress, pages, split_spreads=settings.split_spreads,
                   prefer_text_layer=settings.scan_text_source == "text_layer")

    sample = " ".join(l.text for p in raw.pages[:5] for l in p.lines)
    language = settings.ocr_language if settings.ocr_language != "auto" else detect_language(sample)
    custom = custom_words or CustomWords()
    dictionary = Dictionary([language], custom)

    if progress:
        progress("Detecting document structure", 0.9)
    doc = StructureDetector(dehyphenator(dictionary), word_rejoiner(dictionary)).detect(raw, path)
    doc.language = language
    if any(p.info.kind != "text" for p in raw.pages) and engine is None:
        doc.warnings.append("No OCR engine found. Install Tesseract to convert scanned pages.")

    session = Session(doc, custom)
    if doc.ocr_used:
        if progress:
            progress("Checking OCR text against the dictionary", 0.95)
        session.recompute_corrections(settings)
    if progress:
        progress("Done", 1.0)
    return session
