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
