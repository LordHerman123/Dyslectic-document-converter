"""The structure of display formulas, read from the PDF's glyphs (extract/mathtree.py)."""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pymupdf
import pytest

from dyslexia_converter import pipeline
from dyslexia_converter.extract import mathtree

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "stress" / "s5_formulas.pdf"
STRESS = ROOT / "tests" / "stress" / "s1_math.pdf"
ABX = ROOT / "tests" / "stress" / "s6_mathabx.pdf"
ROUND2 = ROOT / "tests" / "stress" / "s7_round2.pdf"


def equations(path):
    doc = pipeline.load(str(path)).document
    return [b.image for b in doc.blocks if b.image is not None and b.image.kind == "equation"]


@pytest.fixture(scope="module")
def fixture_alts():
    return [im.alt for im in equations(FIXTURE)]


@pytest.mark.parametrize("expected", [
    "y = (a + b)/(c − d)",            # fraction
    "z = 1/(1 + 1/x)",                # nested fraction
    "r = √(x^2 + y^2)",               # radical with scripts inside
    "s = √[3](ab)",                   # n-th root
    "P = 10000^(2i/d)",               # a superscript with several symbols
    "W_i^Q = X_i A",                  # sub- and superscript on one symbol
    "S = ∑_(i=1)^n x_i",              # limits under and over a sum
    "L = lim_(n→∞) a_n",              # limit under a function name
    "F = ∫_0^1 f(x)dx",               # integral limits as scripts
    "M = matrix(a, b; c, d)",         # matrix in tall brackets
    "f(x) = cases(1, x > 0; 0, x ≤ 0)",
    "hat(R) = 1/N ∑_(j=1)^N ℓ(y_j)",  # accent, fraction, sum
    "a ≤ b ≠ c ≈ d",                  # negated relation built from two glyphs
    "(∂L)/(∂w) = −y/a",
])
def test_structure_of_display_formulas(fixture_alts, expected):
    assert expected in fixture_alts


def test_equation_number_is_kept_apart():
    alts = [im.alt for im in equations(STRESS)]
    numbered = [a for a in alts if re.search(r"[^,.;:], equation \(\d+\)$", a)]
    assert numbered, alts
    assert any(a.startswith("|x| = cases(") and a.endswith("equation (6)") for a in numbered)


def test_aligned_rows_are_separated(fixture_alts):
    assert "(a + b)^2 = a^2 + 2ab + b^2 ; = b^2 + 2ab + a^2" in fixture_alts


def _printed(text: str) -> Counter:
    return mathtree._symbols(re.sub(r",? equation \(\d+[a-z]?\)$", "", text))


@pytest.mark.parametrize("path", [FIXTURE, STRESS, ABX, ROUND2])
def test_no_symbol_is_added_or_lost(path):
    for im in equations(path):
        if im.alt != im.glyph_text:  # structured: every printed symbol exactly once
            got = _printed(im.alt) + mathtree._symbols(im.eq_number)
            lost = mathtree._symbols(im.glyph_text) - got
            # only sentence punctuation after a numbered formula may be left out
            assert not (got - mathtree._symbols(im.glyph_text)), im.alt
            assert not lost or (im.eq_number and set(lost) <= set(".:")), im.alt


def _page(draw) -> pymupdf.Page:
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=200)
    draw(page)
    return page


def test_unexplained_line_falls_back():
    """A rule with symbols only above it (an underline) is not a structure this module knows: no guess."""
    def draw(page):
        page.insert_text((100, 100), "x+y", fontname="helv", fontsize=12)
        page.draw_line((98, 104), (125, 104), width=0.4)
    page = _page(draw)
    drawings = [tuple(d["rect"]) for d in page.get_drawings()]
    assert mathtree.linear(page, (90, 85, 140, 110), drawings, 12.0) is None


def test_plain_text_formula_is_kept():
    def draw(page):
        page.insert_text((100, 100), "a = b + c", fontname="helv", fontsize=12)
    page = _page(draw)
    f = mathtree.linear(page, (90, 85, 200, 110), [], 12.0)
    assert f is not None and f.text == "a = b + c" and f.number == ""


def test_switches_turn_parts_off():
    page = pymupdf.open(str(FIXTURE))[0]
    try:
        mathtree.ENABLED["fractions"] = False
        alts = [im.alt for im in equations(FIXTURE)]
        assert "y = (a + b)/(c − d)" not in alts
    finally:
        mathtree.ENABLED["fractions"] = True
    assert page is not None


def test_numbered_rows_are_separate_pictures():
    """A derivation numbered per row becomes one picture per row, each with its own number (F14)."""
    alts = [im.alt for im in equations(STRESS)]
    for n in (3, 4, 5):
        assert sum(f"({n})" in a for a in alts) == 1
        assert all(not (f"({n})" in a and f"({n + 1})" in a) for a in alts)


def test_formulas_side_by_side_stay_one_picture():
    """Two formulas set apart by a wide space on one line are not torn apart (their limits stay with them)."""
    alts = [im.alt for im in equations(STRESS)]
    assert any("∑_(n=1)^∞" in a and "∏_(p prime)" in a for a in alts)


@pytest.mark.parametrize("expected", [
    "x_i = √(1 − β_i) x_(i−1) + √(β_i) z_(i−1), equation (1)",
    "x_i = x_(i−1) + √(σ_i^2 − σ_(i−1)^2) z_(i−1)",
    "a ≤ b < c, S = ∑_(i=1)^N λ_i × µ_i",
    "f(x)∝ exp(−x^2) ± 1",
])
def test_mathabx_fonts(expected):
    """mathabx's symbols come out of the PDF as placeholder letters ("ă" for <); their codes give the symbols."""
    assert expected.replace(" ", "") in [im.alt.replace(" ", "") for im in equations(ABX)]


@pytest.mark.parametrize("expected", [
    "∑_(l=0)^∞ γ^l tilde(r)_t = ∑_(l=0)^∞ γ^l r_(t+l), equation (1)",  # limits next to lines of text
    "W (ℙ_θ, ℙ_(θ^′)) ≤ ∥g_θ(z) − g_(θ^′)(z)∥",  # a prime inside a subscript
    "x_i^m = x_i^(m−1) + ϵ_i s_(θ^∗)(x_i^(m−1))",  # a script of a subscript
    "tilde(f)_i(x) = d bar(w) + √(σ_i^2 − σ_(i−1)^2)",  # accents on the symbol only; radical over scripts
])
def test_harder_structures(expected):
    assert expected.replace(" ", "") in [im.alt.replace(" ", "") for im in equations(ROUND2)]


def test_limits_stay_out_of_the_text_around():
    doc = pipeline.load(str(ROUND2)).document
    text = " ".join(b.text for b in doc.blocks if b.image is None and b.text)
    assert "lines of text around it:" in text and "Letting the transformed values" in text
    assert "∞" not in text and "l=0" not in text


def test_a_script_of_a_script_in_a_small_text():
    """In 9 pt text a subscript row is 6 pt and its own script 5 pt: TeX shrinks the second level less, so the 5 pt
    symbol is nearly as large as the row it belongs to (lim_(ε→0^+) in a 9 pt paper)."""
    def draw(page):
        page.insert_text((100, 100), "x", fontname="helv", fontsize=9)
        page.insert_text((105.2, 102.2), "t0", fontname="helv", fontsize=6)
        page.insert_text((110.6, 99.9), "+", fontname="helv", fontsize=5)
        page.insert_text((116, 100), "= y", fontname="helv", fontsize=9)
    f = mathtree.linear(_page(draw), (95, 88, 140, 106), [], 9.0)
    assert f is not None and f.text == "x_(t0^+) = y"


def test_small_capitals_starting_a_formula_are_part_of_its_line():
    """KL or ELBO set in small capitals at the start of a formula (smaller type on the baseline itself) is the
    formula's first word, not a script before any symbol."""
    def draw(page):
        page.insert_text((100, 100), "ELBO", fontname="helv", fontsize=7)
        page.insert_text((118, 100), "(q) = y", fontname="helv", fontsize=10)
    f = mathtree.linear(_page(draw), (95, 88, 160, 104), [], 10.0)
    assert f is not None and f.text.replace(" ", "") == "ELBO(q)=y"


def test_big_delimiters_are_read_by_the_glyph_names_of_the_font():
    """Extension fonts that add sizes to the CMEX codes (MathDesign: code 150 is "bracketleftbig6") draw whole big
    delimiters at codes CMEX does not have: they are read by the glyph names the embedded font gives them. A piece
    of a delimiter, or a name the font does not give, is not guessed."""
    from types import SimpleNamespace
    program = b"/Encoding 256 array\ndup 2 /bracketleftbig1 put\ndup 150 /bracketleftbig6 put\n" \
              b"dup 153 /bracketrightbig6 put\ndup 160 /bracketlefttp put\nreadonly def"
    parent = SimpleNamespace(extract_font=lambda xref: ("x", "pfa", "Type1", program))
    fonts = [(7, "pfa", "Type1", "EVWXBV+MathDesign-CH-Regular-Extension-10", "F7", "")]
    page = SimpleNamespace(parent=parent, get_fonts=lambda: fonts)
    read = [mathtree._named_delimiter(page, "MathDesign-CH-Regular-Ex", c) for c in (150, 153, 160, 200)]
    assert read == ["[", "]", "", ""]


def test_a_fraction_under_a_root_is_built_inside_it():
    """√(d[σ²(t)]/dt): the root's line and the fraction's line are both under the sign; the fraction is built
    first, with the line under the sign, and the root takes its baseline (not its denominator's)."""
    A = mathtree.Atom
    root = A("√", 100, 88, 110, 118, 104, 10, kind="big", top=88)
    rules = [A("", 110, 88.5, 140, 88.5, 88.5, 0.0, kind="rule", glyphs=0),   # the line over the root
             A("", 112, 103, 138, 103, 103, 0.0, kind="rule", glyphs=0)]      # the fraction's line
    num, den = A("a", 120, 92, 126, 101, 100, 10), A("b", 120, 106, 126, 115, 114, 10)
    b = mathtree._Builder([A("x", 80, 99, 86, 107, 106, 10), A("=", 90, 101, 96, 105, 106, 10), root, num, den],
                          list(rules), 10.0)
    b.radicals()
    b.fractions()
    assert b.rules == []
    [node] = [a for a in b.atoms if a.kind == "node"]
    assert node.text == "√(a/b)" and abs(node.base - (103 + 0.25 * 10)) < 0.01
