"""Command-line interface.

    python -m dyslexia_converter paper.pdf                      # -> paper_readable.pdf
    python -m dyslexia_converter paper.pdf -f docx --preset Spacious
    python -m dyslexia_converter paper.pdf --font "OpenDyslexic" --size 14 --bold-start
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import pipeline
from .fonts import FONT_CHOICES, get_family
from .settings import PRESETS, SettingsStore

EXT = {"pdf": ".pdf", "printable_pdf": ".pdf", "docx": ".docx", "txt": ".txt", "md": ".md"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="dyslexia-converter",
                                 description="Convert PDFs into a cleaner, more readable layout (no AI needed).")
    ap.add_argument("input", help="PDF file to convert (it is never modified)")
    ap.add_argument("-o", "--output", help="output file (default: <input>_readable.<ext>)")
    ap.add_argument("-f", "--format", default="pdf", choices=list(EXT))
    ap.add_argument("--preset", choices=list(PRESETS) + ["My Settings"], default=None)
    ap.add_argument("--font", choices=FONT_CHOICES)
    ap.add_argument("--size", type=float, help="font size in pt")
    ap.add_argument("--line-spacing", type=float)
    ap.add_argument("--paragraph-spacing", type=float, help="pt")
    ap.add_argument("--letter-spacing", type=float, help="extra pt between letters")
    ap.add_argument("--word-spacing", type=float, help="extra pt between words")
    ap.add_argument("--align", choices=["left", "center", "justify"])
    ap.add_argument("--margins", type=float, help="all page margins in cm")
    ap.add_argument("--reading-width", type=float, help="maximum text width in cm")
    ap.add_argument("--bold-start", action="store_true", help="bold the first part of words")
    ap.add_argument("--bold-amount", choices=["first_letter", "25", "40", "auto"])
    ap.add_argument("--move-citations", action="store_true", help="replace author-year citations by [n]")
    ap.add_argument("--keep-footnotes", action="store_true", help="do not move footnotes to the end")
    ap.add_argument("--ocr-correction", choices=["automatic", "review", "disabled"])
    ap.add_argument("--language", choices=["auto", "en", "nl", "de", "fr", "es", "it", "pt"])
    ap.add_argument("--pages", help="page range to convert, e.g. 3-12")
    ap.add_argument("--no-ocr", action="store_true")
    args = ap.parse_args(argv)

    store = SettingsStore()
    s = store.preset(args.preset) if args.preset else (store.load_format() if store.has_saved_format()
                                                       else PRESETS["Standard"].copy())
    changes = {k: v for k, v in {
        "font": args.font, "font_size": args.size, "line_spacing": args.line_spacing,
        "paragraph_spacing": args.paragraph_spacing, "letter_spacing": args.letter_spacing,
        "word_spacing": args.word_spacing, "alignment": args.align, "reading_width": args.reading_width,
        "bold_amount": args.bold_amount, "ocr_correction": args.ocr_correction, "ocr_language": args.language,
    }.items() if v is not None}
    if args.margins is not None:
        changes.update(margin_top=args.margins, margin_bottom=args.margins,
                       margin_left=args.margins, margin_right=args.margins)
    if args.bold_start:
        changes["bold_word_start"] = True
    if args.move_citations:
        changes["move_citations"] = True
    if args.keep_footnotes:
        changes["move_footnotes"] = False
    s = s.copy(**changes)

    src = Path(args.input)
    if not src.is_file():
        print(f"File not found: {src}", file=sys.stderr)
        return 2
    out = Path(args.output) if args.output else src.with_name(src.stem + "_readable" + EXT[args.format])
    if out.resolve() == src.resolve():
        print("Refusing to overwrite the original PDF. Choose another output name.", file=sys.stderr)
        return 2
    pages = None
    if args.pages:
        a, _, b = args.pages.partition("-")
        pages = (int(a), int(b or a))

    def progress(msg: str, frac: float) -> None:
        print(f"\r{msg:<60}", end="", file=sys.stderr, flush=True)

    session = pipeline.load(src, s, progress=progress, use_ocr=not args.no_ocr, pages=pages)
    print(file=sys.stderr)
    doc = session.document
    print(f"PDF type: {doc.pdf_type}; OCR used: {'yes' if doc.ocr_used else 'no'}; language: {doc.language}")
    note = get_family(s.font).substitute_note
    if note:
        print(note)
    for w in doc.warnings:
        print("Warning:", w)
    if doc.corrections:
        applied = sum(1 for c in doc.corrections if c.applied)
        pending = sum(1 for c in doc.corrections if c.status == "pending")
        print(f"OCR corrections applied: {applied}; uncertain (not applied, review in the app): {pending}")
    if s.move_citations:
        print("Note: automated citation detection can make mistakes; original citation text is kept.")
    out.write_bytes(session.export(args.format, s))
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
