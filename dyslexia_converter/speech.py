"""Reading the converted document aloud, with the words it is saying known on the page.

The text comes from the converted PDF itself, so what is heard is what is shown: words with their position
on the page are grouped into sentences, and the speech engine reports which word it is saying, which the
app highlights. Speech uses the voices installed on the computer (Windows, macOS, Linux via eSpeak) through
``pyttsx3``; it works offline and nothing leaves the device. Without a speech engine the feature is simply
unavailable.
"""
from __future__ import annotations

import re
import sys
import threading
from dataclasses import dataclass, field
from typing import Callable, Optional

import pymupdf

Rect = tuple[float, float, float, float]

# words that end with a full stop but do not end a sentence
_ABBREVIATIONS = {"e.g.", "i.e.", "etc.", "et", "al.", "cf.", "vs.", "dr.", "mr.", "mrs.", "ms.", "prof.", "fig.",
                  "figs.", "eq.", "no.", "pp.", "p.", "vol.", "ed.", "eds.", "st.", "approx.", "ca.", "resp.",
                  "incl.", "z.b.", "bzw.", "bijv.", "o.a.", "d.w.z.", "p.ex.", "cf", "ibid."}
MAX_WORDS = 60  # a very long sentence is spoken in parts, so pausing and highlighting stay responsive


@dataclass
class Word:
    text: str  # as spoken (a word hyphenated over two lines is one word)
    page: int
    rects: list[Rect]  # on the page, in PDF points (two for a hyphenated word)
    start: int = 0  # position in the sentence text


@dataclass
class Sentence:
    words: list[Word] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)

    @property
    def page(self) -> int:
        return self.words[0].page if self.words else 0

    def word_at(self, location: int) -> int:
        """Index of the word a speech engine reports by character position.

        Engines count from 0 (Windows) or from 1 (eSpeak): the first word starting at or after
        ``location - 1`` is the one, which is right for both.
        """
        for i, w in enumerate(self.words):
            if w.start >= location - 1:
                return i
        return len(self.words) - 1


def _is_page_number(word: str, y0: float, page_h: float) -> bool:
    return y0 > page_h * 0.92 and bool(re.fullmatch(r"\d{1,4}", word))


def _ends_sentence(word: str, nxt: Optional[str]) -> bool:
    if not re.search(r"[.!?…][\"'”’)\]]*$", word):
        return word.endswith(":") and nxt is not None and nxt[:1].isupper()
    low = word.lower()
    if low in _ABBREVIATIONS or re.fullmatch(r"(?:[A-Za-z]\.)+", word):
        return False  # "e.g.", "A." (an initial)
    return nxt is None or not nxt[:1].islower()


def reading_units(pdf: bytes | str, max_words: int = MAX_WORDS, skip_pages: frozenset = frozenset()) -> list[Sentence]:
    """The converted document as sentences of words with their places on the pages (``skip_pages``: pages
    not to read, such as the table of contents)."""
    doc = pymupdf.open(stream=bytes(pdf), filetype="pdf") if isinstance(pdf, (bytes, bytearray)) \
        else pymupdf.open(pdf)
    raw: list[tuple[str, int, Rect, tuple[int, int]]] = []
    try:
        for pno in range(doc.page_count):
            if pno in skip_pages:
                continue
            page = doc[pno]
            h = page.rect.height
            for x0, y0, x1, y1, text, block, line, _ in page.get_text("words", sort=False):
                if not text.strip() or _is_page_number(text, y0, h):
                    continue
                raw.append((text, pno, (x0, y0, x1, y1), (pno, block)))
    finally:
        doc.close()
    words: list[tuple[Word, tuple[int, int]]] = []
    i = 0
    while i < len(raw):
        text, pno, rect, blk = raw[i]
        rects = [rect]
        # "con-" at the end of a line + "tinues": one word
        while text.endswith(("-", "­")) and len(text) > 2 and i + 1 < len(raw) and raw[i + 1][0][:1].islower() \
                and raw[i + 1][2][1] > rect[1] + 1:
            i += 1
            text = text[:-1] + raw[i][0]
            rects.append(raw[i][2])
        words.append((Word(text, pno, rects), blk))
        i += 1
    sentences: list[Sentence] = []
    cur = Sentence()
    for n, (w, blk) in enumerate(words):
        cur.words.append(w)
        nxt = words[n + 1] if n + 1 < len(words) else None
        end = nxt is None or _ends_sentence(w.text, nxt[0].text) or nxt[1] != blk or len(cur.words) >= max_words
        if end:
            sentences.append(cur)
            cur = Sentence()
    for s in sentences:
        pos = 0
        for w in s.words:
            w.start = pos
            pos += len(w.text) + 1
    return sentences


def first_sentence_on(sentences: list[Sentence], page: int) -> int:
    """Where reading starts when the reader is looking at ``page``."""
    for i, s in enumerate(sentences):
        if any(w.page >= page for w in s.words):
            return i
    return max(0, len(sentences) - 1)


# ------------------------------------------------------------------------------------------ speaking

def _com_init():
    """On Windows the speech engine is a COM object: each thread using it must initialise COM first."""
    if sys.platform != "win32":
        return None
    try:
        import comtypes

        comtypes.CoInitialize()
        return comtypes
    except Exception:
        return None


class Speaker:
    """Speaks sentences one after another on a background thread and reports progress.

    ``on_word(sentence, word)``, ``on_sentence(sentence)`` and ``on_done(finished)`` are called from the
    speech thread. ``stop()`` interrupts at once; reading can then start again from any sentence.
    """

    BASE_RATE = 165  # words per minute at speed 1.0: a calm reading pace

    def __init__(self, engine_factory: Optional[Callable[[], object]] = None):
        self._factory = engine_factory
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._engine = None
        self._available: Optional[bool] = None
        self._voices: Optional[list[tuple[str, str, str]]] = None

    def _make(self):
        if self._factory is not None:
            return self._factory()
        from pyttsx3.engine import Engine

        # a new engine every time: pyttsx3.init() would hand back one made on another thread, and the
        # Windows speech engine must be used on the thread that created it
        return Engine()

    # ---------------------------------------------------------------- facts
    def available(self) -> bool:
        if self._available is None:
            try:
                eng = self._make()
                self._voices = [(v.id, v.name, " ".join(str(x) for x in (getattr(v, "languages", None) or [])))
                                for v in eng.getProperty("voices")]
                self._available = True
                try:
                    eng.stop()
                except Exception:
                    pass
            except Exception:
                self._available = False
                self._voices = []
        return self._available

    def voices(self) -> list[tuple[str, str]]:
        """(id, name) of the installed voices."""
        self.available()
        return [(vid, name) for vid, name, _ in (self._voices or [])]

    def voice_for(self, language: str) -> Optional[str]:
        """A voice for the document's language, if one is installed.

        The voice's language codes decide first ("en", "en-gb"), then its name ("English (America)",
        "Microsoft Zira - English (United States)"); a name that only mentions the language in passing
        ("Chinese, latin as English") does not count.
        """
        self.available()
        names = {"en": "english", "nl": "dutch", "de": "german", "fr": "french", "es": "spanish",
                 "it": "italian", "pt": "portuguese"}
        want = names.get(language, language)
        best, best_score = None, 0
        for vid, name, langs in self._voices or []:
            codes = [c.strip().lower().replace("_", "-") for c in re.split(r"[\s,]+", langs) if c.strip()]
            low = name.lower()
            score = 0
            if language in codes:
                score = 4
            elif any(c.startswith(language + "-") for c in codes):
                score = 3
            elif re.search(rf"(?:^|- ){want}\b", low):
                score = 2
            elif re.search(rf"\b{want}\b", low) and "as " + want not in low:
                score = 1
            if score and (vid.lower().endswith("/" + language) or vid.lower() == language):
                score += 0.5  # the language's main voice, not a regional variant
            if score > best_score:
                best, best_score = vid, score
        return best

    @property
    def speaking(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ---------------------------------------------------------------- control
    def start(self, sentences: list[Sentence], index: int, speed: float = 1.0, voice: Optional[str] = None,
              on_word: Callable[[int, int], None] = lambda s, w: None,
              on_sentence: Callable[[int], None] = lambda s: None,
              on_done: Callable[[bool], None] = lambda finished: None) -> None:
        self.stop()
        self._stop = threading.Event()
        stop = self._stop

        def run():
            finished = False
            com = _com_init()
            try:
                eng = self._make()
                self._engine = eng
                eng.setProperty("rate", int(self.BASE_RATE * max(0.4, min(2.5, speed))))
                if voice:
                    try:
                        eng.setProperty("voice", voice)
                    except Exception:
                        pass
                current = {"s": index}

                def word_cb(name, location, length):
                    if not stop.is_set():
                        s = current["s"]
                        on_word(s, sentences[s].word_at(location))

                eng.connect("started-word", word_cb)
                for si in range(index, len(sentences)):
                    if stop.is_set():
                        break
                    current["s"] = si
                    on_sentence(si)
                    eng.say(sentences[si].text)
                    eng.runAndWait()
                else:
                    finished = not stop.is_set()
            except Exception:
                finished = False
            finally:
                self._engine = None
                if com is not None:
                    com.CoUninitialize()
                on_done(finished)

        self._thread = threading.Thread(target=run, name="read-aloud", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        eng = self._engine
        if eng is not None:
            try:
                eng.stop()
            except Exception:
                pass
        t = self._thread
        if t is not None and t is not threading.current_thread():
            t.join(timeout=2.0)
        self._thread = None
