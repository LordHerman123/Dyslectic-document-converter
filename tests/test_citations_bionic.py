from dyslexia_converter.transform.bionic import bold_ranges
from dyslexia_converter.transform.citations import find_citations, match_reference


def test_author_date_citations():
    text = "Previous studies have demonstrated this effect (Smith, 2020; Jones & Brown, 2021)."
    (c,) = find_citations(text)
    assert c.kind == "author_date" and c.confidence > 0.9
    assert c.items == ["Smith, 2020", "Jones & Brown, 2021"]
    assert text[c.start:c.end] == "(Smith, 2020; Jones & Brown, 2021)"


def test_numeric_ranges_and_lists():
    cites = find_citations("as shown [2, 5, 8] and [3–7] but x in [0, 1]", n_references=10)
    assert [c.items for c in cites[:2]] == [["2", "5", "8"], ["3", "4", "5", "6", "7"]]
    assert cites[2].confidence < 0.5  # [0, 1] is an interval, not a citation


def test_uncertain_and_non_citations():
    assert find_citations("(boyd and Crawford, 2012)")[0].confidence < 0.9
    assert find_citations("the interval (0, 2020) is large") == []
    assert find_citations("(N = 42, 2019 data)") == []


def test_match_reference():
    refs = ["[1] Garcia, M. (2019). Layouts.", "[2] Smith, J. (2020). Dyslexia and typography."]
    assert match_reference("Smith, 2020", refs) == 1
    assert match_reference("Nobody, 2001", refs) == -1


def test_bionic_ranges_skip_punctuation_urls_and_identifiers():
    text = "The quick fox, see https://x.org/a_b and camelCase v2.0 NASA."
    words = [text[a:b] for a, b in bold_ranges(text, "auto")]
    assert words == ["T", "qu", "f", "s", "a"]
    w = "reading"
    assert [w[a:b] for a, b in bold_ranges(w, "first_letter")] == ["r"]
    assert [w[a:b] for a, b in bold_ranges(w, "40")] == ["rea"]
