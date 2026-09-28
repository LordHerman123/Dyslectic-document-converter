"""Local conversion rules that make common layouts come out right without AI: publisher mastheads, affiliation
marks, large bullets, page numbers in wide margins, letter-spaced footers, dashes at a line start, "(cont)"
labels, figure DOIs, repeated headers that OCR reads a little differently, and text wrapped around a pull quote.
Each test also checks the case the rule must leave alone."""
from dataclasses import dataclass
from pathlib import Path

import pymupdf

from dyslexia_converter import pipeline
from dyslexia_converter.extract.layout import untangle
from dyslexia_converter.model import BlockKind
from dyslexia_converter.structure.detector import _dash_goes_on, _norm_furniture

BODY = ("The results of the study show that the method works well for most of the documents that were "
        "tested in this")


FONT = Path(__file__).resolve().parents[1] / "dyslexia_converter" / "assets" / "fonts" / "LiberationSans-Regular.ttf"


def make_pdf(path, pages) -> None:
    """``pages``: per page a list of (x, y, text, size); text is written left to right from (x, y) in a font with
    dashes and bullets."""
    doc = pymupdf.open()
    for rows in pages:
        page = doc.new_page(width=595, height=842)
        for x, y, text, size in rows:
            page.insert_text((x, y), text, fontsize=size, fontname="lib", fontfile=str(FONT))
    doc.save(str(path))


def body_rows(y0: float, n: int, x: float = 60, size: float = 10) -> list:
    """``n`` lines of ordinary running text from height ``y0``."""
    return [(x, y0 + 12.5 * i, f"Line {i} of the text: " + BODY[: 70], size) for i in range(n)]


def blocks(tmp_path, pages, name="doc.pdf"):
    path = tmp_path / name
    make_pdf(path, pages)
    return pipeline.load(path, use_ocr=False).document.blocks


def find(bl, text):
    return next(b for b in bl if text in b.text)


def test_publisher_masthead_is_not_the_title(isolated_home, tmp_path):
    rows = [(200, 60, "Contents lists available at ScienceDirect", 8),
            (240, 85, "Journal of Tests", 14),
            (180, 115, "journal homepage: www.elsevier.com/locate/jot", 8),
            (60, 170, "Reading order in converted documents", 13),
            (60, 195, "Ann Author, Bob Writer", 10.5)] + body_rows(240, 30)
    bl = blocks(tmp_path, [rows, body_rows(80, 40)])
    assert find(bl, "Reading order in converted").kind == BlockKind.TITLE
    for t in ("Contents lists available", "Journal of Tests", "journal homepage"):
        assert find(bl, t).kind == BlockKind.FURNITURE


def test_affiliation_mark_joins_its_line(isolated_home, tmp_path):
    rows = [(60, 100, "A Study of Things", 14), (60, 125, "Ann Author", 10.5),
            (60, 148, "b", 4.5), (63, 150, "Department of Tests, Example University, Utrecht", 6.4)] + \
        body_rows(200, 30)
    bl = blocks(tmp_path, [rows])
    aff = find(bl, "Department of Tests")
    assert aff.text.startswith(("b Department", "bDepartment"))  # a line of its own, or a superscript in the line
    assert not any(b.text == "b" for b in bl)


def test_lone_mark_block_joins_the_block_beside_it():
    from dyslexia_converter.model import Block
    from dyslexia_converter.structure.detector import StructureDetector

    mark = Block("m", BlockKind.PARAGRAPH, "b", 0, (33, 218, 35, 222), font_size=4.5)
    aff = Block("a", BlockKind.PARAGRAPH, "University of Exeter, Exeter, UK", 0, (37, 218, 241, 225), font_size=6.4)
    lone = Block("n", BlockKind.PARAGRAPH, "c", 0, (33, 300, 35, 304), font_size=4.5)
    far = Block("f", BlockKind.PARAGRAPH, "Text far below the letter", 0, (37, 400, 241, 407), font_size=6.4)
    out = StructureDetector()._join_markers([mark, aff, lone, far])
    assert [b.text for b in out] == ["b University of Exeter, Exeter, UK", "c", "Text far below the letter"]
    assert out[0].styles[0].superscript and out[0].styles[0].end == 1


def test_large_bullet_does_not_make_a_heading(isolated_home, tmp_path):
    rows = [(60, 100, "HIGHLIGHTS", 7)]
    for k, (a, b) in enumerate([("Hydrogen recycling electrochemical", "system was used for removal."),
                                ("Donnan dialysis improved the", "recovery of ammonia.")]):
        y = 120 + 30 * k
        rows += [(60, y + 2, "•", 15), (68, y, a, 7.2), (68, y + 9, b, 7.2)]
    rows += body_rows(200, 30)
    bl = blocks(tmp_path, [rows])
    item = find(bl, "Hydrogen recycling")
    assert item.kind == BlockKind.LIST_ITEM and "system was used for removal." in item.text
    assert not any(b.kind in (BlockKind.HEADING, BlockKind.TITLE) and "Hydrogen" in b.text for b in bl)


def test_page_number_in_a_wide_margin(isolated_home, tmp_path):
    pages = [body_rows(80, 45) + [(290, 0.86 * 842, str(121 + i), 10)] for i in range(3)]
    bl = blocks(tmp_path, pages)
    for i in range(3):
        assert find(bl, str(121 + i)).kind == BlockKind.FURNITURE
    # a number at the end of a line of text is text
    bl = blocks(tmp_path, [body_rows(80, 30) + [(60, 80 + 12.5 * 30, "12", 10)]], "b.pdf")
    assert all(b.kind != BlockKind.FURNITURE for b in bl)


def test_letter_spaced_journal_footer_but_not_a_formula(isolated_home, tmp_path):
    pages = [body_rows(80, 40) + [(60, 820, "4 2 6 | N A T U R E | V O L 4 9 5", 7)],
             body_rows(80, 40) + [(200, 820, "Wx = W y = W E = 0,", 10)]]
    bl = blocks(tmp_path, pages)
    assert find(bl, "N A T U R E").kind == BlockKind.FURNITURE
    assert find(bl, "Wx = W y").kind != BlockKind.FURNITURE


def test_dash_at_a_line_start_goes_on_but_a_list_stays(isolated_home, tmp_path):
    rows = [(60, 100, "Publishers earned 9 billion dollars and published about 1.8 million articles", 10),
            (60, 112.5, "— an average revenue per article of roughly 5,000 dollars. Analysts expect", 10),
            (60, 125, "margins of 20 to 30 per cent for the industry as a whole in the coming years.", 10),
            (60, 160, "From the second equation we can conclude that,", 10),
            (60, 172.5, "– if a = 1, then the map is the identity;", 10),
            (60, 185, "– if a = 2, then the map doubles every length.", 10)] + body_rows(220, 25)
    bl = blocks(tmp_path, [rows])
    para = find(bl, "an average revenue")
    assert para.kind == BlockKind.PARAGRAPH and para.text.startswith("Publishers earned")
    assert find(bl, "if a = 1").kind == BlockKind.LIST_ITEM


def test_dash_rules():
    assert _dash_goes_on("", "— an average revenue")
    assert _dash_goes_on("", "– based on some criteria – that seemingly offer")
    assert _dash_goes_on("the approach – which is new", "– makes little sense")
    assert not _dash_goes_on("we conclude that,", "– if a = 1, then:")
    assert not _dash_goes_on("", "- a plain list item")


def test_continued_label_is_furniture(isolated_home, tmp_path):
    pages = [body_rows(80, 40), [(60, 50, "(cont).", 9)] + body_rows(80, 40)]
    bl = blocks(tmp_path, pages)
    assert find(bl, "(cont)").kind == BlockKind.FURNITURE


def test_figure_doi_joins_its_caption(isolated_home, tmp_path):
    rows = body_rows(80, 20) + [(60, 400, "Fig 1. Share of papers by publisher, 1973-2013.", 9),
                                (60, 412, "doi:10.1371/journal.pone.0127502.g001", 9)] + body_rows(450, 20)
    bl = blocks(tmp_path, [rows])
    cap = find(bl, "Fig 1. Share")
    assert cap.kind == BlockKind.CAPTION and cap.text.endswith("pone.0127502.g001")


def test_repeated_headers_match_despite_numbers_and_marks():
    assert _norm_furniture("290 B. Wynne") == _norm_furniture("B. Wynne 291")
    assert _norm_furniture("CHAPTER 6 « Science, Values") == _norm_furniture("CHAPTER 6 » Science, Values")
    assert _norm_furniture("Page 3") == _norm_furniture("Page 4") != _norm_furniture("Chapter 4")
    assert _norm_furniture("NEWS FEATURE") == _norm_furniture("FEATURE NEWS")


@dataclass
class L:
    size: float
    bbox: tuple
    text: str
    font: str = "body"


def test_text_wrapped_around_a_pull_quote_is_untangled():
    rows = [(9.4, (216, 202, 375, 215), "relate clearly to those goals. The choice of"),
            (9.4, (216, 213, 292, 225), "indicators, and the"), (10.2, (301, 220, 355, 234), "“Simplicity"),
            (9.4, (216, 223, 292, 236), "ways in which they"), (10.2, (301, 231, 358, 245), "is a virtue in"),
            (9.3, (216, 234, 292, 246), "are used, should take"), (10.2, (301, 242, 358, 256), "an indicator"),
            (9.4, (216, 244, 292, 257), "into account the"), (10.2, (301, 253, 349, 267), "because it"),
            (9.4, (216, 255, 290, 267), "wider contexts."), (10.2, (301, 264, 346, 278), "enhances"),
            (9.4, (216, 265, 292, 278), "Scientists have"), (10.2, (301, 275, 371, 289), "transparency.”"),
            (9.4, (216, 276, 292, 288), "diverse missions."), (9.4, (216, 287, 375, 299), "Research that...")]
    lines = [L(s, b, t, "quote" if s > 10 else "body") for s, b, t in rows]
    text = " ".join(l.text for l in untangle(lines))
    assert "The choice of indicators, and the ways in which they are used, should take into account the wider " \
           "contexts. Scientists have diverse missions." in text
    assert "“Simplicity is a virtue in an indicator because it enhances transparency.” Research" in text


def test_two_columns_of_the_same_type_are_left_to_the_column_check():
    lines = [L(10, (60, 100 + 12 * i, 290, 110 + 12 * i), f"left {i}") if k == 0 else
             L(10, (300, 100 + 12 * i, 550, 110 + 12 * i), f"right {i}") for i in range(4) for k in range(2)]
    assert untangle(lines) == lines


class Ordering:
    """Stands in for the AI: gives the pieces in reverse order."""
    model = "stand-in"

    def complete_json(self, system, prompt, schema, max_tokens=1024, answer_hint=""):
        from dyslexia_converter.ai.providers import Reply

        n = len(prompt.splitlines())
        return Reply({"o": list(range(n))[::-1]}, "{}", 10, 5)


def test_ai_order_for_a_page_the_check_flagged_keeps_other_edits_and_undoes(isolated_home, tmp_path, monkeypatch):
    from dyslexia_converter import check
    from dyslexia_converter.ai import assistant as assistant_mod
    from dyslexia_converter.model import Correction
    from dyslexia_converter.ai.keystore import KeyStore
    from dyslexia_converter.settings import AISettings, FormatSettings

    path = tmp_path / "two.pdf"
    make_pdf(path, [[(60, 100, "Second part of the story comes here and it ends the page.", 10),
                     (60, 400, "First part of the story is printed lower down on the page.", 10)],
                    body_rows(80, 10)])
    session = pipeline.load(path, use_ocr=False)
    settings = FormatSettings()
    doc = session.document
    first = find(doc.blocks, "Second part")
    other = find(doc.blocks, "Line 3 of the text")
    session.check_findings = [check.Finding(f"{first.id}:order:0", "order", first.id, 1, "Second part")]
    at = other.text.index("Line 3")
    c = Correction("c1", other.id, at, at + 6, "Line 3", "Line 3", 1.0)
    session.edit_text(c, session.editable_sentence(c).replace("Line 3", "Line three"))
    ks = KeyStore()
    ks._keyring = False
    ks.set("mistral", "test-key-000000000")
    monkeypatch.setattr(assistant_mod, "make_provider", lambda *a, **k: Ordering())
    ai = assistant_mod.AIAssistant(AISettings(mode="ai_assisted", consent_given=True), ks)

    def page1():
        return [b.text[:6] for b in session.document.blocks if b.page == 0 and b.kind == BlockKind.PARAGRAPH]

    assert page1() == ["Second", "First "]
    assert session.reorder_page(session.check_findings[0].id, ai, settings) == 0
    assert page1() == ["First ", "Second"]
    assert session.check_findings == []  # the finding was about text that moved
    text = " ".join(it.text for it in session.compose(settings).items)
    assert "Line three of the text" in text  # the reader's edit on page 2 is kept
    session.undo_reorder(0, settings)
    assert page1() == ["Second", "First "]
    assert "Line three of the text" in " ".join(it.text for it in session.compose(settings).items)
