"""Stress documents: mathematics, two-column layout, figures and tables (see tests/fixtures)."""
from pathlib import Path

import pytest

from dyslexia_converter import pipeline
from dyslexia_converter.extract import pdf_reader
from dyslexia_converter.model import BlockKind

FIX = Path(__file__).parent / "fixtures"


def load(name):
    return pipeline.load(FIX / name).document


@pytest.fixture(scope="module")
def maths():
    return load("s1_math.pdf")


def blocks(doc, *kinds):
    return [b for b in doc.blocks if b.kind in kinds]


def equations(doc):
    return [b for b in blocks(doc, BlockKind.IMAGE) if b.image is not None and b.image.kind == "equation"]


def text_of(doc):
    return "\n".join(b.text for b in doc.blocks if b.text)


def test_display_equations_are_kept_as_pictures(maths):
    eqs = equations(maths)
    alts = " ".join(e.image.alt for e in eqs)
    # numbered equations (1)-(10), the unnumbered sums and the braces
    for n in range(1, 11):
        assert f"({n})" in alts
    assert len(eqs) >= 11


def test_inline_formulas_stay_in_the_text(maths):
    text = text_of(maths)
    # the abstract's formulas and the formula-only last line of a paragraph are not pulled out
    abstract = next(b for b in maths.blocks if "We collect many kinds" in b.text)
    assert "a sum" in abstract.text
    assert "ℕ" in text and "ℝ" in text and "ℂ" in text
    assert "ℒ" in text  # \mathscr{L}
    assert not any(e.image.alt.startswith("We collect") for e in equations(maths))


def test_theorem_blocks_start_new_paragraphs(maths):
    assert any(b.text.startswith("Lemma 3.2.") for b in maths.blocks)
    assert any(b.text.startswith("Proof.") for b in maths.blocks)


def test_subscript_before_superscript():
    import pymupdf
    page = pymupdf.open(FIX / "s1_math.pdf")[0]
    line = next(l for l in pdf_reader._text_lines(page, 0) if "Indices can be deep" in l.text)
    assert "ai1i2(k)" in line.text


def test_matrix_rows_and_multiline_equations():
    import pymupdf
    page = pymupdf.open(FIX / "s1_math.pdf")[0]
    lines = pdf_reader._text_lines(page, 0)
    eqs, rest = pdf_reader._equations(page, lines)
    assert not any(l.text.strip() == "7 8 9" for l in rest), "the last matrix row belongs to its equation"


def test_two_column_reading_order():
    doc = load("s2_twocol.pdf")
    order = [b.text for b in blocks(doc, BlockKind.HEADING)]
    assert order.index("1 Introduction") < order.index("2 Method") < order.index("3 Results") \
        < order.index("4 Conclusion")
    body = text_of(doc)
    assert body.count("exactly once and in the right place") == 1
    assert "O(1/√T)" in body


def test_side_by_side_panels_are_separate_and_in_order():
    raw = pdf_reader.read_pdf(str(FIX / "s2_twocol.pdf"))
    figs = sorted((f for f in raw.pages[1].figures if f.image.kind == "figure"), key=lambda f: f.bbox[0])
    assert len(figs) == 3
    for a, b in zip(figs, figs[1:]):
        assert a.bbox[2] <= b.bbox[0], "panels must not overlap"


def test_booktabs_table_with_bold_best_scores():
    doc = load("s2_twocol.pdf")
    tables = [b.table for b in blocks(doc, BlockKind.TABLE)]
    main = next(t for t in tables if any("Baseline" in r[0] for r in t.rows))
    ours = next(i for i, r in enumerate(main.rows) if r[0] == "Ours")
    assert (ours, 1) in main.bold_cells and main.rows[ours][1] == "76.8"


def test_rotated_long_and_wide_tables():
    raw = pdf_reader.read_pdf(str(FIX / "s3_figtab.pdf"))
    tables = [t.table for p in raw.pages for t in p.tables]
    assert any(len(t.rows[0]) == 12 for t in tables), "twelve-column table"
    assert any(len(t.rows) >= 30 for t in tables), "long table"
    rotated = [f for p in raw.pages for f in p.figures if "rotated table" in (f.image.alt or "")]
    assert rotated and rotated[0].image.width > rotated[0].image.height, "turned upright"
    # one table is found once, even when both its rules and its caption point to it
    rects = [t.bbox for p in raw.pages for t in p.tables]
    assert len(rects) == len(set(rects))


def test_chart_labels_belong_to_the_chart():
    doc = load("s3_figtab.pdf")
    text = text_of(doc)
    assert "Epoch" not in text and "2 1.5 1" not in text


def test_times_maths_margin_notes_and_accents():
    doc = load("s4_times.pdf")
    text = text_of(doc)
    assert "Schrödinger" in text
    notes = blocks(doc, BlockKind.FOOTNOTE)
    assert any("1.055" in n.text for n in notes), "a footnote with maths stays a footnote"
    assert all("margin" not in e.image.alt for e in equations(doc))
    assert "A note in the margin." in text


def test_narrow_gutter_plain_columns_do_not_merge(tmp_path):
    """Two columns of ordinary text 12 pt apart: each line stays in its own column (no maths involved)."""
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    left = "Left column words keep flowing down the page in their own column here. " * 12
    right = "Right column sentences are separate and must never be glued to the left. " * 12
    page.insert_textbox(pymupdf.Rect(50, 60, 291, 800), left, fontsize=10, fontname="tiro")
    page.insert_textbox(pymupdf.Rect(303, 60, 545, 800), right, fontsize=10, fontname="tiro")
    path = tmp_path / "columns.pdf"
    doc.save(path)
    lines = pdf_reader._text_lines(pymupdf.open(path)[0], 0)
    assert lines and all(not ("Left" in l.text and "Right" in l.text) for l in lines)
    assert all(l.x1 < 297 or l.x0 > 297 for l in lines)
