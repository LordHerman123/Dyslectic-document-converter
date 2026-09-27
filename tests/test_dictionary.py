"""The word card's dictionary: meanings found from inflected forms, syllables, online link."""
from dyslexia_converter import dictionary


def test_meanings_of_base_and_inflected_words():
    e = dictionary.lookup("Empiricism,", "en")
    assert e.word == "Empiricism" and e.base == "empiricism"
    assert e.senses and "experience" in e.senses[0].meaning and e.source
    assert dictionary.lookup("theories", "en").base == "theory"
    assert dictionary.lookup("mice", "en").base == "mouse"  # irregular form
    ran = dictionary.lookup("ran", "en")
    assert ran.base == "run" and all(s.pos == "verb" for s in ran.senses)


def test_cleaning_quotes_and_ligatures():
    assert dictionary.clean("‘scientiﬁc’;") == "scientific"
    assert dictionary.lookup("scientiﬁc", "en").senses


def test_unknown_word_and_other_languages():
    assert not dictionary.lookup("xyzzyq", "en").senses
    nl = dictionary.lookup("kennisproductie", "nl")
    assert not nl.senses and len(nl.syllables) >= 4  # no Dutch dictionary, but syllables
    assert dictionary.online_url("Kennis", "nl") == "https://nl.wiktionary.org/wiki/kennis"


def test_syllables():
    assert dictionary.syllables("running", "en") == ["run", "ning"]
    assert dictionary.syllables("x", "zz") == ["x"]  # unknown language: the word as it is
