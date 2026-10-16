"""Numbers in scanned tables that text recognition may have misread: flagged for the reader to check against the
original (never changed), marked in focus mode, and correctable like any word."""
from dyslexia_converter import highlights as hl
from dyslexia_converter import pipeline, quality, speech
from dyslexia_converter.extract.ocr import OcrWord
from dyslexia_converter.extract.pdf_reader import _doubtful_cells, _ocr_tables
from dyslexia_converter.model import Block, BlockKind, Document, PageInfo, TableData, table_rows, table_text
from dyslexia_converter.render import pdf_writer
from dyslexia_converter.render.compose import compose
from dyslexia_converter.settings import FormatSettings
from dyslexia_converter.transform.spelling import CustomWords


def _line(words: list, y: int, cells: list, line_no: int, conf: dict | None = None) -> None:
    """A printed line on a page scanned at 200 dpi: per column (its left edge, its words), read straight across;
    ``conf``: the confidence of some of its words (95 otherwise)."""
    for x, text in cells:
        for w in text.split():
            words.append(OcrWord(w, (x, y, x + 13 * len(w), y + 20), (conf or {}).get(w, 95.0), 0, 1, line_no))
            x += 13 * len(w) + 8


def test_numbers_unlike_their_column_are_flagged():
    rows = [["Method", "WER", "CER", "Params", "Note"],
            ["Baseline", "Ol", "3.2", "120", "fast"],
            ["Wide", "8.7", "3.0", "85", "slow"],
            ["Deep", "8.5", "29", "64", "slow"],
            ["Ours", "7.9", "2.6", "1500", "best"]]
    assert _doubtful_cells(rows, 1, {}) == {(1, 1): "number", (3, 2): "number"}  # "0.1"?, "2.9"?
    # a decimal point lost in a longer number; zero and one-digit numbers are left alone
    assert _doubtful_cells([["A"], ["29.1"], ["291"], ["15.8"], ["0"], ["7"]], 1, {}) == {(2, 0): "number"}
    # decimals with a comma; thousands set apart by a comma are no decimals of other numbers
    assert _doubtful_cells([["A"], ["29,1"], ["158"], ["15,8"]], 1, {}) == {(2, 0): "number"}
    assert _doubtful_cells([["A"], ["1,234"], ["980"], ["12,500"]], 1, {}) == {}
    # a table of settings, one quantity per row: whole numbers in a row of whole numbers are no slip of a point
    settings = [["", "Cart-pole", "Swimmer", "Walker"], ["State dim.", "10", "12", "20"],
                ["Parameters", "364", "4806", "8206"], ["Step size", "0.01", "0.05", "0.02"]]
    assert _doubtful_cells(settings, 1, {}) == {}
    # results copied from other papers, rounded there: a row of whole numbers among rows with decimals
    results = [["Model", "TFD", "CIFAR-10"], ["NICE", "5514.71", "5371.78"], ["Deep MFA", "5250", "3622"],
               ["GRBM", "2413", "2365"]]
    assert _doubtful_cells(results, 1, {}) == {}
    # a column of words with a few numbers in it, and the headings, are not checked as numbers
    assert _doubtful_cells([["29"], ["fast"], ["12.5"], ["slow"], ["Ol"]], 1, {}) == {}
    assert _doubtful_cells([["Top-l1"], ["71.2"], ["73.5"], ["74.0"]], 1, {}) == {}
    # a word text recognition was unsure of, wherever it is
    assert _doubtful_cells([["Top-l1", "B"], ["71.2", "x"]], 1, {(0, 0): 41.0, (1, 1): 80.0}) == {(0, 0): "unclear"}


def test_a_scanned_table_flags_its_doubtful_cells_and_keeps_their_text():
    words: list = []
    columns = (200, 500, 700, 900)
    _line(words, 300, list(zip(columns, ("Method", "WER", "CER", "Avg."))), 0)
    values = (("Baseline", "Ol", "3.2", "36.6"), ("Wide", "8.7", "3.0", "37.6"), ("Deep", "8.5", "29", "38.3"),
              ("Ours", "7.9", "2.6", "392"))
    for k, row in enumerate(values):
        _line(words, 340 + 40 * k, list(zip(columns, row)), 1 + k, conf={"Wide": 30.0})
    [t] = [t.table for t in _ocr_tables(words, 72 / 200, lambda r: None)[0]]
    assert t.rows == [["Method", "WER", "CER", "Avg."]] + [list(r) for r in values]  # never changed
    assert t.unsure_cells == {(1, 1): "number", (2, 0): "unclear", (3, 2): "number", (4, 3): "number"}


def test_a_scanned_table_with_headings_over_groups_of_columns_flags_cells_too():
    words: list = []
    x = (200, 420, 560, 700, 840, 980, 1120, 1260)
    _line(words, 300, [(477, "Vision"), (744, "Language"), (1037, "Audio")], 0)
    _line(words, 316, [(x[0], "Method"), (x[7], "Avg.")], 1)
    _line(words, 334, list(zip(x[1:7], ("Top-l1", "Top-5", "BLEU", "PPL", "WER", "CER"))), 2, conf={"Top-l1": 40.0})
    values = (("Baseline", "71.2", "90.1", "27.3", "18.4", "Ol", "3.2", "36.6"),
              ("Wide", "73.5", "91.0", "28.1", "17.2", "8.7", "3.0", "37.6"),
              ("Deep", "74.0", "91.8", "29.4", "16.9", "8.5", "29", "38.3"),
              ("Ours", "76.8", "93.2", "291", "158", "7.9", "2.6", "39.2"))
    for k, row in enumerate(values):
        _line(words, 380 + 30 * k, list(zip(x, row)), 3 + k)
    [t] = [t.table for t in _ocr_tables(words, 72 / 200, lambda r: None)[0]]
    head = len(t.rows) - len(values)
    assert t.rows[head:] == [list(r) for r in values]
    top = next(ri for ri in range(head) if "Top-l1" in t.rows[ri])
    assert t.unsure_cells == {(top, 1): "unclear", (head, 5): "number", (head + 2, 6): "number",
                              (head + 3, 3): "number", (head + 3, 4): "number"}


def _table_doc() -> Document:
    rows = [["City", "Jan", "Feb"], ["Amsterdam", "3.4", "38"], ["Brussels", "3.3", "3.7"], ["Paris", "5.0", "5.6"]]
    table = TableData(rows, None, True, unsure_cells={(1, 2): "number"})
    blocks = [Block("p1", BlockKind.PARAGRAPH, "Mean temperatures in three cities.", page=0),
              Block("t1", BlockKind.TABLE, page=0, bbox=(72, 100, 400, 200), table=table)]
    return Document("scan.pdf", pages=[PageInfo(0, 595, 842, "scanned", ocr_used=True, text_source="ocr")],
                    blocks=blocks)


def test_a_flagged_cell_is_marked_where_it_is_in_the_converted_pdf():
    doc = _table_doc()
    settings = FormatSettings()
    pdf = pdf_writer.build_pdf(compose(doc, settings), settings)
    marks = pdf_writer.last_unsure_marks()
    assert [m[5] for m in marks] == ["number"]
    words = hl.document_words(speech.reading_units(pdf))
    [(page, [(first, last, why)])] = quality.parts_on_pages(words, marks).items()
    assert (hl.text_of(words, first, last), why) == ("38", "number")


def test_a_cell_is_corrected_like_any_word_and_then_no_longer_flagged(tmp_path):
    session = pipeline.Session(_table_doc(), CustomWords(tmp_path / "words.txt"))
    where = session.find_passage("38")
    assert where is not None and where[0] == "t1"
    assert session.passage_as_shown(*where) == "38"
    assert session.edit_passage(*where, "3.8") is not None
    result = compose(session.document, FormatSettings())
    [t] = [it.table for it in result.items if it.kind == "table"]
    assert t.rows[1] == ["Amsterdam", "3.4", "3.8"] and t.unsure_cells == {}
    assert session.document.block("t1").table.rows[1][2] == "38"  # the original reading is kept (undo)
    assert session.find_passage("3.8") == where  # found as shown
    # the correction is listed with its cell around it (OCR review), and can be retyped there
    [mine] = [c for c in session.document.corrections if c.source == "user"]
    assert session.correction_sentence(mine) == ("", "38", "") and session.editable_sentence(mine) == "3.8"
    again = session.edit_text(mine, "3.9")
    assert again is not None and (again.original, again.replacement) == ("38", "3.9")
    # words of two cells are corrected one cell at a time: a table is never torn apart
    two = session.find_passage("Brussels 3.3")
    assert two is not None and session.edit_passage(*two, "Brussels 33") is None


def test_a_table_text_that_lost_its_shape_keeps_the_cells():
    rows = [["a", "b"], ["c", "d"]]
    assert table_rows(table_text(rows), rows) == rows
    assert table_rows("a\tb\nc\td\te", rows) is rows and table_rows("a b\nc\td", rows) is rows
    assert table_rows("x\tb\nc\ty", rows) == [["x", "b"], ["c", "y"]]
