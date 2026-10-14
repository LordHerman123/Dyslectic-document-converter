"""Sentences kept whole and clutter kept out: bullets drawn apart from their item, table cells whose words have no
space characters, borderless tables, large numbers before numbered points, words broken by a soft hyphen across a
paragraph break, a sentence going on below a drop cap, notes numbered in the margin, page numbers of pages that are
only pictures, publisher badges and article labels on the first page. Each test also checks the case the rule must
leave alone."""
import io
import re

import pymupdf
from PIL import Image

from dyslexia_converter import pipeline
from dyslexia_converter.extract.pdf_reader import _with_breaks
from dyslexia_converter.model import Block, BlockKind
from dyslexia_converter.structure.detector import StructureDetector
from test_robustness import BODY, FONT, body_rows, make_pdf


def load(tmp_path, pages, name="doc.pdf", extra=None):
    """The document read from ``pages`` (see :func:`make_pdf`); ``extra(doc)`` can add to the PDF first."""
    path = tmp_path / name
    make_pdf(path, pages)
    if extra is not None:
        doc = pymupdf.open(str(path))
        extra(doc)
        doc.save(str(tmp_path / ("x" + name)))
        path = tmp_path / ("x" + name)
    return pipeline.load(path, use_ocr=False).document


def find(bl, text):
    return next(b for b in bl if text in b.text)


def test_a_bullet_drawn_apart_stays_with_its_item(isolated_home, tmp_path):
    rows = body_rows(80, 10) + [(60, 220, "The process has four common features, for example:", 10)]
    items = ["participatory processes are highly structured;", "their duration is defined beforehand;",
             "interaction takes place in small groups;"]
    for k, text in enumerate(items):
        y = 240 + 14 * k
        rows += [(71, y + 0.5, "●", 8), (81, y, text, 10)]  # smaller, a little lower, 5 points to the left
    rows += [(60, 300, "In units a middle dot is no bullet: 21.5 kJ at 10 A", 10), (305, 300, "·", 10),
             (309, 300, "m per day as measured.", 10)] + body_rows(320, 20)
    bl = load(tmp_path, [rows]).blocks
    for text in items:
        assert find(bl, text).kind == BlockKind.LIST_ITEM
    assert not any(b.text.strip() == "●" for b in bl)
    assert re.search(r"at 10 A ?· ?m per day", find(bl, "middle dot").text)  # the dot stays where it is


def test_table_cells_keep_their_word_breaks():
    assert _with_breaks("RelevantRIdimensions", ["Relevant", "RI", "dimensions"]) == "Relevant RI dimensions"
    assert _with_breaks("Risksidentified,managed", ["Risks", "identiﬁed,", "managed"]) == "Risks identified, managed"
    assert _with_breaks("already spaced", ["already", "spaced"]) == "already spaced"
    assert _with_breaks("abc", ["ab", "x"]) == "abc"  # other letters: left as it is


def test_a_borderless_table_is_a_table_but_running_text_is_not(isolated_home, tmp_path):
    rows = body_rows(80, 12) + [(60, 250, "A borderless table, as often found in reports:", 10)]
    for k, cells in enumerate([("Name", "Role", "Office"), ("Anna", "Editor", "2.14"), ("Bram", "Reviewer", "3.02"),
                               ("Chen", "Author", "1.07")]):
        rows += [(x, 275 + 14 * k, c, 10) for x, c in zip((237, 290, 360), cells)]
    rows += body_rows(350, 20)
    doc = load(tmp_path, [rows])
    [table] = [b for b in doc.blocks if b.kind == BlockKind.TABLE]
    assert table.table.rows == [["Name", "Role", "Office"], ["Anna", "Editor", "2.14"], ["Bram", "Reviewer", "3.02"],
                                ["Chen", "Author", "1.07"]]
    assert not any(b.kind == BlockKind.TABLE for b in load(tmp_path, [body_rows(80, 50)], "b.pdf").blocks)


def test_a_large_number_goes_before_its_point_not_into_its_second_line(isolated_home, tmp_path):
    rows = body_rows(80, 20) + [
        (44, 352, "1", 15), (60, 344, "Quantitative evaluation should sup-", 9),  # as tall as both lines
        (60, 355, "port qualitative, expert assessment.", 9),
        (60, 370, "Quantitative metrics can challenge bias tendencies in peer review.", 9)] + body_rows(390, 20)
    bl = load(tmp_path, [rows]).blocks
    assert "1 Quantitative evaluation should support qualitative, expert assessment." in " ".join(b.text for b in bl)
    # a number inside a line keeps its place
    rows = body_rows(80, 20) + [(60, 355, "while consuming 21.5 kJ at", 9), (176, 355, "10", 13),
                                (190, 355, "m and the same load.", 9)] + body_rows(380, 20)
    assert re.search(r"at 10 ?m and the same load", " ".join(b.text for b in load(tmp_path, [rows], "b.pdf").blocks))


def test_a_soft_hyphen_joins_a_word_across_a_paragraph_break():
    a = Block("a", BlockKind.PARAGRAPH, "Before 2000, there was the Science Cita­", 0, (231, 633, 379, 645),
              font_size=9.4)
    b = Block("b", BlockKind.PARAGRAPH, "tion Index on CD-ROM from the Institute.", 0, (222, 643, 381, 656),
              font_size=9.2)
    a._nlines = b._nlines = 1  # (set by the detector when it builds blocks)
    [joined] = StructureDetector()._merge_across_breaks([a, b])
    assert joined.text == "Before 2000, there was the Science Citation Index on CD-ROM from the Institute."


def test_a_sentence_going_on_below_a_drop_cap_is_one_paragraph(isolated_home, tmp_path):
    rows = body_rows(80, 10) + [
        (71, 230, "ata are increasingly used to govern", 9.4), (71, 241, "science. Research evaluations that", 9.4),
        (71, 252, "were once bespoke and performed", 9.4), (43, 263, "by peers are now routine and reliant on", 9.4),
        (43, 274, "metrics. The problem is that evaluation is led.", 9.4)] + body_rows(300, 20)
    bl = load(tmp_path, [rows]).blocks
    assert "bespoke and performed by peers are now routine" in find(bl, "bespoke").text


def test_a_note_number_in_the_margin_goes_before_its_note():
    num = Block("n", BlockKind.PARAGRAPH, "23", 22, (11, 256, 18, 262), font_size=7)
    note = Block("t", BlockKind.PARAGRAPH, "House of Commons Agriculture Select Committee, 1988.", 22,
                 (23, 256, 376, 282), font_size=7)
    year = Block("y", BlockKind.PARAGRAPH, "12", 22, (11, 300, 18, 306), font_size=7)
    figures = Block("f", BlockKind.PARAGRAPH, "1988 figures follow in the table.", 22, (23, 300, 376, 310), font_size=7)
    out = StructureDetector()._join_markers([num, note, year, figures])
    assert [b.text for b in out] == ["23 House of Commons Agriculture Select Committee, 1988.", "12",
                                     "1988 figures follow in the table."]
    assert not out[0].styles  # a note number, not a raised mark


def _picture(w: int = 300, h: int = 200) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (90, 120, 200)).save(buf, "PNG")
    return buf.getvalue()


def test_the_number_of_a_page_that_is_only_a_picture_is_its_page_number(isolated_home, tmp_path):
    def add_picture_pages(doc):
        for n in (523, 524):
            page = doc.new_page(width=595, height=842)
            page.insert_image(pymupdf.Rect(150, 150, 450, 600), stream=_picture())
            page.insert_text((445, 660), str(n), fontsize=10, fontname="lib", fontfile=str(FONT))
    doc = load(tmp_path, [body_rows(80, 50)], extra=add_picture_pages)
    numbers = [b for b in doc.blocks if b.text.strip() in ("523", "524")]
    assert numbers and all(b.kind == BlockKind.FURNITURE for b in numbers)


def test_a_publisher_badge_on_the_first_page_is_decorative(isolated_home, tmp_path):
    def add_badges(doc):
        page = doc[0]
        page.insert_image(pymupdf.Rect(40, 280, 110, 340), stream=_picture(140, 120))
        page.insert_link({"kind": pymupdf.LINK_URI, "from": pymupdf.Rect(40, 300, 110, 320),
                          "uri": "http://crossmark.crossref.org/dialog/?doi=10.1371/x"})
        page.insert_image(pymupdf.Rect(300, 280, 370, 340), stream=_picture(140, 120))  # a picture without the link
    rows = body_rows(360, 30) + [(60, 100, "A title for the test document", 20)]
    doc = load(tmp_path, [rows], extra=add_badges)
    kinds = sorted((b.bbox[0] > 200, b.image.kind) for b in doc.blocks if b.image is not None)
    assert kinds == [(False, "decorative"), (True, "figure")]


def test_the_kind_of_article_above_the_title_is_small_print(isolated_home, tmp_path):
    rows = [(60, 70, "Original Research Article", 11, "hebo"), (60, 110, "Big Data and new epistemologies", 22),
            (60, 140, "Rob Kitchin", 11), (60, 180, "Introduction", 13, "hebo")] + body_rows(200, 40)
    bl = load(tmp_path, [rows]).blocks
    label = find(bl, "Original Research Article")
    assert label.kind == BlockKind.PARAGRAPH and label.font_size < 10
    assert find(bl, "Big Data and new").kind == BlockKind.TITLE
    assert find(bl, "Introduction").kind == BlockKind.HEADING


def test_a_scanned_table_is_read_row_by_row_but_scanned_prose_is_not_a_table():
    from dyslexia_converter.extract.ocr import OcrWord
    from dyslexia_converter.extract.pdf_reader import _ocr_tables

    def word(text, x, y, block, line):  # at 200 dpi: a 10 pt word is about 20 pixels high
        return OcrWord(text, (x, y, x + 14 * len(text), y + 20), 90.0, block, 1, line)

    rows = [("Name", "Role", "Office"), ("Anna", "Editor", "2.14"), ("Bram", "Reviewer", "3.02"),
            ("Chen", "Author", "1.07")]
    words = [word(c, x, 300 + 40 * k, block=ci, line=k)  # OCR reads each column as a block of its own
             for k, row in enumerate(rows) for ci, (x, c) in enumerate(zip((200, 400, 600), row))]
    tables, used = _ocr_tables(words, 72 / 200, lambda r: None)
    assert [t.table.rows for t in tables] == [[list(r) for r in rows]] and len(used) == len(words)
    prose, text = [], (BODY + " " + BODY).split()
    for k in range(6):  # lines of running text: ordinary word spaces
        x = 200
        for w in text[k * 6:k * 6 + 6]:
            prose.append(word(w, x, 300 + 40 * k, 0, k))
            x += 14 * len(w) + 8
    assert _ocr_tables(prose, 72 / 200, lambda r: None) == ([], set())


def test_a_scanned_table_with_wrapped_cells_keeps_its_columns_apart():
    from dyslexia_converter.extract.ocr import OcrWord
    from dyslexia_converter.extract.pdf_reader import _ocr_tables

    words = []

    def line(y, cells, line_no, conf=95.0):
        """A printed line: per column (its left edge, its words); OCR reads it straight across."""
        for x, text in cells:
            for w in text.split():
                words.append(OcrWord(w, (x, y, x + 13 * len(w), y + 20), conf, 0, 1, line_no))
                x += 13 * len(w) + 8

    columns = (200, 700, 1200)  # at 200 dpi; the columns are a few points apart
    line(300, list(zip(columns, ("Type of Interview", "Characteristics", "Strengths"))), 0)
    body = [[("Informal", 0), ("Questions emerge", 1), ("Increases the", 2)],
            [("", 0), ("from the context", 1), ("salience of", 2)],
            [("", 0), ("and are asked", 1), ("questions", 2)],
            [("Guide approach", 0), ("Topics are", 1), ("The outline", 2)],
            [("", 0), ("specified", 1), ("helps", 2)]]
    for k, cells in enumerate(body):
        y = 350 + 28 * k + (12 if k >= 3 else 0)
        line(y, [(columns[c], t) for t, c in cells if t], k + 1)
    tables, _ = _ocr_tables(words, 72 / 200, lambda r: None)
    assert [t.table.rows for t in tables] == [[
        ["Type of Interview", "Characteristics", "Strengths"],
        ["Informal", "Questions emerge from the context and are asked", "Increases the salience of questions"],
        ["Guide approach", "Topics are specified", "The outline helps"]]]
    # columns of running text side by side, the ends of their sentences in a row, are no table
    words.clear()
    line(300, list(zip(columns, ("program?", "hard.", "program?"))), 0)
    prose = (BODY + " " + BODY + " " + BODY + " " + BODY).split()
    for k in range(5):  # six words a line in each column, as narrow columns of text have
        line(350 + 28 * k, [(x, " ".join(prose[(k * 3 + c) * 6:(k * 3 + c) * 6 + 6])) for c, x in enumerate(columns)],
             k + 1)
    assert _ocr_tables(words, 72 / 200, lambda r: None)[0] == []


def _ocr_line(words: list, y: int, cells: list, line_no: int, conf: float = 95.0) -> None:
    """A printed line on a page scanned at 200 dpi: per column (its left edge, its words), read straight across."""
    from dyslexia_converter.extract.ocr import OcrWord
    for x, text in cells:
        for w in text.split():
            words.append(OcrWord(w, (x, y, x + 13 * len(w), y + 20), conf, 0, 1, line_no))
            x += 13 * len(w) + 8


def test_a_scanned_table_beside_a_column_of_text_leaves_the_text_out():
    """A table in the right-hand column of a two-column page: the lines of the left-hand column level with it are
    not a column of the table, and the heading below the table is not a row of it."""
    from dyslexia_converter.extract.pdf_reader import _ocr_tables
    words: list = []
    prose = (BODY + " " + BODY + " " + BODY).split()
    for k in range(13):  # the left-hand column: justified lines of six words, 12 pt apart
        line = prose[k * 6:k * 6 + 6]
        x = 650 - sum(13 * len(w) + 8 for w in line) + 8
        _ocr_line(words, 905 + 33 * k, [(x, " ".join(line))], 100 + k)
    columns = (850, 1100, 1300)  # the table, set in from the right-hand column's edge (760)
    _ocr_line(words, 987, list(zip(columns, ("Condition", "Time", "Accuracy"))), 0)
    for k, row in enumerate((("Standard", "61.2", "0.84"), ("Spacious", "55.9", "0.85"), ("Wide", "58.4", "0.83"))):
        _ocr_line(words, 1037 + 40 * k, list(zip(columns, row)), 1 + k)
    _ocr_line(words, 1190, [(760, "4 Discussion")], 10)
    _ocr_line(words, 1235, [(760, "The present findings suggest that simple changes help")], 11)
    tables, used = _ocr_tables(words, 72 / 200, lambda r: None)
    assert [t.table.rows for t in tables] == [[["Condition", "Time", "Accuracy"], ["Standard", "61.2", "0.84"],
                                               ["Spacious", "55.9", "0.85"], ["Wide", "58.4", "0.83"]]]
    assert {w.text for w in words if id(w) in used} == {"Condition", "Time", "Accuracy", "Standard", "Spacious", "Wide",
                                                        "61.2", "55.9", "58.4", "0.84", "0.85", "0.83"}


def test_a_scanned_table_with_headings_over_groups_of_columns():
    """Headings over two lines with a label over each group of columns (and labels set midway between the lines):
    the columns under a group stay apart, and every line of values is a row."""
    from dyslexia_converter.extract.pdf_reader import _ocr_tables
    words: list = []
    x = (200, 420, 560, 700, 840, 980, 1120, 1260)
    _ocr_line(words, 300, [(477, "Vision"), (744, "Language"), (1037, "Audio")], 0)
    _ocr_line(words, 316, [(x[0], "Method"), (x[7], "Avg.")], 1)
    _ocr_line(words, 334, list(zip(x[1:7], ("Top-1", "Top-5", "BLEU", "PPL", "WER", "CER"))), 2)
    values = (("Baseline", "71.2", "90.1", "27.3", "18.4", "9.1", "3.2", "36.6"),
              ("Wide", "73.5", "91.0", "28.1", "17.2", "8.7", "3.0", "37.6"),
              ("Deep", "74.0", "91.8", "29.4", "16.9", "8.5", "2.9", "38.3"))
    for k, row in enumerate(values):
        _ocr_line(words, 380 + 30 * k, list(zip(x, row)), 3 + k)
    tables, _ = _ocr_tables(words, 72 / 200, lambda r: None)
    assert [t.table.rows for t in tables] == [[["", "Vision", "", "Language", "", "Audio", "", ""],
                                               ["Method", "Top-1", "Top-5", "BLEU", "PPL", "WER", "CER", "Avg."]]
                                              + [list(r) for r in values]]


def test_labels_scattered_over_a_scanned_drawing_are_no_table():
    """Panel titles above a drawing and its labels a few points apart (not lines of text below each other): the
    words and confidences OCR gave for such a figure in a scanned article."""
    from dyslexia_converter.extract.ocr import OcrWord
    from dyslexia_converter.extract.pdf_reader import _ocr_tables
    k = 200 / 72  # points to pixels at 200 dpi
    printed = [(492.6, [("A)", 84, 93, 96), ("Current", 143, 177, 96), ("Driven", 180, 209, 96),
                        ("Extraction", 212, 258, 96), ("B)", 303, 313, 92), ("Donnan", 351, 386, 96),
                        ("Dialysis", 389, 424, 96)]),
               (512.2, [("[CEM", 158, 180, 77), ("Feed", 314, 334, 90), ("[CEM", 345, 368, 68)]),
               (515.5, [("(Feed", 114, 147, 37), ("Cathode", 186, 216, 95), ("cove", 257, 277, 92),
                        ("Cathode", 373, 409, 91), ("COV", 444, 459, 89)]),
               (518.9, [("thigher]", 77, 103, 41)]),
               (526.9, [("IK)", 225, 238, 23)])]
    words = [OcrWord(t, (x0 * k, (cy - 3) * k, x1 * k, (cy + 3) * k), conf, 0, 1, n)
             for n, (cy, line) in enumerate(printed) for t, x0, x1, conf in line]
    assert _ocr_tables(words, 1 / k, lambda r: None)[0] == []
