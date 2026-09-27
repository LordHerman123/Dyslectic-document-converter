"""Coloured highlights in focus mode: marking, erasing, surviving layout and text changes, saving."""
from dyslexia_converter import highlights as hl


def words_of(text, per_page=6, line=3):
    """Word list like the converted document gives: (page, text, [rect]) with lines of `line` words."""
    out = []
    for i, w in enumerate(text.split()):
        page, k = divmod(i, per_page)
        row, col = divmod(k, line)
        x0 = 50 + col * 60
        out.append((page, w, [(x0, 100 + row * 20, x0 + 50, 112 + row * 20)]))
    return out


TEXT = "one two three four five six seven eight nine ten eleven twelve"


def test_mark_erase_and_recolour():
    words = words_of(TEXT)
    hs = hl.add([], 1, 3, "yellow", words)
    assert [(h.start, h.end, h.colour, h.words) for h in hs] == [(1, 3, "yellow", "two three four")]
    hs = hl.add(hs, 3, 5, "blue", words)  # overlapping: the new colour wins where they meet
    assert [(h.start, h.end, h.colour) for h in hs] == [(1, 2, "yellow"), (3, 5, "blue")]
    hs = hl.erase(hs, 2, 3, words)  # the middle of both
    assert [(h.start, h.end, h.colour) for h in hs] == [(1, 1, "yellow"), (4, 5, "blue")]
    hs = hl.add(hs, 5, 4, "green", words)  # dragged backwards
    assert [(h.start, h.end, h.colour) for h in hs] == [(1, 1, "yellow"), (4, 5, "green")]
    assert hl.erase(hs, 0, 11, words) == []


def test_marks_become_one_band_per_line_and_stay_on_their_page():
    words = words_of(TEXT)
    hs = hl.add([], 1, 7, "pink", words)  # two..eight: lines on page 0 and page 1
    p0 = hl.page_marks(hs, words, 0)
    assert len(p0) == 2  # "two three" and "four five six" as two bands, not five boxes
    assert all(c == hl.COLOURS["pink"] for _, c in p0)
    first = p0[0][0]
    assert first[0] == 110 and first[2] == 220  # from "two" to "three" in one piece
    assert len(hl.page_marks(hs, words, 1)) == 1  # "seven eight"
    assert hl.page_marks(hs, words, 5) == []


def test_highlights_follow_their_words_when_the_text_shifts():
    words = words_of(TEXT)
    hs = hl.add([], 4, 5, "yellow", words)  # "five six"
    shifted = words_of("zero [12] " + TEXT)  # two words were added in front (a citation number)
    assert hl.resolve(hs[0], shifted) == (6, 7)
    assert hl.resolve(hs[0], words_of("completely different text now")) is None  # gone: not shown
    # a new layout (more words per page): same word numbers, other pages
    relaid = words_of(TEXT, per_page=12, line=4)
    assert hl.resolve(hs[0], relaid) == (4, 5) and len(hl.page_marks(hs, relaid, 0)) == 1


def test_word_at_a_point():
    pw = hl.words_on_page(words_of(TEXT), 0)
    assert hl.word_at(pw, 75, 105) == 0 and hl.word_at(pw, 140, 125) == 4
    assert hl.word_at(pw, 400, 106) == 2  # right of the line: its last word
    assert hl.word_at([], 1, 1) is None


def test_saved_per_document(tmp_path):
    store = hl.HighlightStore(tmp_path / "h.json")
    words = words_of(TEXT)
    store.save("doc-a", hl.add([], 0, 1, "green", words))
    store.save("doc-b", hl.add([], 2, 2, "blue", words))
    assert [h.words for h in store.load("doc-a")] == ["one two"]
    assert [h.colour for h in store.load("doc-b")] == ["blue"]
    store.save("doc-a", [])
    assert store.load("doc-a") == [] and store.load("doc-b")
    (tmp_path / "h.json").write_text("{not json", encoding="utf-8")  # damaged file: start afresh
    assert store.load("doc-b") == []
    (tmp_path / "h.json").write_text('{"doc-c": [{"start": "x"}, {"start": 1, "end": 2, "colour": "pink"}]}',
                                     encoding="utf-8")
    assert [(h.start, h.end) for h in store.load("doc-c")] == [(1, 2)]


def test_document_key_depends_on_content_only(tmp_path):
    a, b, c = tmp_path / "a.pdf", tmp_path / "b.pdf", tmp_path / "c.pdf"
    a.write_bytes(b"%PDF same")
    b.write_bytes(b"%PDF same")
    c.write_bytes(b"%PDF other")
    assert hl.document_key(a) == hl.document_key(b) != hl.document_key(c)


def test_highlights_go_into_the_exported_pdf():
    import pymupdf

    from dyslexia_converter import highlights as hl
    from dyslexia_converter.speech import reading_units

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "The quick brown fox jumps over the lazy dog.", fontsize=12)
    page.insert_text((72, 130), "A second line of text to read.", fontsize=12)
    pdf = doc.tobytes()
    words = hl.document_words(reading_units(pdf))
    marks = hl.add([], 1, 3, "green", words)  # quick brown fox
    out = hl.apply_to_pdf(pdf, marks)
    out_doc = pymupdf.open(stream=out, filetype="pdf")
    out_page = out_doc[0]
    annots = list(out_page.annots())
    assert len(annots) == 1 and annots[0].type[1] == "Highlight"
    r = annots[0].rect
    covered = [t for x0, y0, x1, y1, t, *_ in out_page.get_text("words")
               if min(x1, r.x1) - max(x0, r.x0) > 2 and min(y1, r.y1) - max(y0, r.y0) > 2]
    assert covered == ["quick", "brown", "fox"]
    green = annots[0].colors["stroke"]
    assert green[1] > green[0] and green[1] > green[2]
    plain = pymupdf.open(stream=hl.apply_to_pdf(pdf, []), filetype="pdf")
    assert not list(plain[0].annots())
