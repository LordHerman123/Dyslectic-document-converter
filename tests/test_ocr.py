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


def test_a_line_of_small_marks_under_a_scanned_formula_is_part_of_its_picture():
    """OCR reads the indices under a formula as a line of small marks ("2 ij", now measured as small type): it stays
    in the formula's picture, as far below it as the formula's own lines may be (it was cut into a second picture)."""
    from dyslexia_converter.extract.pdf_reader import RawLine, _scan_formulas
    from dyslexia_converter.model import ImageData, OcrWordConfidence

    def line(text, bbox, size, conf):
        return RawLine(text, bbox, size, 0, source="ocr", conf=[OcrWordConfidence(0, len(text), conf)])
    prose = "The model has three parts, and each of them is trained in turn."
    lines = [line(prose, (72, 100 + 14 * k, 520, 110 + 14 * k), 10, 95) for k in range(4)]
    formula = line("f(x) = |y| + 2", (220, 200, 380, 212), 12, 40)
    marks = line("2 ij", (250, 228, 290, 233), 5, 30)  # 16 points under it: more than 1.5 x its own size
    lines += [formula, marks, line(prose, (72, 260, 520, 270), 10, 95)]
    pictures, rest = _scan_formulas(lines, 595, lambda r: ImageData(b"", "png", 1, 1))
    assert len(pictures) == 1 and pictures[0].bbox[1] <= 200 and pictures[0].bbox[3] >= 233
    assert formula not in rest and marks not in rest
