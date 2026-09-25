"""App translations: English, Dutch, French, German, Spanish and Italian.

Only the app's own words are translated; the documents you convert are never changed.
Texts are looked up by their English wording, so a missing translation simply shows the English.
Messages produced by the processing core (progress, warnings) are matched by the patterns below.
"""
from __future__ import annotations

import locale
import re

from .translations import PATTERNS, T

LANGUAGES = {"en": "English", "nl": "Nederlands", "fr": "Français", "de": "Deutsch", "es": "Español",
             "it": "Italiano"}

# core messages (English) -> pattern id; each locale has a template per id using {0}, {1}, ...
MESSAGE_PATTERNS: list[tuple[str, re.Pattern]] = [(k, re.compile(p)) for k, p in [
    ("read_scanned_eta", r"^Read (\d+) of (\d+) scanned page\(s\) - about (.+) left$"),
    ("read_scanned", r"^Read (\d+) of (\d+) scanned page\(s\)$"),
    ("reading_page", r"^Reading page (\d+) of (\d+)$"),
    ("ocr_page", r"^Running OCR on page (\d+) of (\d+)$"),
    ("no_ocr", r"^(\d+) scanned page\(s\) are kept as pictures because no OCR engine is installed\. "
               r"Install Tesseract OCR to convert them to text\.$"),
    ("text_layer", r"^(\d+) scanned page\(s\) used the text the scanner stored in the PDF, which can be of lower "
                   r"quality\. Install Tesseract OCR for the best results\.$"),
    ("pictured", r"^The text the scanner stored for page\(s\) (.+?) of the PDF is unreadable, so \(parts of\) "
                 r"these pages are shown as pictures\. Install Tesseract OCR to convert them to text\.$"),
    ("garbled", r"^The text the scanner stored for page\(s\) (.+?) of the PDF contains errors\. "
                r"Install Tesseract OCR for a cleaner result\.$"),
    ("sent_to_ai", r"^Sent to AI: (.+)$"),
    ("n_citations", r"^(\d+) uncertain citation\(s\)$"),
    ("n_ocr_words", r"^(\d+) uncertain OCR word\(s\)$"),
    ("font_substitute", r"^(.+) is not installed on this device; using the similar free font (.+) instead\.$"),
]]


def system_language() -> str:
    """The device's language if the app speaks it, else English."""
    names = {"nl": ("nl", "dutch"), "fr": ("fr", "french"), "de": ("de", "german"), "es": ("es", "spanish"),
             "it": ("it", "italian")}
    try:
        loc = (locale.getlocale()[0] or "").lower()
    except Exception:
        loc = ""
    for code, prefixes in names.items():
        if loc.startswith(prefixes):
            return code
    return "en"


class Translator:
    def __init__(self, lang: str = "en"):
        self.lang = lang if lang in LANGUAGES else "en"
        self.strings = {en: tr[self.lang] for en, tr in T.items() if self.lang in tr}
        self.patterns = {key: tr[self.lang] for key, tr in PATTERNS.items() if self.lang in tr}

    def __call__(self, text: str, **values) -> str:
        s = self.strings.get(text, text)
        return s.format(**values) if values else s

    def message(self, msg: str) -> str:
        """Translate a message from the processing core (exact text first, then the known patterns)."""
        if self.lang == "en" or not msg:
            return msg
        if msg in self.strings:
            return self.strings[msg]
        for key, pat in MESSAGE_PATTERNS:
            m = pat.match(msg)
            if m and key in self.patterns:
                parts = [self.message(g) for g in m.groups()]
                if key == "sent_to_ai":
                    parts = [", ".join(self.message(x) for x in m.group(1).split(", "))]
                return self.patterns[key].format(*parts)
        return msg
