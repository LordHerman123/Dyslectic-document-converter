"""Local dictionary based OCR-error correction.

Pipeline:
 1. detect suspicious words (not in the dictionary, not protected)
 2. generate candidates (dictionary edit-distance candidates plus typical OCR
    confusions such as ``l``/``i``, ``rn``/``m``, ``0``/``o``)
 3. score candidates with a weighted edit distance, word frequency and how
    often the candidate occurs elsewhere in the document
 4. only propose a replacement when one candidate is clearly best

Names, abbreviations, technical terms and the user's custom words are
protected. Corrections are stored separately from the original text.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Iterable, Optional

from rapidfuzz.distance import Levenshtein

from ..model import Block, BlockKind, Correction, Document
from ..settings import app_data_dir

SUPPORTED_LANGUAGES = {"en": "English", "nl": "Dutch", "de": "German", "fr": "French", "es": "Spanish"}

# (wrong, right) substrings typical for OCR, with low substitution cost
OCR_CONFUSIONS = [
    ("rn", "m"), ("m", "rn"), ("l", "i"), ("i", "l"), ("1", "l"), ("1", "i"), ("l", "1"), ("0", "o"),
    ("o", "0"), ("5", "s"), ("8", "B"), ("cl", "d"), ("vv", "w"), ("ii", "u"), ("li", "h"), ("I", "l"),
    ("l", "I"), ("c", "e"), ("e", "c"), ("n", "u"), ("u", "n"), ("h", "b"), ("f", "t"), ("t", "f"),
    ("fi", "ﬁ"), ("|", "l"), ("!", "l"), ("€", "e"), ("é", "e"), ("tl", "d"), ("ri", "n"), ("in", "m"),
]
TOKEN_RE = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)
STOPWORDS = {
    "en": {"the", "and", "of", "to", "in", "is", "that", "for", "it", "with", "as", "was", "on", "are", "this"},
    "nl": {"de", "het", "een", "en", "van", "in", "is", "dat", "op", "te", "zijn", "voor", "met", "niet", "die"},
    "de": {"der", "die", "und", "das", "ist", "nicht", "mit", "den", "von", "zu", "ein", "eine", "auf"},
    "fr": {"le", "la", "les", "et", "des", "est", "une", "dans", "que", "pour", "pas", "sur", "du"},
    "es": {"el", "la", "los", "las", "y", "que", "es", "en", "una", "por", "para", "con", "del"},
}


def detect_language(text: str) -> str:
    words = Counter(w.lower() for w in TOKEN_RE.findall(text[:20000]))
    scores = {lang: sum(words[w] for w in sw) for lang, sw in STOPWORDS.items()}
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "en"


class CustomWords:
    """User dictionary stored as a plain text file (one word per line)."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or (app_data_dir() / "custom_words.txt")
        self.words: set[str] = set()
        try:
            self.words = {w.strip() for w in self.path.read_text(encoding="utf-8").splitlines() if w.strip()}
        except OSError:
            pass

    def add(self, word: str) -> None:
        word = word.strip()
        if word:
            self.words.add(word)
            self._save()

    def remove(self, word: str) -> None:
        self.words.discard(word)
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("\n".join(sorted(self.words, key=str.lower)) + "\n", encoding="utf-8")

    def __contains__(self, word: str) -> bool:
        return word in self.words or word.lower() in {w.lower() for w in self.words}


@lru_cache(maxsize=None)
def _spellchecker(lang: str):
    from spellchecker import SpellChecker

    try:
        return SpellChecker(language=lang, distance=2)
    except Exception:
        return SpellChecker(language="en", distance=2)


class Dictionary:
    """Word lookup for one or more languages (pyspellchecker backend)."""

    def __init__(self, languages: Iterable[str], custom: Optional[CustomWords] = None):
        self.languages = [l for l in languages if l in SUPPORTED_LANGUAGES] or ["en"]
        self.checkers = [_spellchecker(l) for l in self.languages]
        self.custom = custom

    def known(self, word: str) -> bool:
        w = word.lower()
        if self.custom is not None and word in self.custom:
            return True
        return any(w in c for c in self.checkers)

    def frequency(self, word: str) -> float:
        w = word.lower()
        return max((c.word_usage_frequency(w) for c in self.checkers), default=0.0)

    def candidates(self, word: str) -> set[str]:
        w = word.lower()
        out: set[str] = set()
        for c in self.checkers:
            cands = c.candidates(w) if len(w) <= 18 else None
            if cands:
                out |= {x for x in cands if x != w}
        return out


def ocr_variants(word: str, dictionary: Dictionary, max_edits: int = 2) -> dict[str, float]:
    """Dictionary words reachable by undoing typical OCR confusions, with cost."""
    results: dict[str, float] = {}
    frontier = {word: 0.0}
    for _ in range(max_edits):
        nxt: dict[str, float] = {}
        for w, cost in frontier.items():
            for wrong, right in OCR_CONFUSIONS:
                start = 0
                while True:
                    i = w.find(wrong, start)
                    if i < 0:
                        break
                    v = (w[:i] + right + w[i + len(wrong):]).lower()
                    if v != word and (v not in nxt or nxt[v] > cost + 0.3):
                        nxt[v] = cost + 0.3
                    start = i + 1
        frontier = nxt
        for v, cost in nxt.items():
            if v not in results and dictionary.known(v):
                results[v] = cost
    return results


SPELLING_VARIANTS = [("ise", "ize"), ("isation", "ization"), ("ising", "izing"), ("ised", "ized"),
                     ("yse", "yze"), ("our", "or"), ("tre", "ter"), ("ll", "l"), ("ogue", "og"), ("ence", "ense"),
                     ("ae", "e"), ("oe", "e")]


def is_spelling_variant(word: str, dictionary: "Dictionary") -> bool:
    """British/American (and similar) variants of known words are correct spellings."""
    w = word.lower()
    for a, b in SPELLING_VARIANTS:
        for x, y in ((a, b), (b, a)):
            i = w.find(x)
            while i >= 0:
                if dictionary.known(w[:i] + y + w[i + len(x):]):
                    return True
                i = w.find(x, i + 1)
    return False


INFLECTIONS = ("s", "es", "ed", "d", "ing", "ly", "er", "ers", "al", "ally", "ness", "ity", "ies", "ic", "ics")


def _is_inflection(a: str, b: str) -> bool:
    long, short = (a, b) if len(a) > len(b) else (b, a)
    return long.startswith(short) and long[len(short):] in INFLECTIONS


def match_case(template: str, word: str) -> str:
    if template.isupper():
        return word.upper()
    if template[:1].isupper():
        return word[:1].upper() + word[1:]
    return word


class OcrCorrector:
    def __init__(self, dictionary: Dictionary, threshold: float = 0.9):
        self.dictionary = dictionary
        self.threshold = threshold

    # ---------------------------------------------------------------- helpers
    def _protected(self, token: str, text: str, pos: int, doc_counts: Counter) -> bool:
        if len(token) <= 2:
            return True
        letters = re.sub(r"[^A-Za-zÀ-ɏ]", "", token)
        if token.isupper() and len(token) <= 6:
            return True  # abbreviation
        if re.search(r"[a-z][A-Z]", token) and not re.search(r"[0-9|!]", token):
            return True  # camelCase identifiers
        if re.search(r"\d", token) and not re.search(r"[a-z]{2}\d|\d[a-z]{2}", token, re.I):
            return True  # numbers, codes (but "informati0n" is checked)
        if not letters:
            return True
        # capitalised word in the middle of a sentence: likely a name
        before = text[:pos].rstrip()
        if token[:1].isupper() and before and not before.endswith((".", "!", "?", ":", "“", '"')):
            return True
        if doc_counts[token.lower()] >= 3:
            return True  # used consistently: probably a real term
        return False

    def suggest(self, token: str, text: str, pos: int, doc_counts: Counter,
                word_conf: Optional[float] = None) -> Optional[tuple[str, float]]:
        d = self.dictionary
        if d.known(token) or self._protected(token, text, pos, doc_counts):
            return None
        if is_spelling_variant(token, d):
            return None  # e.g. "optimised" is a correct British spelling of "optimized"
        parts = token.split("-")
        if len(parts) > 1 and all(d.known(p) for p in parts if p):
            return None  # valid compound
        lower = token.lower()
        ocr = ocr_variants(lower, d)
        cands = set(ocr) | d.candidates(lower)
        if not cands:
            return None
        scored = []
        for c in cands:
            if _is_inflection(lower, c):
                continue  # e.g. "analytics" vs "analytic": probably a real word
            lev = float(Levenshtein.distance(lower, c))
            dist = min(ocr.get(c, 9.0), lev)
            if dist > 2:
                continue
            freq = d.frequency(c)
            in_doc = doc_counts[c] > 0
            score = dist - 0.08 * math.log10(freq * 1e6 + 1) - (0.35 if in_doc else 0)
            scored.append((score, dist, c, in_doc, freq, c in ocr))
        if not scored:
            return None
        scored.sort()
        best = scored[0]
        second = scored[1] if len(scored) > 1 else None
        _, dist, cand, in_doc, freq, via_ocr = best
        if via_ocr and dist <= 0.6:
            conf = 0.97 if dist <= 0.3 else 0.93
        else:
            # generic spelling edits are not typical OCR errors: never auto-apply
            conf = 0.85 if dist <= 1 else 0.6
        if dist <= 1 and len(token) < 5:
            conf -= 0.1  # short words have many neighbours
        if second is not None:
            margin = second[0] - best[0]
            if margin < 0.15:
                conf -= 0.3
            elif margin < 0.5:
                conf -= 0.1
        if in_doc:
            conf += 0.03
        if word_conf is not None and word_conf >= 0:
            if word_conf > 90:
                conf -= 0.15  # engine was confident: be careful
            elif word_conf < 60:
                conf += 0.02
        conf = max(0.05, min(0.99, conf))
        return match_case(token, cand), round(conf, 2)

    # ------------------------------------------------------------- document
    def correct_document(self, doc: Document, mode: str, include_text_blocks: bool = False) -> list[Correction]:
        """Create corrections for a document.

        ``automatic``: only high-confidence corrections are applied.
        ``review``:    high-confidence corrections are applied, uncertain ones
                       are proposed for the user to accept or reject.
        ``disabled``:  nothing is corrected.
        All corrections can be reverted because the original text is kept.
        """
        if mode == "disabled":
            return []
        blocks = [b for b in doc.blocks if b.text and (b.source == "ocr" or include_text_blocks)
                  and b.kind not in (BlockKind.FURNITURE, BlockKind.REFERENCE, BlockKind.IMAGE, BlockKind.TABLE)]
        counts = Counter(t.lower() for b in doc.blocks for t in TOKEN_RE.findall(b.text))
        corrections: list[Correction] = []
        n = 0
        for b in blocks:
            for m in TOKEN_RE.finditer(b.text):
                token = m.group()
                wc = _word_conf(b, m.start())
                res = self.suggest(token, b.text, m.start(), counts, wc)
                if not res:
                    continue
                replacement, conf = res
                if conf >= self.threshold:
                    status = "auto"
                elif mode == "review" and conf >= 0.5:
                    status = "pending"
                else:
                    continue
                n += 1
                corrections.append(Correction(f"c{n}", b.id, m.start(), m.end(), token, replacement, conf, status))
        return corrections


def _word_conf(block: Block, pos: int) -> Optional[float]:
    for c in block.ocr_confidence:
        if c.start <= pos < c.end:
            return c.confidence
    return None


def dehyphenator(dictionary: Dictionary):
    """Decide whether ``left-`` + ``right`` at a line break is one word."""

    def decide(left: str, right: str) -> bool:
        joined = left + right
        if dictionary.known(joined):
            return True
        if dictionary.known(left) and dictionary.known(right):
            return False  # probably a real compound like "well-known"
        return not (dictionary.known(left) or dictionary.known(right))

    return decide
