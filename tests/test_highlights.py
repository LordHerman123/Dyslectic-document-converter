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


def _words(n=12):
    return [(0, f"w{i}", [(10.0 + 30 * (i % 6), 10.0 + 20 * (i // 6), 35.0 + 30 * (i % 6), 22.0 + 20 * (i // 6))])
            for i in range(n)]


def test_notes_stay_with_their_words():
    from dyslexia_converter import highlights as hl

    words = _words()
    hs = hl.add([], 2, 5, "yellow", words, "important")
    assert hl.at(hs, 3, words) == 0 and hl.at(hs, 7, words) is None
    hs = hl.recolour(hs, 0, "blue")
    assert hs[0].colour == "blue" and hs[0].note == "important"
    part = hl.erase(hs, 2, 2, words)  # a note stays with the part that is left
    assert [(h.start, h.end, h.note) for h in part] == [(3, 5, "important")]
    bigger = hl.add(hs, 1, 8, "pink", words)  # covering a noted highlight keeps its note
    assert bigger[0].note == "important"
    hs = hl.set_note(hs, 0, "  ")
    assert hs[0].note == ""
    assert hl.note_marks(hl.add([], 2, 5, "yellow", words, "n"), words, 0) == [(185.0, 10.0)]  # top right of the band


def test_lines_on_page():
    from dyslexia_converter import highlights as hl

    assert hl.lines_on_page(_words(), 0) == [(10.0, 22.0), (30.0, 42.0)]
    assert hl.lines_on_page(_words(), 1) == []


def test_notes_become_pdf_comments():
    import pymupdf

    from dyslexia_converter import highlights as hl
    from dyslexia_converter.speech import reading_units

    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((72, 100), "The quick brown fox jumps over the lazy dog.", fontsize=12)
    pdf = doc.tobytes()
    words = hl.document_words(reading_units(pdf))
    out = hl.apply_to_pdf(pdf, hl.add([], 1, 2, "yellow", words, "Remember this"))
    out_doc = pymupdf.open(stream=out, filetype="pdf")
    out_page = out_doc[0]
    annots = list(out_page.annots())
    assert annots[0].info["content"] == "Remember this"


def test_store_keeps_notes(tmp_path):
    from dyslexia_converter import highlights as hl

    store = hl.HighlightStore(tmp_path / "h.json")
    store.save("k", [hl.Highlight(1, 2, "green", "a b", "my note")])
    assert store.load("k")[0].note == "my note"


def test_page_tints_ruler_and_note_signs():
    import io

    import pymupdf
    from PIL import Image

    from dyslexia_converter.render import preview

    doc = pymupdf.open()
    doc.new_page().insert_text((72, 100), "Some text on a line.", fontsize=12)
    pdf = doc.tobytes()

    def pixel(**kw):
        png = preview.render_highlight(pdf, 0, 300, [], [], **kw)
        return Image.open(io.BytesIO(png)).convert("RGB").getpixel((5, 5))

    assert pixel() == (255, 255, 255)
    assert pixel(tint="cream") == preview.TINTS["cream"]
    assert max(pixel(tint="dark")) < 60
    ink = preview.render_highlight(pdf, 0, 300, [], [], ruler=(200.0, 212.0))  # text away from the ruler
    plain = preview.render_highlight(pdf, 0, 300, [], [])
    darkest = lambda png: Image.open(io.BytesIO(png)).convert("L").crop((30, 40, 150, 56)).getextrema()[0]  # noqa
    assert darkest(ink) > darkest(plain) + 60  # is faded
    assert preview.render_highlight(pdf, 0, 300, [], [], notes=[(100.0, 90.0)], picked=[(72, 90, 120, 102)])
