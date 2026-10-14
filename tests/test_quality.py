"""How far to trust a conversion: the ratings, the words to check, and where they are in the converted PDF."""
from conftest import needs_tesseract
from dyslexia_converter import highlights as hl
from dyslexia_converter import pipeline, quality, speech
from dyslexia_converter.model import Block, BlockKind, Correction, Document, OcrWordConfidence, PageInfo
from dyslexia_converter.render import pdf_writer
from dyslexia_converter.render.compose import compose
from dyslexia_converter.settings import FormatSettings
from dyslexia_converter.transform.spelling import CustomWords

KNOWN = {"the", "early", "state", "viewed", "its", "forests", "through", "fiscal", "lens", "revenue", "needs",
         "officials", "counted", "trees", "in", "sample", "plots", "careful", "measurement", "was", "made", "by"}


def known(word: str) -> bool:
    return word.lower() in KNOWN


def ocr_block(bid: str, text: str, confidences: list[float], page: int = 0) -> Block:
    """A paragraph read by OCR, one confidence per word."""
    spans, start = [], None
    for i, ch in enumerate(text + " "):
        if ch.isspace():
            if start is not None:
                spans.append((start, i))
                start = None
        elif start is None:
            start = i
    assert len(spans) == len(confidences)
    return Block(bid, BlockKind.PARAGRAPH, text, page=page, source="ocr",
                 ocr_confidence=[OcrWordConfidence(a, b, c) for (a, b), c in zip(spans, confidences)])


def scanned_doc(blocks: list[Block], pages: int = 1) -> Document:
    return Document("scan.pdf", pages=[PageInfo(i, 595, 842, "scanned", ocr_used=True, text_source="ocr")
                                       for i in range(pages)], blocks=blocks)


def test_text_pdf_is_excellent_with_nothing_to_check(paper):
    q = pipeline.load(paper).quality()
    assert q.document.level == quality.EXCELLENT
    assert all(r.level >= quality.HIGH for r in q.pages.values())
    assert not any(why in ("unclear", "unknown") for spans in q.unsure.values() for *_, why in spans)


def test_unsure_recognised_words_are_found_and_lower_the_rating():
    good = ocr_block("b1", "The early state viewed its forests through the fiscal lens of revenue needs.",
                     [96] * 13)
    poor = ocr_block("b2", "Officials counted trces in sarnple plots.", [95, 94, 41, 93, 82, 95])
    q = quality.assess(scanned_doc([good, poor]), known)
    found = [(poor.text[a:e], why) for a, e, why in q.unsure["b2"]]
    assert found == [("trces", "unclear"), ("sarnple", "unknown")]
    assert "b1" not in q.unsure
    assert q.document.level < quality.HIGH  # 2 uncertain of 19 recognised words
    assert ("unsure", 11) in q.document.reasons
    clean = quality.assess(scanned_doc([good]), known)
    assert clean.document.level == quality.HIGH and clean.unsure == {}


def test_a_corrected_word_is_no_longer_to_check():
    poor = ocr_block("b2", "Officials counted trces in sample plots.", [95, 94, 41, 82, 93, 95])
    doc = scanned_doc([poor])
    doc.corrections.append(Correction("c1", "b2", 18, 23, "trces", "trees", 1.0, status="accepted", source="user"))
    assert quality.assess(doc, known).unsure == {}


def test_a_sentence_split_over_two_paragraphs_is_marked():
    a = Block("a", BlockKind.PARAGRAPH, "Careful measurement was made by", page=0)
    b = Block("b", BlockKind.PARAGRAPH, "officials who counted trees.", page=0)
    doc = Document("x.pdf", pages=[PageInfo(0, 595, 842, "text")], blocks=[a, b])
    q = quality.assess(doc, known)
    assert q.unsure == {"a": [(29, 31, "split")], "b": [(0, 9, "split")]}


def test_the_words_to_check_are_marked_where_they_are_in_the_converted_pdf():
    poor = ocr_block("b2", "Officials counted trces in sample plots and the state viewed its forests.",
                     [95, 94, 41, 82, 93, 95, 96, 96, 96, 96, 96, 96])
    doc = scanned_doc([poor])
    q = quality.assess(doc, known)
    settings = FormatSettings()
    pdf = pdf_writer.build_pdf(compose(doc, settings, unsure=q.unsure), settings)
    marks = pdf_writer.last_unsure_marks()
    assert [m[5] for m in marks] == ["unclear"]
    words = hl.document_words(speech.reading_units(pdf))
    parts = quality.parts_on_pages(words, marks)
    [(page, [(first, last, why)])] = parts.items()
    assert (hl.text_of(words, first, last), why) == ("trces", "unclear")


def test_neighbouring_words_to_check_make_one_part():
    words = [(0, "a", [(10, 10, 20, 20)]), (0, "b", [(25, 10, 35, 20)]), (0, "c", [(40, 10, 50, 20)]),
             (1, "d", [(10, 10, 20, 20)])]
    marks = [(0, 24, 9, 36, 21, "unclear"), (0, 39, 9, 51, 21, "unclear"), (1, 9, 9, 21, 21, "split")]
    assert quality.parts_on_pages(words, marks) == {0: [(1, 2, "unclear")], 1: [(3, 3, "split")]}


@needs_tesseract
def test_a_session_rates_its_conversion_and_notes_the_marks(scanned, tmp_path):
    session = pipeline.load(scanned, custom_words=CustomWords(tmp_path / "words.txt"))
    q = session.quality()
    assert q.document.level <= quality.HIGH and ("ocr", 0) in q.document.reasons
    assert q.pages and set(q.by_source) <= {0, 1}
    session.export("pdf", FormatSettings())
    assert len(session.unsure_marks) <= sum(len(v) for v in q.unsure.values())
