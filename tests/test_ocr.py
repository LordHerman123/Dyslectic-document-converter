from conftest import needs_tesseract

from dyslexia_converter import pipeline
from dyslexia_converter.model import BlockKind


@needs_tesseract
def test_scanned_pdf_is_ocrd_and_structured(scanned):
    doc = pipeline.load(scanned).document
    assert doc.pdf_type == "scanned" and doc.ocr_used
    text = " ".join(b.text for b in doc.blocks)
    assert "Reading difficulties affect a substantial proportion" in text
    headings = [b.text for b in doc.blocks if b.kind == BlockKind.HEADING]
    assert "1 Introduction" in headings and "References" in headings
    assert any(b.kind == BlockKind.IMAGE for b in doc.blocks)


@needs_tesseract
def test_scanned_export_keeps_text_selectable(scanned):
    import pymupdf

    session = pipeline.load(scanned)
    pdf = session.export("pdf", pipeline.FormatSettings())
    with pymupdf.open(stream=pdf, filetype="pdf") as d:
        assert "Reading difficulties" in "".join(p.get_text() for p in d)
