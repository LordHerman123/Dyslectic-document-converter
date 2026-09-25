"""The app's texts are translated into every supported language, with matching {placeholders}."""
import ast
import string
from pathlib import Path

import pytest

from dyslexia_converter.ui.i18n import LANGUAGES, MESSAGE_PATTERNS, Translator
from dyslexia_converter.ui.translations import PATTERNS, T

PKG = Path(__file__).resolve().parents[1] / "dyslexia_converter"
OTHER = [code for code in LANGUAGES if code != "en"]


def _ui_texts() -> list[str]:
    """Every literal passed to the translator (t("...") or self.t("...")) in the UI."""
    tree = ast.parse((PKG / "ui" / "app.py").read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            f = node.func
            if (isinstance(f, ast.Name) and f.id == "t") or (isinstance(f, ast.Attribute) and f.attr == "t"):
                out.append(node.args[0].value)
    return out


def _fields(s: str) -> set:
    return {f for _, f, _, _ in string.Formatter().parse(s) if f}


def test_every_ui_text_is_translated():
    texts = _ui_texts()
    assert len(texts) > 150
    missing = [(t, lang) for t in texts for lang in OTHER if lang not in T.get(t, {})]
    assert not missing, missing[:10]


def test_placeholders_match():
    for en, tr in T.items():
        for lang in OTHER:
            assert _fields(tr[lang]) == _fields(en), (en, lang)
    for key, tr in PATTERNS.items():
        assert set(tr) == set(OTHER), key


def test_every_pattern_has_translations():
    assert {k for k, _ in MESSAGE_PATTERNS} == set(PATTERNS)


@pytest.mark.parametrize("msg", [
    "Read 3 of 12 scanned page(s) - about 40 s left",
    "Read 12 of 12 scanned page(s)",
    "Reading page 2 of 9",
    "Running OCR on page 4 of 9",
    "3 scanned page(s) are kept as pictures because no OCR engine is installed. Install Tesseract OCR to convert "
    "them to text.",
    "2 scanned page(s) used the text the scanner stored in the PDF, which can be of lower quality. Install "
    "Tesseract OCR for the best results.",
    "The text the scanner stored for page(s) 3-5, 9 of the PDF is unreadable, so (parts of) these pages are shown "
    "as pictures. Install Tesseract OCR to convert them to text.",
    "The text the scanner stored for page(s) 20 of the PDF contains errors. Install Tesseract OCR for a cleaner "
    "result.",
    "Sent to AI: 2 uncertain citation(s), 5 uncertain OCR word(s)",
    "Verdana is not installed on this device; using the similar free font DejaVu Sans instead.",
    "Detecting document structure",
])
def test_core_messages_are_translated(msg):
    for lang in OTHER:
        out = Translator(lang).message(msg)
        assert out != msg and "{" not in out, (lang, out)


def test_core_messages_still_exist_in_the_core():
    """If the core's wording changes, the patterns above must change with it."""
    src = "".join((PKG / f).read_text(encoding="utf-8") for f in
                  ["pipeline.py", "extract/pdf_reader.py", "fonts.py", "ai/assistant.py"])
    for piece in ["scanned page(s) are kept as pictures because no OCR engine is ",
                  "used the text the scanner stored in the PDF, ",
                  "of the PDF is \"\n                            \"unreadable, so (parts of) these pages are shown",
                  "of the PDF contains \"\n                            \"errors. Install Tesseract OCR for a cleaner",
                  "Read {done} of {scans_total} scanned page(s){eta}", "Reading page {pno + 1} of {n}",
                  "Running OCR on page {pno + 1} of {n}", "is not installed on this device; using the similar free",
                  "Using the saved text recognition of this document", "Detecting document structure",
                  "Checking OCR text against the dictionary", "Sent to AI: ", "Nothing needed AI help."]:
        assert piece in src, piece


def test_unknown_text_falls_back_to_english():
    assert Translator("fr")("Something new") == "Something new"
    assert Translator("xx")("Settings") == "Settings"
    assert Translator("de")("Settings") == "Einstellungen"
