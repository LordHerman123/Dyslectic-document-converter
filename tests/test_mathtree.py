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


@pytest.mark.parametrize("path", [FIXTURE, STRESS])
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
