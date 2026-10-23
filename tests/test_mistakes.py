"""Words split after fi / fl / ff are joined, and the reader's own list of common mistakes is fixed or marked in
every document: as corrections (the text itself is kept), each one can be undone and stays undone."""
from dyslexia_converter import pipeline
from dyslexia_converter.model import Block, BlockKind, Document, PageInfo
from dyslexia_converter.settings import FormatSettings
from dyslexia_converter.transform.spelling import CustomWords, Dictionary, MistakeList, ligature_gaps


def test_words_split_after_fi_fl_ff_are_found():
    d = Dictionary(["en"])
    joined = lambda text: [j for _a, _z, j in ligature_gaps(text, d)]  # noqa: E731
    assert joined("the scientifi c method, a signifi cant result") == ["scientific", "significant"]
    assert joined("the fl ow of water") == ["flow"] and joined("Fl ow") == ["Flow"]
    assert joined("diff erent views and the eﬃ cient way") == ["different", "eﬃcient"]
    # two real words, or a name, stay as they are
    assert joined("the staff of the lab, off ice, Bickerstaff and Aronoff") == []


def test_the_list_of_mistakes_is_kept_and_found_as_whole_words(tmp_path):
    m = MistakeList(tmp_path / "mistakes.txt")
    m.add("scientifi c", "scientific")
    m.add("teh")  # only to mark
    again = MistakeList(tmp_path / "mistakes.txt")
    assert again.entries == [("scientifi c", "scientific"), ("teh", "")]
    text = "Scientifi  c work: teh end, not tehran."
    assert again.find(text) == [(0, 12, "Scientific"), (19, 22, "")]
    again.remove("teh")
    assert MistakeList(tmp_path / "mistakes.txt").entries == [("scientifi c", "scientific")]


def _session(tmp_path, text: str, mistakes: MistakeList) -> pipeline.Session:
    doc = Document("x.pdf", pages=[PageInfo(0, 595, 842, "text")], language="en",
                   blocks=[Block("p1", BlockKind.PARAGRAPH, text, page=0)])
    session = pipeline.Session(doc, CustomWords(tmp_path / "words.txt"), mistakes=mistakes)
    session.apply_word_fixes()
    return session


def test_fixes_are_corrections_that_can_be_undone_and_stay_undone(tmp_path):
    m = MistakeList(tmp_path / "mistakes.txt")
    m.add("resuIts", "results")
    session = _session(tmp_path, "The scientifi c resuIts were signifi cant.", m)
    out = session.export("txt", FormatSettings()).decode("utf-8")
    assert "The scientific results were significant." in out
    assert session.document.blocks[0].text == "The scientifi c resuIts were signifi cant."  # the text is kept
    assert {c.source for c in session.document.corrections} == {"ligature", "list"}
    first = next(c for c in session.document.corrections if c.original == "scientifi c")
    session.set_correction(first.id, "rejected")
    session.apply_word_fixes()  # done again (the list changed, or the page was laid out again)
    assert "The scientifi c results" in session.export("txt", FormatSettings()).decode("utf-8")


def test_a_mistake_without_a_fix_is_a_word_to_check(tmp_path):
    m = MistakeList(tmp_path / "mistakes.txt")
    m.add("data set")
    session = _session(tmp_path, "We use the data  set of the study.", m)
    assert session.quality().unsure["p1"] == [(11, 20, "listed")]
    assert "data  set" in session.document.blocks[0].text and not session.document.corrections
