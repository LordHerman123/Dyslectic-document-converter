from collections import Counter

from dyslexia_converter.model import Block, BlockKind, Correction, Document, apply_corrections
from dyslexia_converter.transform.spelling import CustomWords, Dictionary, OcrCorrector, detect_language


def corrector(tmp_path, *words):
    cw = CustomWords(tmp_path / "words.txt")
    for w in words:
        cw.add(w)
    return OcrCorrector(Dictionary(["en"], cw))


def test_typical_ocr_errors_are_confident(tmp_path):
    c = corrector(tmp_path)
    assert c.suggest("dyslexla", "x dyslexla", 2, Counter()) == ("dyslexia", 0.97)
    assert c.suggest("informatlon", "x informatlon", 2, Counter())[0] == "information"
    assert c.suggest("cornputer", "x cornputer", 2, Counter())[1] >= 0.9


def test_non_ocr_misspellings_are_only_suggested(tmp_path):
    word, conf = corrector(tmp_path).suggest("reserach", "The reserach", 4, Counter())
    assert word == "research" and conf < 0.9


def test_protected_words(tmp_path):
    c = corrector(tmp_path, "Kitchin")
    ctx = "as argued by Kitchin and NASA in their optimised analytics"
    for w in ("Kitchin", "NASA", "optimised", "analytics"):
        assert c.suggest(w, ctx, ctx.index(w), Counter()) is None
    assert c.suggest("colour", "the colour", 4, Counter()) is None


def test_modes_and_reversibility(tmp_path):
    doc = Document("x.pdf", blocks=[Block("b1", BlockKind.PARAGRAPH, "The dyslexla study used the reserach data.",
                                          source="ocr")])
    c = corrector(tmp_path)
    assert c.correct_document(doc, "disabled") == []
    auto = c.correct_document(doc, "automatic")
    assert [(x.original, x.status) for x in auto] == [("dyslexla", "auto")]
    review = c.correct_document(doc, "review")
    assert {x.original: x.status for x in review} == {"dyslexla": "auto", "reserach": "pending"}
    doc.corrections = review
    assert doc.display_text(doc.blocks[0]) == "The dyslexia study used the reserach data."
    assert doc.blocks[0].text == "The dyslexla study used the reserach data."  # original kept
    for x in review:
        x.status = "rejected"
    assert doc.display_text(doc.blocks[0]) == doc.blocks[0].text


def test_apply_corrections_skips_stale_offsets():
    c = Correction("c1", "b", 0, 3, "abc", "xyz", 0.9, "accepted")
    assert apply_corrections("abd def", [c]) == "abd def"


def test_language_detection():
    assert detect_language("de kat zit op het dak en de hond is in de tuin") == "nl"
    assert detect_language("the cat is on the roof and the dog is in the garden") == "en"


def test_book_scan_words_are_not_miscorrected(tmp_path):
    c = corrector(tmp_path)
    ctx = "x "
    for w in ("crown’s", "naturalist’s", "forests’", "utilité", "l’esprit", "logics",
              "nonsustainable", "decentral", "collectivizers", "describ", "strik", "avy"):
        assert c.suggest(w, ctx + w, len(ctx), Counter()) is None, w
    assert c.suggest("characreristic", "x characreristic", 2, Counter())[0] == "characteristic"


def test_words_broken_without_hyphen_are_rejoined():
    from dyslexia_converter.transform.spelling import word_rejoiner

    join = word_rejoiner(Dictionary(["en"]))
    assert join("describ", "ing") and join("particu", "larly")
    assert not join("the", "forest") and not join("state", "tax")


def test_words_from_other_languages_are_protected(tmp_path):
    c = corrector(tmp_path)
    for w in ("aune", "pinte", "rentes", "Weltanschauung", "gemeente"):
        assert c.suggest(w, "x " + w, 2, Counter()) is None, w
    assert c.suggest("cornputer", "x cornputer", 2, Counter())[0] == "computer"  # OCR errors still fixed


def test_more_languages_detected():
    assert detect_language("il gatto è sul tetto e non per la casa della nonna che sono anche") == "it"
    assert detect_language("o gato não está com os cães para mais também que os outros") == "pt"


def test_review_shows_the_whole_sentence():
    """The OCR review shows the full sentence around a word (abbreviations don't end it)."""
    from dyslexia_converter.model import Correction
    from dyslexia_converter.pipeline import Session

    text = "Intro sentence here. Smith et al. showed that the rnodel works, e.g. in tests. Next one!"

    class Doc:
        def block(self, _):
            return type("B", (), {"text": text})

    session = Session.__new__(Session)
    session.document = Doc()
    i = text.index("rnodel")
    c = Correction.__new__(Correction)
    c.block_id, c.start, c.end, c.original, c.replacement = 1, i, i + 6, "rnodel", "model"
    assert session.correction_sentence(c) == ("Smith et al. showed that the ", "rnodel", " works, e.g. in tests.")


def _session_with(tmp_path, text, word, replacement):
    from dyslexia_converter.pipeline import Session

    block = Block(id="b1", kind=BlockKind.PARAGRAPH, text=text, page=0)
    doc = Document(source_path="scan.pdf", blocks=[block])
    i = text.index(word)
    doc.corrections = [Correction("c1", "b1", i, i + len(word), word, replacement, 0.6)]
    return Session(doc, CustomWords(tmp_path / "words.txt")), doc, block


def test_user_can_retype_a_badly_read_line(tmp_path):
    text = "Suburbs have, after fifty years, become thoroughly diffe ent settings from what was planned. Next."
    session, doc, block = _session_with(tmp_path, text, "ent", "cut")
    suggestion = doc.corrections[0]
    assert session.pending_corrections() == [suggestion]

    edit = session.edit_text(suggestion, "Suburbs have, after fifty years, become thoroughly different settings "
                                         "from what was planned.")
    assert (edit.original, edit.replacement, edit.source, edit.status) == ("diffe ent", "different", "user",
                                                                          "accepted")
    assert "thoroughly different settings" in doc.display_text(block)
    assert "cut" not in doc.display_text(block)
    assert session.pending_corrections() == []          # the suggestion is replaced by the user's text
    assert block.text == text                            # the scanned text itself is never changed

    session.remove_user_edit(edit.id)                    # undo
    assert doc.display_text(block) == text
    assert session.pending_corrections() == [suggestion]


def test_unchanged_edit_does_nothing(tmp_path):
    session, doc, _ = _session_with(tmp_path, "One two thre four. Five.", "thre", "three")
    assert session.edit_text(doc.corrections[0], "One two thre four.") is None
    assert len(doc.corrections) == 1
