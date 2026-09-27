"""Looking up a word: its syllables, and what it means.

Meanings come from an English dictionary kept in the app (Open English WordNet, CC BY 4.0), so nothing
leaves the device. For other languages there is no free offline dictionary of the same quality; the word
card then shows the syllables and offers to look the word up online (Wiktionary, in the browser).
Syllables use the hyphenation patterns of the document's language (pyphen), where available.
"""
from __future__ import annotations

import gzip
import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import quote

DATA = Path(__file__).resolve().parent / "assets" / "dictionary" / "en.json.gz"
SOURCE = "Open English WordNet"
POS_NAMES = {"n": "noun", "v": "verb", "a": "adjective", "r": "adverb"}
# WordNet's rules for finding the base form of a regular inflection
_RULES = {
    "n": [("s", ""), ("ses", "s"), ("xes", "x"), ("zes", "z"), ("ches", "ch"), ("shes", "sh"), ("men", "man"),
          ("ies", "y")],
    "v": [("s", ""), ("ies", "y"), ("es", "e"), ("es", ""), ("ed", "e"), ("ed", ""), ("ing", "e"), ("ing", "")],
    "a": [("er", ""), ("est", ""), ("er", "e"), ("est", "e")],
    "r": [],
}
_PYPHEN = {"en": "en_US", "nl": "nl_NL", "de": "de_DE", "fr": "fr", "es": "es", "it": "it_IT", "pt": "pt_PT"}


@dataclass
class Sense:
    """One meaning of a word: its part of speech (noun, verb, ...), the meaning and an example sentence."""
    pos: str  # "noun", "verb", ...
    meaning: str
    example: str = ""


@dataclass
class Entry:
    """What the word card shows for a word: its syllables and, when the dictionary has it, its meanings."""
    word: str  # as it was clicked, cleaned up
    base: str = ""  # the dictionary form the meanings belong to ("run" for "running")
    syllables: list[str] = field(default_factory=list)
    senses: list[Sense] = field(default_factory=list)
    source: str = ""


def clean(word: str) -> str:
    """The word without the punctuation and quotes around it (ligatures such as "ﬁ" written out)."""
    word = unicodedata.normalize("NFKC", word)
    word = word.replace("’", "'").replace("­", "")
    return re.sub(r"^[^\w]+|[^\w]+$", "", word)


_data: Optional[dict] = None


def _load() -> dict:
    """The dictionary data, read once and kept (an empty dictionary when the file is missing or damaged)."""
    global _data
    if _data is None:
        try:
            _data = json.loads(gzip.decompress(DATA.read_bytes()))
        except (OSError, ValueError):
            _data = {"entries": {}, "exc": {}}
    return _data



def _bases(word: str) -> list[tuple[str, str]]:
    """Possible dictionary forms of an English word, with the part of speech they would be."""
    data = _load()
    out = [(p, word) for p in "nvar"]
    for p in "nvar":
        base = data["exc"].get(p, {}).get(word)
        if base:
            out.append((p, base))
        for suffix, ending in _RULES[p]:
            if word.endswith(suffix) and len(word) > len(suffix) + 1:
                out.append((p, word[: len(word) - len(suffix)] + ending))
    return out


def meanings(word: str, per_pos: int = 3) -> tuple[str, list[Sense]]:
    """The dictionary form of an English word and its meanings (most common first)."""
    entries = _load()["entries"]
    w = word.lower()
    if w.endswith("'s"):
        w = w[:-2]
    for candidate in [w] + [b for _, b in _bases(w) if b != w]:
        senses = entries.get(candidate)
        if not senses:
            continue
        if candidate != w:  # keep only the parts of speech the inflection can be ("ran" is a verb)
            fits = {p for p, b in _bases(w) if b == candidate}
            senses = [s for s in senses if s[0] in fits] or senses
        out, counts = [], {}
        for p, meaning, example in senses:
            if counts.get(p, 0) < per_pos:
                counts[p] = counts.get(p, 0) + 1
                out.append(Sense(POS_NAMES.get(p, p), meaning, example))
        return candidate, out
    return "", []


def syllables(word: str, language: str = "en") -> list[str]:
    """The word split into syllables with the hyphenation patterns of its language (pyphen).

    When pyphen or the language's patterns are missing, the whole word comes back as one part.
    """
    try:
        import pyphen
    except ImportError:
        return [word]
    lang = _PYPHEN.get(language, language)
    if not pyphen.language_fallback(lang):
        return [word]
    parts = pyphen.Pyphen(lang=lang).inserted(word, hyphen="‧").split("‧")
    return [p for p in parts if p] or [word]


def lookup(word: str, language: str = "en") -> Entry:
    """Everything the word card needs for a word as it appears in the text (punctuation is removed)."""
    w = clean(word)
    entry = Entry(w, syllables=syllables(w, language) if w else [])
    if w and language == "en":
        entry.base, entry.senses = meanings(w)
        if entry.senses:
            entry.source = SOURCE
    return entry


def online_url(word: str, language: str = "en") -> str:
    """The word on Wiktionary in the document's language (opened in the browser, only when asked)."""
    lang = language if re.fullmatch(r"[a-z]{2,3}", language or "") else "en"
    return f"https://{lang}.wiktionary.org/wiki/{quote(clean(word).lower())}"
