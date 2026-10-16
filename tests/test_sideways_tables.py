"""A wide table printed sideways in a text PDF (turned to fit the page) is read as a table: its cells wrap over
several lines, and a page that continues it gets its headings. Other sideways text stays a picture."""
import pymupdf
import pytest

from dyslexia_converter import pipeline
from dyslexia_converter.model import BlockKind
from dyslexia_converter.render import pdf_writer
from dyslexia_converter.render.compose import compose
from dyslexia_converter.settings import FormatSettings

COLUMNS = (60, 200, 380, 560)  # left edges on the landscape page
HEADINGS = ("Study", "Method", "Measures", "Comments")
ROWS = [  # per row: the lines of each cell
    (["Rowe and", "Frewer (2004)"], ["Survey"], ["Nine criteria: task", "definition, early in-", "volvement."],
     ["Interviews were vali-", "dated before the evalua-", "tion began."]),
    (["Carr (2001)"], ["Interviews", "and survey"], ["Three criteria: fair-", "ness and trust."],
     ["Criteria were only", "loosely defined."]),
    (["Joss (1998)"], ["Questionnaire"], ["None stated, though the", "reports mention impact."],
     ["A consensus confer-", "ence in Denmark on", "gene technology."]),
    (["Barnes (1999)"], ["Observation and", "interviews"], ["Fairness and compe-", "tence, found after the",
                                                           "exercises."], ["Mainly descriptive of", "the two juries."]),
]


def _landscape(caption: str, headings: bool, rows: list, continued: bool = False) -> pymupdf.Document:
    """A landscape page with a table: a caption, headings between two rules, rows of wrapped cells (lines 10 points
    apart, rows 16 apart), a rule under it and, for a table that goes on, "(continued)" under that."""
    doc = pymupdf.open()
    page = doc.new_page(width=792, height=612)
    page.insert_text((60, 80), caption, fontsize=10)
    y = 100
    if headings:
        page.draw_line((60, y), (730, y), width=0.6)
        for x, h in zip(COLUMNS, HEADINGS):
            page.insert_text((x, y + 14), h, fontsize=8)
        y += 22
        page.draw_line((60, y), (730, y), width=0.4)
    y += 14
    for row in rows:
        for x, cell in zip(COLUMNS, row):
            for k, line in enumerate(cell):
                page.insert_text((x + (6 if k else 0), y + 10 * k), line, fontsize=8)
        y += 10 * max(len(c) for c in row) + 6
    page.draw_line((60, y), (730, y), width=0.6)
    if continued:
        page.insert_text((670, y + 14), "(continued)", fontsize=8)
    return doc


def _sideways(pages: list[pymupdf.Document], path) -> None:
    """The landscape pages turned onto portrait pages, as a journal prints a wide table."""
    out = pymupdf.open()
    for src in pages:
        page = out.new_page(width=612, height=792)
        page.show_pdf_page(page.rect, src, 0, rotate=90)
    out.save(path)


def test_a_sideways_table_is_read_as_a_table_and_its_next_page_gets_the_headings(tmp_path):
    path = tmp_path / "sideways.pdf"
    _sideways([_landscape("Table 1. Studies compared", True, ROWS[:2], continued=True),
               _landscape("Table 1 (continued)", False, ROWS[2:])], path)
    doc = pipeline.load(path).document
    tables = [b.table for b in doc.blocks if b.kind == BlockKind.TABLE]
    assert len(tables) == 2
    assert tables[0].rows == [list(HEADINGS),
                              ["Rowe and Frewer (2004)", "Survey", "Nine criteria: task definition, early involvement.",
                               "Interviews were validated before the evaluation began."],
                              ["Carr (2001)", "Interviews and survey", "Three criteria: fairness and trust.",
                               "Criteria were only loosely defined."]]
    assert tables[1].rows == [list(HEADINGS),
                              ["Joss (1998)", "Questionnaire", "None stated, though the reports mention impact.",
                               "A consensus conference in Denmark on gene technology."],
                              ["Barnes (1999)", "Observation and interviews",
                               "Fairness and competence, found after the exercises.",
                               "Mainly descriptive of the two juries."]]
    assert any(b.kind == BlockKind.CAPTION and b.text.startswith("Table 1. Studies") for b in doc.blocks)
    assert not any("continued)" in b.text for b in doc.blocks if b.kind != BlockKind.CAPTION)
    # the page that continues it, converted on its own: a table without headings (its first row is not set as one)
    alone = pipeline.load(path, pages=(2, 2)).document
    [table] = [b.table for b in alone.blocks if b.kind == BlockKind.TABLE]
    assert table.header_rows == 0 and table.rows == tables[1].rows[1:]
    pdf = pymupdf.open(stream=pdf_writer.build_pdf(compose(alone, FormatSettings()), FormatSettings()),
                       filetype="pdf")
    joss = next(s for p in pdf for b in p.get_text("dict")["blocks"] for l in b.get("lines", [])
                for s in l["spans"] if s["text"].startswith("Joss"))
    assert not joss["flags"] & 16 and "Bold" not in joss["font"]  # not bold: no heading row


@pytest.mark.parametrize("turn", [90, -90])
def test_sideways_text_that_is_no_table_stays_a_picture(tmp_path, turn):
    src = pymupdf.open()
    page = src.new_page(width=792, height=612)
    text = ("The participants read the passages in two layouts, and their reading speed and comprehension were "
            "measured after every passage. ") * 6
    page.insert_textbox((60, 60, 730, 560), text, fontsize=11)
    out = pymupdf.open()
    out.new_page(width=612, height=792).show_pdf_page(pymupdf.Rect(0, 0, 612, 792), src, 0, rotate=turn)
    out.save(tmp_path / "prose.pdf")
    doc = pipeline.load(tmp_path / "prose.pdf").document
    assert not any(b.kind == BlockKind.TABLE for b in doc.blocks)
    assert any(b.kind == BlockKind.IMAGE for b in doc.blocks)
