"""Headless self-test for packaged builds.

    DyslexiaConverter.exe --selftest input.pdf output.pdf [log.txt]

Converts one PDF without opening a window and writes a short report. The
release workflow runs this on the finished .exe before publishing it.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path


def run(argv: list[str]) -> int:
    src = Path(argv[0]) if argv else None
    out = Path(argv[1]) if len(argv) > 1 else None
    log = Path(argv[2]) if len(argv) > 2 else (out.with_suffix(".log") if out else Path("selftest.log"))
    lines: list[str] = []
    try:
        from . import __version__, pipeline
        from .extract.ocr import find_tesseract

        lines.append(f"Dyslexia Converter {__version__}")
        lines.append(f"Tesseract: {find_tesseract()}")
        if src is None or out is None:
            raise SystemExit("usage: --selftest input.pdf output.pdf [log.txt]")
        session = pipeline.load(src)
        doc = session.document
        lines.append(f"PDF type: {doc.pdf_type}; OCR used: {doc.ocr_used}; blocks: {len(doc.blocks)}")
        lines += [f"Warning: {w}" for w in doc.warnings]
        out.write_bytes(session.export("pdf", pipeline.FormatSettings()))
        lines.append(f"Wrote {out} ({out.stat().st_size} bytes)")
        code = 0
    except BaseException:  # the report must always be written
        lines.append(traceback.format_exc())
        code = 1
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if sys.stdout is not None:
        print("\n".join(lines))
    return code
