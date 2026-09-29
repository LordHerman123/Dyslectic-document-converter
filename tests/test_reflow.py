"""The reading view (text flowing to fit the window) and where each document was left."""
from dyslexia_converter import pipeline
from dyslexia_converter.settings import FormatSettings
from dyslexia_converter.ui.app import ConverterApp


def _app_with(paper) -> ConverterApp:
    app = ConverterApp(page=None)
    app.session = pipeline.load(paper, FormatSettings())
    app.source_path = str(paper)
    app.doc_key = "doc-1"
    return app


def test_read_aloud_words_point_at_their_place_in_the_text(paper):
    """Every word handed to the speech engine knows where it is in its paragraph, so the word being said can be
    marked in the text."""
    app = _app_with(paper)
    r = app.reflow
    r.result = app.session.compose(app.settings)
    r.items = r.result.items
    r._sentences()
    assert r._units and len(r._units) == len(r._unit_spans)
    for unit, spans in zip(r._units, r._unit_spans):
        text = r.plain(r.items[unit.page])
        for word, (a, b) in zip(unit.words, spans):
            assert text[a:b] == word.text
    # a sentence the engine gets is the words joined with single spaces, and word starts point into it
    first = r._units[0]
    assert all(first.text[w.start:w.start + len(w.text)] == w.text for w in first.words)


def test_reading_position_is_kept_per_document(paper):
    app = _app_with(paper)
    assert app.reading_position("reflow", 0) == 0
    app.save_reading_position("reflow", 12)
    app.save_reading_position("focus", 3)
    assert app.reading_position("reflow") == 12 and app.reading_position("focus") == 3
    app.doc_key = "doc-2"
    assert app.reading_position("reflow", 0) == 0  # another document starts at the beginning
    # the list stays bounded: the oldest documents are forgotten
    for n in range(app.POSITIONS_KEPT + 5):
        app.doc_key = f"many-{n}"
        app.save_reading_position("focus", n)
    assert len(app.ui["positions"]) == app.POSITIONS_KEPT
    app.doc_key = "doc-1"
    assert app.reading_position("focus", 0) == 0


def test_formula_pictures_are_read_as_their_text(paper):
    """A small formula picture inside a line is shown (and read) as its text in the reading view."""
    from dyslexia_converter.model import ImageData
    from dyslexia_converter.render.compose import RItem, Run

    app = _app_with(paper)
    r = app.reflow
    r.result = app.session.compose(app.settings)
    r.result.inline_images = {"": ImageData(b"", "png", 10, 10, kind="equation", alt="x^2")}
    item = RItem("paragraph", [Run("area  grows")])
    assert r.plain(item) == "area  x^2  grows"
