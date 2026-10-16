"""Formulas inside the sentences of a scanned page, which text recognition cannot read, are kept as pictures cut
from the scan (as a text PDF keeps a fraction in a line) instead of as garbled text; the words around them stay
text."""
from pathlib import Path

import pymupdf

from conftest import needs_tesseract
from dyslexia_converter import pipeline
from dyslexia_converter.extract.ocr import OcrWord
from dyslexia_converter.extract.pdf_reader import RawLine, _formula_words, _inline_formulas
from dyslexia_converter.model import BlockKind, ImageData
from dyslexia_converter.transform.spelling import Dictionary

# "Let f: Rⁿ → R be a smooth function and let x₀ ∈ Rⁿ." as text recognition reads it, with its confidences
READ = [("Let", 92), ("f:", 84), ("R”", 83), (">", 77), ("R", 91), ("be", 96), ("a", 96), ("smooth", 96),
        ("function", 96), ("and", 96), ("let", 94), ("2p", 43), ("€", 89), ("R”.", 69)]


def _words(read=READ) -> list[OcrWord]:
    """The words on one line of a page scanned at 200 dpi, 20 pixels high, 13 pixels a letter."""
    out, x = [], 100
    for text, conf in read:
        out.append(OcrWord(text, (x, 300, x + 13 * len(text), 320), float(conf), 0, 1, 0))
        x += 13 * len(text) + 9
    return out


def test_the_misread_pieces_of_a_formula_are_found_and_the_words_of_the_sentence_are_not():
    marks = _formula_words(_words(), Dictionary(["en"]).known)
    assert [w for (w, _), m in zip(READ, marks) if m] == ["f:", "R”", ">", "R", "2p", "€", "R”."]
    # a sentence read well has none, and neither have quoted words, short words or a word read unsure
    prose = [("The", 96), ("“search", 68), ("for", 95), ("truth”", 80), ("is", 96), ("a", 96), ("hard", 41),
             ("task.", 93)]
    assert not any(_formula_words(_words(prose), Dictionary(["en"]).known))


def test_a_misread_formula_becomes_a_picture_in_the_line_and_its_full_stop_stays_text():
    words = _words()
    scale = 72 / 200
    line = RawLine(" ".join(w.text for w in words), (100 * scale, 300 * scale, 900 * scale, 320 * scale), 10.0, 0,
                   source="ocr")
    cut = []

    def crop(r):
        cut.append(r)
        return ImageData(b"png", "png", 40, 12)
    out = _inline_formulas(line, words, scale, crop, Dictionary(["en"]).known)
    first, second = out.inline_images
    assert out.text == f"Let {first} be a smooth function and let {second}."
    assert all(i.kind == "inline-math" and i.text_size == 10.0 and i.width_pt > 0 for i in out.inline_images.values())
    assert [s.math for s in out.styles] == [True, True]
    assert [out.text[c.start:c.end] for c in out.conf] == ["Let", "be", "a", "smooth", "function", "and", "let"]
    # the second picture ends before the full stop, which stays text
    assert cut[1][2] < (words[-1].bbox[2] - 13) * scale + 1.5
    # a line without such pieces is left as it is
    plain = _words([("The", 96), ("gradient", 95), ("points", 96)])
    same = RawLine("The gradient points", (0, 0, 10, 10), 10.0, 0, source="ocr")
    assert _inline_formulas(same, plain, scale, crop, Dictionary(["en"]).known) is same


@needs_tesseract
def test_formulas_in_the_sentences_of_a_scanned_page_are_pictures(tmp_path):
    src = pymupdf.open(Path(__file__).parent / "stress" / "s1_math.pdf")
    out = pymupdf.open()
    pix = src[0].get_pixmap(dpi=200, colorspace=pymupdf.csGRAY)
    page = out.new_page(width=src[0].rect.width, height=src[0].rect.height)
    page.insert_image(page.rect, stream=pix.tobytes("png"))
    out.save(tmp_path / "scan.pdf")
    doc = pipeline.load(tmp_path / "scan.pdf").document
    inline = [b for b in doc.blocks if b.kind == BlockKind.PARAGRAPH and any(0xF0000 <= ord(c) for c in b.text)]
    assert inline and all(doc.inline_images[c].kind == "inline-math"
                          for b in inline for c in b.text if 0xF0000 <= ord(c))
    text = " ".join(b.text for b in doc.blocks)
    for words in ("be a smooth function", "points in the direction of steepest ascent", "describes the curvature",
                  "appear often, and so do sets like"):
        assert words in text, words
