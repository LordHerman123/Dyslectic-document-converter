"""A formula the reader types in LaTeX to correct one: written as the converter's formula text, in the maths font."""
import pytest

from dyslexia_converter import pipeline
from dyslexia_converter.model import Block, BlockKind, Document, PageInfo
from dyslexia_converter.render.compose import compose
from dyslexia_converter.settings import FormatSettings
from dyslexia_converter.transform.latex import to_formula_text


@pytest.mark.parametrize("latex, text", [
    (r"\frac{a+b}{2c} + \sqrt{x^2+1}", "(a+b)/(2c) + √(x²+1)"),
    (r"\sum_{i=1}^{n} x_i", "∑ᵢ₌₁ⁿ xᵢ"),
    (r"e^{i\pi} + 1 = 0", "e^(iπ) + 1 = 0"),
    (r"\lim_{x \to 0} \frac{\sin x}{x} = 1", "lim_(x → 0) (sin x)/x = 1"),
    (r"$A = \mathrm{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$", "A = softmax((QKᵀ)/(√(dₖ)))V"),
    (r"\begin{pmatrix} a & b \\ c & d \end{pmatrix}", "matrix(a, b; c, d)"),
    (r"f(x) = \begin{cases} x & x \ge 0 \\ -x & \text{otherwise} \end{cases}", "f(x) = cases(x, x ≥ 0; −x, otherwise)"),
    (r"\hat{x} + \bar{y} \ne \hat{xy}", "x̂ + ȳ ≠ hat(xy)"),
    (r"\mathbb{R}^n \subseteq \mathcal{L}", "ℝⁿ ⊆ ℒ"),
    (r"\sqrt[3]{x} \le \alpha\beta", "∛x ≤ αβ"),
])
def test_latex_becomes_the_converters_formula_text(latex, text):
    r = to_formula_text(latex)
    assert r.text == text and not r.unknown and r.balanced


def test_nothing_typed_is_lost():
    r = to_formula_text(r"\overbrace{a+b}{c} = 2")
    assert r.text == r"\overbrace{a+b}{c} = 2" and r.unknown == [r"\overbrace"]
    assert not to_formula_text(r"\frac{1}{").balanced
    assert not to_formula_text(r"x}").balanced


def test_a_typed_formula_replaces_the_words_in_the_maths_font_and_opens_again_as_latex(tmp_path):
    b = Block("b", BlockKind.PARAGRAPH, "Input: data {(2;, yi) }%,, rate n for t", page=0)
    doc = Document("x.pdf", pages=[PageInfo(0, 595, 842, "text")], blocks=[b])
    session = pipeline.Session(doc, pipeline.CustomWords(tmp_path / "words.txt"))
    where = session.find_passage("{(2;, yi) }%,,")
    latex = r"\{(x_i, y_i)\}_{i=1}^{N}"
    edit = session.edit_passage(*where, to_formula_text(latex).text, latex=latex)
    assert edit is not None and edit.latex == latex
    item = next(i for i in compose(doc, FormatSettings()).items if i.block_id == "b")
    assert [(r.text, r.math) for r in item.runs] == [("Input: data ", False), ("{(xᵢ, yᵢ)}ᵢ₌₁ᴺ", True),
                                                     (" rate n for t", False)]
    again = session.find_passage("{(xᵢ, yᵢ)}ᵢ₌₁ᴺ")
    assert session.passage_latex(*again) == latex
    assert session.edit_passage(*again, to_formula_text(latex).text, latex=latex) is None  # nothing changed
    session.remove_user_edit(edit.id)
    assert doc.display_text(b) == b.text
