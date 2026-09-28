"""The unusual-layout check, the pieces of a page for the optional AI layout check, the AI's order, and drop
caps."""
from dataclasses import dataclass

from dyslexia_converter.ai.assistant import checked_order
from dyslexia_converter.extract.layout import interleaved, pieces, reading_order
from dyslexia_converter.extract.pdf_reader import _join_drop_caps, _Span

PROSE = "words that make up an ordinary line of running text here"


@dataclass
class Line:
    """A text line as the layout functions see it."""
    text: str
    bbox: tuple
    block_no: int = 0
    size: float = 9.0


@dataclass
class Picture:
    """A figure (no text)."""
    bbox: tuple


def two_columns(n: int = 8, box_across: bool = False) -> list:
    """Two columns of prose (left block 1, right block 2), optionally with a box across the column gap."""
    items = [Line(f"left {i} {PROSE}", (40, 100 + 12 * i, 290, 110 + 12 * i), 1) for i in range(n)]
    items += [Line(f"right {i} {PROSE}", (300, 100 + 12 * i, 550, 110 + 12 * i), 2) for i in range(n)]
    if box_across:
        items.append(Picture((250, 130, 340, 170)))
    return items


def test_normal_columns_are_not_flagged():
    assert not interleaved(reading_order(two_columns()))


def test_mixed_up_columns_are_flagged():
    rows = sorted(two_columns(), key=lambda it: (it.bbox[1], it.bbox[0]))  # read straight across: mixed up
    assert interleaved(rows)


def test_short_text_side_by_side_is_not_flagged():
    labels = [Line(w, (40 + 60 * k, 100 + 12 * i, 90 + 60 * k, 110 + 12 * i)) for i in range(6) for k, w in
              enumerate(["2019", "12.4", "n = 30"])]
    assert not interleaved(sorted(labels, key=lambda it: (it.bbox[1], it.bbox[0])))


def test_pieces_keep_each_column_together_even_when_the_order_is_mixed():
    items = two_columns(box_across=True)
    ps = pieces(items)
    texts = [[it.text for it in p] for p in ps if isinstance(getattr(p[0], "text", None), str)]
    assert sorted(len(t) for t in texts) == [8, 8]
    for t in texts:  # top to bottom within a piece
        assert [int(x.split()[1]) for x in t] == list(range(8))
    assert sum(1 for p in ps for it in p) == len(items)  # every item exactly once


def test_checked_order_keeps_every_piece_once():
    assert checked_order([2, 0, 1], 3) == [2, 0, 1]
    assert checked_order([1], 3) == [1, 0, 2]  # left out: added in the local order
    assert checked_order([0, 0, 1], 3) is None  # repeated
    assert checked_order([0, 5], 3) is None  # unknown
    assert checked_order("0,1,2", 3) is None


def boxed_pdf(path) -> None:
    """A page with two columns of numbered sentences and a box across the gap between them (like a magazine)."""
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    for i in range(24):
        y = 130 + 13 * i
        # full columns (40-290 and 300-555); next to the box both columns make room for it
        beside = 8 <= i < 14
        left = f"Left column sentence {i} runs on" + ("" if beside else " to fill the whole line")
        page.insert_text((40, y), left + ".", fontsize=9)
        page.insert_text((355 if beside else 300, y), f"Right column sentence {i} runs on to fill the line.",
                         fontsize=9)
    page.draw_rect((245, 222, 350, 300), color=(0, 0, 0), fill=(0.9, 0.9, 0.6))
    for k, words in enumerate(["BOX: Subscribe", "today and save", "thirty per cent"]):
        page.insert_text((252, 245 + 16 * k), words, fontsize=12)
    doc.save(str(path))


class Answering:
    """Stands in for the AI: gives a fixed answer."""
    model = "stand-in"

    def __init__(self, answer):
        self.answer = answer

    def complete_json(self, system, prompt, schema, max_tokens=1024, answer_hint=""):
        from dyslexia_converter.ai.providers import Reply

        Answering.prompt = prompt
        return Reply(self.answer(prompt), "{}", 100, 10)


def column_order(prompt: str) -> dict:
    """The right answer for boxed_pdf: the left column, the right column, then the box."""
    import re

    rows = [re.match(r"(\d+) \| x (\d+)-\d+ y (\d+)", line).groups() for line in prompt.splitlines()]
    body = sorted((r for r in rows if "BOX" not in prompt.splitlines()[int(r[0])]),
                  key=lambda r: (int(r[1]) > 50, int(r[2])))
    return {"o": [int(r[0]) for r in body] + [int(r[0]) for r in rows if r not in body]}


def run_layout(tmp_path, monkeypatch, answer):
    """Load boxed_pdf and run the AI layout check with a stand-in answer; returns the session."""
    from dyslexia_converter import pipeline
    from dyslexia_converter.ai import assistant as assistant_mod
    from dyslexia_converter.ai.keystore import KeyStore
    from dyslexia_converter.settings import AISettings, FormatSettings

    path = tmp_path / "boxed.pdf"
    boxed_pdf(path)
    settings = FormatSettings()
    session = pipeline.load(path, settings, use_ocr=False)
    ks = KeyStore()
    ks._keyring = False
    ks.set("mistral", "test-key-000000000")
    monkeypatch.setattr(assistant_mod, "make_provider", lambda *a, **k: Answering(answer))
    ai = assistant_mod.AIAssistant(AISettings(mode="ai_assisted", consent_given=True, use_for_citations=False,
                                              use_for_ocr=False), ks)
    return session, ai, settings


def body_text(session) -> str:
    return " ".join(b.text for b in session.document.blocks if b.kind.name in ("PARAGRAPH", "HEADING"))


def test_boxed_page_is_flagged_and_the_ai_order_fixes_it(isolated_home, tmp_path, monkeypatch):
    session, ai, settings = run_layout(tmp_path, monkeypatch, column_order)
    assert any("unusual layout" in w for w in session.document.warnings)
    before = body_text(session)
    session.run_ai(ai, settings)
    text = body_text(session)
    assert not any("unusual layout" in w for w in session.document.warnings)
    assert session.document.pages[0].ai_layout
    # the left column is read to its end before the right column starts, and no words are lost or added
    assert text.index("Left column sentence 23") < text.index("Right column sentence 0")
    assert sorted(text.split()) == sorted(before.split())
    assert "Subscribe" not in Answering.prompt or "…" in Answering.prompt or len(Answering.prompt) < 4000
    assert ai.log.entries()[-1].task == "layout"


def test_boxed_page_is_read_column_by_column_without_ai(isolated_home, tmp_path):
    from dyslexia_converter import pipeline

    path = tmp_path / "boxed.pdf"
    boxed_pdf(path)
    session = pipeline.load(path, use_ocr=False)
    text = body_text(session)
    assert any("column by column" in w for w in session.document.warnings)
    assert text.index("Left column sentence 23") < text.index("Right column sentence 0")
    assert text.index("Right column sentence 7") < text.index("Right column sentence 8")
    for i in range(24):  # every sentence once
        assert text.count(f"Left column sentence {i} ") == 1 and text.count(f"Right column sentence {i} ") == 1


def test_an_answer_that_would_repeat_text_is_not_used(isolated_home, tmp_path, monkeypatch):
    session, ai, settings = run_layout(tmp_path, monkeypatch, lambda prompt: {"o": [0, 0, 1]})
    before = [b.text for b in session.document.blocks]
    session.run_ai(ai, settings)
    assert [b.text for b in session.document.blocks] == before  # the local result is kept
    assert any("unusual layout" in w for w in session.document.warnings)


def span(text, bbox, size):
    """A span of text as read from a PDF."""
    return _Span(text, bbox, bbox[3] - 2, size, "Times", 0, 0)


def test_drop_cap_is_put_back_in_front_of_its_word():
    spans = [span("M", (33, 595, 72, 667), 57), span("ichael Eisen doesn’t hold back", (76, 612, 291, 622), 9.5),
             span("what we pay, he declares.", (76, 633, 291, 643), 9.5), span("text " * 20, (37, 700, 291, 710), 9.5)]
    out = _join_drop_caps(spans)
    assert [s.text for s in out][:2] == ["Michael Eisen doesn’t hold back", "what we pay, he declares."]
    assert len(out) == 3


def test_a_large_letter_that_is_no_drop_cap_stays():
    spans = [span("A", (33, 100, 60, 140), 30), span("Introduction to the topic", (70, 110, 300, 120), 10),
             span("text " * 30, (37, 200, 291, 210), 10)]
    assert [s.text for s in _join_drop_caps(spans)] == [s.text for s in spans]  # next word is not lower case
