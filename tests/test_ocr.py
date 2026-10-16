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


def test_the_type_size_of_a_recognised_word_counts_the_dots_of_i_and_j():
    """A word with an i or j but no ascender ("piecewise") is as high as one with ascenders: the dots reach about
    as high (a line "A piecewise definition:" was taken for a heading)."""
    from dyslexia_converter.extract.pdf_reader import _estimate_font_size
    ink = 0.94 * 10  # ascender and descender height of a 10 pt word
    assert _estimate_font_size("piecewise", ink) == _estimate_font_size("height", ink) == 10.0
    assert _estimate_font_size("ocean", 0.5 * 10) == 10.0  # x-height only
