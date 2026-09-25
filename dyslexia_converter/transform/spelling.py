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

SUPPORTED_LANGUAGES = {"en": "English", "nl": "Dutch", "de": "German", "fr": "French", "es": "Spanish",
                       "it": "Italian", "pt": "Portuguese"}

# (wrong, right) substrings typical for OCR, with low substitution cost
OCR_CONFUSIONS = [
    ("rn", "m"), ("m", "rn"), ("l", "i"), ("i", "l"), ("1", "l"), ("1", "i"), ("l", "1"), ("0", "o"),
    ("o", "0"), ("5", "s"), ("8", "B"), ("cl", "d"), ("vv", "w"), ("ii", "u"), ("li", "h"), ("I", "l"),
    ("l", "I"), ("c", "e"), ("e", "c"), ("n", "u"), ("u", "n"), ("h", "b"), ("f", "t"), ("t", "f"),
    ("y", "v"), ("v", "y"), ("iy", "ry"), ("fi", "ﬁ"), ("|", "l"), ("!", "l"), ("€", "e"), ("é", "e"), ("tl", "d"), ("ri", "n"), ("in", "m"),
]
TOKEN_RE = re.compile(r"[^\W_]+(?:['’\-][^\W_]+)*", re.UNICODE)
STOPWORDS = {
    "en": {"the", "and", "of", "to", "in", "is", "that", "for", "it", "with", "as", "was", "on", "are", "this"},
    "nl": {"de", "het", "een", "en", "van", "in", "is", "dat", "op", "te", "zijn", "voor", "met", "niet", "die"},
    "de": {"der", "die", "und", "das", "ist", "nicht", "mit", "den", "von", "zu", "ein", "eine", "auf"},
    "fr": {"le", "la", "les", "et", "des", "est", "une", "dans", "que", "pour", "pas", "sur", "du"},
    "es": {"el", "la", "los", "las", "y", "que", "es", "en", "una", "por", "para", "con", "del"},
    "it": {"il", "lo", "gli", "le", "di", "che", "non", "per", "una", "sono", "della", "nel", "anche"},
    "pt": {"os", "as", "um", "uma", "que", "não", "para", "com", "por", "dos", "das", "mais", "também"},
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
        self._cand_cache: dict[str, set[str]] = {}

    def _in_dict(self, w: str) -> bool:
        return any(w in c for c in self.checkers)

    def known(self, word: str) -> bool:
        if self.custom is not None and word in self.custom:
            return True
        w = word.lower().replace("\u2019", "'").replace("\u2018", "'")
        if self._in_dict(w):
            return True
        if w.endswith(("'s", "s'")) and self._in_dict(w[:-2] if w.endswith("'s") else w[:-1]):
            return True  # possessives: crown's, forests'
        return self._known_by_parts(w)

    def _known_by_parts(self, w: str) -> bool:
        """Valid derivations of known words: non-sustainable, decentral, collectivizers, ..."""
        if len(w) < 6:
            return False
        for p in PREFIXES:
            if w.startswith(p) and len(w) - len(p) >= 4 and self._in_dict(w[len(p):]):
                return True
        for suf in SUFFIXES:
            if w.endswith(suf) and len(w) - len(suf) >= 4:
                stem = w[: -len(suf)]
                if self._in_dict(stem) or self._in_dict(stem + "e") or (
                        stem.endswith("i") and self._in_dict(stem[:-1] + "y")):
                    return True
        return False

    def foreign_known(self, word: str) -> bool:
        """True if the word is valid in one of the other common languages (loaded on first use).

        Academic texts quote French, German, Latin-rooted terms and so on; such words
        are correct as written and must not be "corrected" into the document language.
        """
        w = word.lower().replace("\u2019", "'")
        if len(w) < 4:
            return False
        others = [l for l in SUPPORTED_LANGUAGES if l not in self.languages]
        return any(w in _spellchecker(l) for l in others)

    def frequency(self, word: str) -> float:
        w = word.lower()
        return max((c.word_usage_frequency(w) for c in self.checkers), default=0.0)

    def candidates(self, word: str) -> set[str]:
        """Known words one edit away (insert, delete, replace or swap one letter).

        Two-edit guesses are slow to compute and almost never confident enough to
        use, so they are left out; typical OCR mix-ups are handled by ``ocr_variants``.
        """
        w = word.lower()
        key = w
        if key in self._cand_cache:
            return self._cand_cache[key]
        out: set[str] = set()
        for c in self.checkers:
            out |= {x for x in c.known(c.edit_distance_1(w)) if x != w}
        self._cand_cache[key] = out
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


PREFIXES = ("non", "de", "un", "re", "pre", "anti", "counter", "over", "under", "post", "sub", "super",
            "inter", "multi", "semi", "co", "mis", "proto", "pseudo", "quasi", "neo", "hyper", "micro", "macro")
SUFFIXES = ("s", "es", "ed", "ing", "er", "ers", "ly", "ness", "ism", "isms", "ist", "ists", "ity", "ities", "al",
            "ally", "ation", "ations", "ize", "izes", "ized", "izer", "izers", "ise", "ised", "able", "ment", "ments")

WORD_ENDINGS = {"tion", "tions", "sion", "sions", "ment", "ments", "ness", "ity", "ities", "ing", "ings", "ly",
                "ally", "ous", "ive", "ives", "ance", "ence", "ure", "ures", "ism", "ist", "ists", "able", "ible",
                "ical", "ated", "ation", "ations", "tive", "tial", "cial", "ture", "tures"}

TRUNCATION_ENDINGS = ("e", "le", "ing", "ed", "es", "er", "ion", "ions", "ity", "al", "ly", "able", "ation", "ment")

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
        if self.dictionary.languages == ["en"] and re.search(r"[\u00C0-\u024F]", token):
            return True  # accented word in an English text: a foreign word or name, not an OCR error
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
        if d.foreign_known(token):
            return None  # a correct word in another language (e.g. a quoted French term)
        low_t = token.lower()
        if low_t in WORD_ENDINGS:
            return None  # the end of a word split across lines ("...tion"): nothing to correct
        if len(low_t) >= 6 and any(d.known(low_t[:i]) and d.known(low_t[i:])
                                   for i in range(2, len(low_t) - 1) if len(low_t[:i]) > 1 and len(low_t[i:]) > 1
                                   and (len(low_t[:i]) > 2 or low_t[:i] in ("a", "an", "to", "of", "in", "on", "at", "is", "it", "be", "by", "or", "as", "we"))
                                   and (len(low_t[i:]) > 2 or low_t[i:] in ("to", "of", "in", "on", "at", "is", "it", "be", "by", "or", "as", "an", "we"))):
            return None  # two words run together ("triesto" = "tries to"): not a misspelling to replace
        if is_spelling_variant(token, d):
            return None  # e.g. "optimised" is a correct British spelling of "optimized"
        if re.search(r"\w['\u2019]\w", token) and not re.search(r"[0-9|!]", token):
            return None  # elisions and foreign forms: l'esprit, d'Alembert
        low = token.lower()
        if len(low) >= 4 and any(d.known(low + suf) for suf in TRUNCATION_ENDINGS):
            return None  # the start of a longer word cut off at the page edge ("strik", "appreciab")
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
            if "'" in c and "'" not in lower.replace("\u2019", "'"):
                continue  # never invent apostrophes (logics -> logic's)
            if c.startswith(lower) or lower.startswith(c) or c.endswith(lower):
                continue  # a cut-off word ("describ"): the missing letters are unknown, don't guess
            if len(lower) <= 3 and c not in ocr:
                continue  # 3-letter words have too many neighbours for generic spelling edits
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
        if len(token) <= 3:
            conf = min(conf, 0.75)  # fragments of cut-off words: never apply automatically
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


def word_rejoiner(dictionary: Dictionary):
    """Decide whether two pieces at a line/page break are one word that lost its hyphen in OCR."""

    def decide(left: str, right: str) -> bool:
        if dictionary.known(left) and dictionary.known(right):
            return False
        return dictionary.known(left + right)

    return decide


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
