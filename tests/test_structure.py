from dyslexia_converter import pipeline
from dyslexia_converter.model import BlockKind


def kinds(doc, kind):
    return [b for b in doc.blocks if b.kind == kind]


def test_detects_text_pdf_and_structure(paper):
    doc = pipeline.load(paper).document
    assert doc.pdf_type == "text" and not doc.ocr_used
    assert kinds(doc, BlockKind.TITLE)[0].text == "Typography and Reading Speed in Academic Texts"
    assert "Anna de Vries" in kinds(doc, BlockKind.AUTHORS)[0].text
    headings = [(b.level, b.text) for b in kinds(doc, BlockKind.HEADING)]
    assert (1, "1 Introduction") in headings
    assert (2, "2.1 Participants") in headings
    assert (1, "References") in headings


def test_reading_order_follows_columns(paper):
    doc = pipeline.load(paper).document
    texts = [b.text for b in doc.blocks if b.kind in (BlockKind.HEADING, BlockKind.PARAGRAPH)]
    order = [next(i for i, t in enumerate(texts) if t.startswith(p)) for p in
             ("1 Introduction", "Reading difficulties", "2 Methods", "3 Results", "Reading times", "4 Discussion")]
    assert order == sorted(order)


def test_footnotes_references_tables_captions(paper):
    doc = pipeline.load(paper).document
    notes = kinds(doc, BlockKind.FOOTNOTE)
    assert [n.footnote_label for n in notes] == ["1", "2"]
    refs = kinds(doc, BlockKind.REFERENCE)
    assert len(refs) == 4 and refs[-1].text.startswith("[4] Smith")
    table = kinds(doc, BlockKind.TABLE)[0].table
    assert table.rows[0] == ["Condition", "Time (s)", "Accuracy"]
    assert table.rows[2][1] == "55.9"
    captions = kinds(doc, BlockKind.CAPTION)
    assert all(c.caption_for for c in captions)
    assert kinds(doc, BlockKind.IMAGE), "the vector chart must be kept as an image"
    furniture = {b.text for b in kinds(doc, BlockKind.FURNITURE)}
    assert "Journal of Reading Studies - Vol. 3" in furniture


def test_paragraph_split_across_columns_is_joined(paper):
    doc = pipeline.load(paper).document
    para = next(b for b in doc.blocks if b.text.startswith("In addition, each participant"))
    assert para.text.endswith("for the procedure).")


def test_page_range(paper):
    doc = pipeline.load(paper, pages=(2, 2)).document
    assert [p.source_page for p in doc.pages] == [1]  # only the second PDF page was read
    assert any("[4] Smith, J. (2020)" in b.text for b in doc.blocks)


def test_ocr_junk_around_a_line_end_hyphen():
    from dyslexia_converter.structure.detector import StructureDetector
    from dyslexia_converter.transform.spelling import Dictionary, dehyphenator, word_rejoiner

    d = Dictionary(["en"])
    det = StructureDetector(dehyphenator(d), word_rejoiner(d))
    assert det._junk_hyphen("known causal mecha-", "“nisms that") == ("known causal mecha", 1)
    assert det._junk_hyphen("leads to the mal--.", "function of") == ("leads to the mal", 0)
    assert det._junk_hyphen("strategy for cli-", "- mate deniers") == ("strategy for cli", 2)
    assert det._junk_hyphen("a well-", "known fact") is None  # no junk: the normal rules decide
    assert det._junk_hyphen("the self-", "“Upper case") is None
    assert det._junk_hyphen("no hyphen", "“quote") is None
