"""Formulas read aloud as maths: their text said in words in the document's language, at their place in the reading
order, and highlighted while they are said."""
import io
import re

from PIL import Image as PILImage, ImageDraw

from dyslexia_converter import pipeline, speech
from dyslexia_converter.mathspeech import speak
from dyslexia_converter.model import Block, BlockKind, Document, ImageData, PageInfo
from dyslexia_converter.settings import FormatSettings
from dyslexia_converter.transform.spelling import CustomWords


def test_formulas_said_in_words():
    assert speak("E = mc^2, equation (3)") == "E equals m c squared, equation 3"
    assert speak("∑_(i=1)^n x_i") == "the sum from i equals 1 to n of x sub i"
    assert speak("x = (−b ± √(b^2 − 4ac))/(2a)") == (
        "x equals the fraction minus b plus or minus the square root of b squared minus 4 a c, end root, over 2 a, "
        "end fraction")
    assert speak("∂/(∂z_i) f(z, t)") == "partial over partial z sub i f of z, t"
    assert speak("lim_(ε→0^+) |Δ|") == (
        "the limit as epsilon goes to 0 superscript plus of the absolute value of capital delta end absolute value")
    assert speak("hat(h)_t = matrix(a; b)^⊤") == (
        "h hat sub t equals the matrix, row 1: a; row 2: b, end matrix, transpose")
    assert speak("P (y | x)") == "P open bracket y given x close bracket"  # set apart: perhaps a product


def test_formulas_in_the_six_languages():
    f = "∑_(i=1)^n x_i^2 = (a)/(b), equation (4)"
    assert speak(f, "nl") == "de som van i is gelijk aan 1 tot n van x index i kwadraat is gelijk aan a gedeeld door b, " \
                             "vergelijking 4"
    assert speak(f, "de") == "Summe von i gleich 1 bis n von x Index i Quadrat gleich a durch b, Gleichung 4"
    assert speak(f, "fr") == "la somme de i égale 1 à n de x indice i au carré égale a sur b, équation 4"
    assert speak(f, "es") == "la suma desde i igual a 1 hasta n de x subíndice i al cuadrado igual a a entre b, ecuación 4"
    assert speak(f, "it") == "la somma da i uguale a 1 a n di x pedice i al quadrato uguale a a fratto b, equazione 4"
    assert speak(f, "pt") == speak(f, "en")  # other languages: English
    # prepositions and articles run together as the language wants
    assert speak("x ≤ |y|", "it") == "x minore o uguale al valore assoluto di y fine del valore assoluto"
    assert speak("f(∏_(i=1)^n x_i)", "fr") == "f du produit de i égale 1 à n de x indice i"
    assert speak("θ ∈ ℝ", "it") == "theta appartiene all'insieme dei numeri reali"


def test_nothing_is_left_as_notation_and_the_authors_words_stay():
    for f in ("a_i^l = w_i^(l^⊤)h^l", "(∂ log p(z))/(∂t) = −tr (u (∂h)/(∂z)^T)", "D_(KL)[P∥Q] ≈ 1/2δ^⊤F",
              "σ = √(1/H ∑_(i=1)^H (a_i − μ)^2)", "∫_0^∞ e^(−x) dx", "hat(w) = argmin_(w,ξ) C/n ∑_(j=1)^n ξ_(jy)"):
        for lang in ("en", "nl", "de", "fr", "es", "it"):
            said = speak(f, lang)
            assert not re.search(r"[_^/√∑∫∂]", said), (f, lang, said)
    # a word of the formula's own is not a word of the reading ("if" is not translated, "to" is not "tot")
    assert speak("x = 1 if y to z", "nl") == "x is gelijk aan 1 if y to z"


def test_the_word_being_said_is_found_inside_a_formula_said_in_several_words():
    s = speech.Sentence([speech.Word("We", 0, []), speech.Word("x equals y squared", 0, []), speech.Word("here", 0, [])])
    for k, w in enumerate(s.words):
        w.start = sum(len(v.text) + 1 for v in s.words[:k])
    assert [s.word_at(p) for p in (0, 1, 3, 4, 12, 21, 22, 23)] == [0, 0, 1, 1, 1, 1, 2, 2]


def _equation(alt: str, built: bool) -> ImageData:
    im = PILImage.new("RGB", (400, 60), "white")
    ImageDraw.Draw(im).text((20, 20), alt, fill="black")
    buf = io.BytesIO()
    im.save(buf, "PNG")
    img = ImageData(buf.getvalue(), "png", 400, 60, kind="equation", alt=alt, text_size=10)
    img.built = built
    return img


def test_a_display_formula_is_read_aloud_as_maths_in_its_place(tmp_path):
    blocks = [Block("p1", BlockKind.PARAGRAPH, "The energy of a body at rest is its mass times a constant.", page=0),
              Block("e1", BlockKind.IMAGE, page=0, bbox=(100, 200, 300, 220), image=_equation("E = mc^2", True)),
              Block("p2", BlockKind.PARAGRAPH, "Here c is the speed of light.", page=0),
              Block("e2", BlockKind.IMAGE, page=0, bbox=(100, 300, 300, 320), image=_equation("gl σil √x∼", False)),
              Block("p3", BlockKind.PARAGRAPH, "That one could not be read.", page=0)]
    doc = Document("x.pdf", pages=[PageInfo(0, 595, 842, "text")], blocks=blocks, language="en")
    session = pipeline.Session(doc, CustomWords(tmp_path / "words.txt"))
    pdf = session.export("pdf", FormatSettings())
    assert [(m[5], m[6], m[7]) for m in session.formula_marks] == [("E = mc^2", True, True),
                                                                    ("gl σil √x∼", False, True)]
    said = [s.text for s in speech.reading_units(pdf, formulas=session.formula_marks, language="en")]
    assert said[1:5] == ["E equals m c squared", "Here c is the speed of light.", "Formula",
                         "That one could not be read."]  # (then the note about this version)
    formula = speech.reading_units(pdf, formulas=session.formula_marks)[1].words[0]
    mark = session.formula_marks[0]
    assert formula.rects == [tuple(mark[1:5])]  # highlighted as a whole while it is said
    # in Dutch, and without the marks the formula pictures are passed over as before
    assert speech.reading_units(pdf, formulas=session.formula_marks, language="nl")[1].text == \
        "E is gelijk aan m c kwadraat"
    assert [s.text for s in speech.reading_units(pdf)][1:3] == ["Here c is the speed of light.",
                                                                "That one could not be read."]


def test_read_along_says_display_formulas_too():
    """The reading view (text flowing to fit the window) reads a display formula as maths, as a sentence of its own."""
    from types import SimpleNamespace

    from dyslexia_converter.render.compose import RItem
    from dyslexia_converter.ui.reflow import ReflowMode
    view = object.__new__(ReflowMode)
    view.app = SimpleNamespace(session=SimpleNamespace(document=SimpleNamespace(language="de")))
    view.items = [RItem("equation", image=_equation("x^2 = y", True)), RItem("equation", image=_equation("gl σ", False))]
    view._sentences()
    assert [u.text for u in view._units] == ["x Quadrat gleich y", "Formel"]
    assert view._unit_spans == [[(0, 0)], [(0, 0)]]  # nothing to mark in the text: the picture is the formula
