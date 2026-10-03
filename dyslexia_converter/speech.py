"""Reading the converted document aloud, with the words it is saying known on the page.

The text comes from the converted PDF itself, so what is heard is what is shown: words with their position
on the page are grouped into sentences, and the speech engine reports which word it is saying, which the
app highlights. Speech uses the voices installed on the computer (Windows, macOS, Linux via eSpeak) through
``pyttsx3``; it works offline and nothing leaves the device. Without a speech engine the feature is simply
unavailable.
"""
from __future__ import annotations

import logging
import re
import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional

import pymupdf

Rect = tuple[float, float, float, float]
log = logging.getLogger(__name__)

# words that end with a full stop but do not end a sentence
_ABBREVIATIONS = {"e.g.", "i.e.", "etc.", "et", "al.", "cf.", "vs.", "dr.", "mr.", "mrs.", "ms.", "prof.", "fig.",
                  "figs.", "eq.", "no.", "pp.", "p.", "vol.", "ed.", "eds.", "st.", "approx.", "ca.", "resp.",
                  "incl.", "z.b.", "bzw.", "bijv.", "o.a.", "d.w.z.", "p.ex.", "cf", "ibid."}
MAX_WORDS = 60  # a very long sentence is spoken in parts, so pausing and highlighting stay responsive


@dataclass
class Word:
    """A word to be read aloud, with the page and rectangle(s) where it is (for highlighting it while it is said)."""
    text: str  # as spoken (a word hyphenated over two lines is one word)
    page: int
    rects: list[Rect]  # on the page, in PDF points (two for a hyphenated word)
    start: int = 0  # position in the sentence text


@dataclass
class Sentence:
    """A sentence (or other reading unit) of words, read aloud in one go by the speech engine."""
    words: list[Word] = field(default_factory=list)

    @property
    def text(self) -> str:
        """The sentence as the speech engine gets it (words joined with spaces)."""
        return " ".join(w.text for w in self.words)

    @property
    def page(self) -> int:
        """The page the sentence starts on."""
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
    """Whether a word is the page number at the foot of a page (it is not read out)."""
    return y0 > page_h * 0.92 and bool(re.fullmatch(r"\d{1,4}", word))


def _ends_sentence(word: str, nxt: Optional[str]) -> bool:
    """Whether a sentence ends after ``word`` (``nxt`` is the next word): full stops of abbreviations and initials do
    not end one.
    """
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


def prepare_reading(sentences: list[Sentence], skip_citations: bool = False,
                    end: Optional[int] = None) -> tuple[list[Sentence], list[list[int]]]:
    """The sentences as they are read aloud: without in-text citations ("(Smith, 2019)", "[3]", "[Note 2]") when
    ``skip_citations``, and without anything from sentence ``end`` on (the reference list and notes at the end).
    Returns them with, for each, the numbers of the original words kept, so the highlight marks the right word.
    A sentence that was only a citation has no words left (it is passed over)."""
    from .audio_export import citation_spans

    out, maps = [], []
    for si, s in enumerate(sentences if end is None else sentences[:end]):
        keep = list(range(len(s.words)))
        if skip_citations and s.words:
            text, starts, pos = "", [], 0
            for w in s.words:
                starts.append(len(text))
                text += w.text + " "
            spans = citation_spans(text)
            if spans:
                keep = [k for k in keep if not any(a <= starts[k] < b or a < starts[k] + len(s.words[k].text) <= b
                                                     for a, b in spans)]
        words, pos, kept = [], 0, set(keep)
        for k, w in enumerate(s.words):
            if k in kept:
                words.append(Word(w.text, w.page, w.rects, pos))
                pos += len(w.text) + 1
            elif words:
                # punctuation after a citation ("2014).") stays with the word before it, so the sentence still ends
                tail = re.sub(r"^.*?[)\]]", "", w.text) if re.search(r"[)\]]", w.text) else ""
                if tail and not re.search(r"\w", tail):
                    words[-1] = Word(words[-1].text + tail, words[-1].page, words[-1].rects, words[-1].start)
                    pos += len(tail)
        out.append(Sentence(words))
        maps.append(keep)
    return out, maps


def sentence_at(sentences: list[Sentence], page: int, x: float, y: float) -> Optional[int]:
    """The sentence of the word nearest to a point on a page (a click on the preview)."""
    best, best_d = None, None
    for si, s in enumerate(sentences):
        for w in s.words:
            if w.page != page:
                continue
            for x0, y0, x1, y1 in w.rects:
                dx = max(x0 - x, 0.0, x - x1)
                dy = max(y0 - y, 0.0, y - y1)
                d = dx * dx + (dy * 3) ** 2  # a line above or below counts more than a gap in the line
                if best_d is None or d < best_d:
                    best, best_d = si, d
    return best


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
        import pythoncom

        pythoncom.CoInitialize()
        return pythoncom
    except Exception:
        return None


# Windows language ids (the low bits of an LCID, as SAPI voices report them) -> language codes
_LANG_IDS = {0x09: "en", 0x13: "nl", 0x07: "de", 0x0C: "fr", 0x0A: "es", 0x10: "it", 0x16: "pt"}


class SapiEngine:
    """The Windows speech engine (SAPI), used directly.

    Speaking is started asynchronously on the reading thread, which also runs the Windows message loop,
    so the engine's word events arrive there (with pyttsx3 they did not, which left reading aloud
    silent). The engine's status is polled as well, in case events are not available. Offers the small
    part of the pyttsx3 engine interface the Speaker uses. ``output_wav``: speak into a WAV file instead
    of the speakers (for tests on machines without sound).
    """

    POLL_MS = 60
    DEFAULT_WPM = 180  # SAPI rate 0

    def __init__(self, output_wav: Optional[str] = None):
        """Connect to SAPI's voice; ``output_wav`` writes the speech to a WAV file instead of the speakers (for
        tests).
        """
        import win32com.client

        self._events = 0
        self._last = -1
        sink = self._word

        class _Events:
            """Receives SAPI's events on the speaking thread."""
            def OnWord(self, stream_number, stream_position, character_position, length):  # noqa: N802
                """SAPI starts a word: pass its position in the text on."""
                sink(int(character_position), int(length), event=True)

        self.mode = "events"
        try:
            self._voice = win32com.client.DispatchWithEvents("SAPI.SpVoice", _Events)
            self._voice.EventInterests = 33790  # SVEAllEvents: includes word boundaries
        except Exception as e:  # no type library wrappers: poll the status only
            log.info("SAPI events unavailable; polling the speech status", exc_info=True)
            self.mode = f"polling ({type(e).__name__}: {e})"
            self._voice = win32com.client.Dispatch("SAPI.SpVoice")
        self._stream = None
        if output_wav:
            self._stream = win32com.client.Dispatch("SAPI.SpFileStream")
            self._stream.Open(output_wav, 3)  # SSFMCreateForWrite
            self._voice.AudioOutputStream = self._stream
        self._cb = None
        self._text = ""
        self._stopped = False

    def getProperty(self, key: str):
        """pyttsx3-style: the installed SAPI voices with their languages (``key`` = "voices")."""
        if key != "voices":
            return None
        out = []
        tokens = self._voice.GetVoices()
        for i in range(tokens.Count):
            tok = tokens.Item(i)
            langs = []
            try:
                for part in str(tok.GetAttribute("Language")).split(";"):
                    code = _LANG_IDS.get(int(part, 16) & 0x3FF)
                    if code:
                        langs.append(code)
            except Exception:
                pass
            out.append(_VoiceInfo(tok.Id, tok.GetDescription(), langs))
        return out

    def setProperty(self, key: str, value) -> None:
        """pyttsx3-style: set the speed (words per minute) or the voice (its id)."""
        if key == "rate":  # words per minute -> SAPI's -10..10 (10 = three times as fast)
            import math

            rate = 10 * math.log(max(0.1, float(value) / self.DEFAULT_WPM)) / math.log(3)
            self._voice.Rate = max(-10, min(10, int(round(rate))))
        elif key == "voice":
            tokens = self._voice.GetVoices()
            for i in range(tokens.Count):
                if tokens.Item(i).Id == value:
                    self._voice.Voice = tokens.Item(i)
                    break

    def connect(self, name: str, cb) -> None:
        """pyttsx3-style: the callback for each word ("started-word")."""
        if name == "started-word":
            self._cb = cb

    def say(self, text: str) -> None:
        """pyttsx3-style: the text to speak on the next :meth:`runAndWait`."""
        self._text = text

    def _word(self, pos: int, length: int, event: bool = False) -> None:
        """A word starts (from an event, or seen in the status): report each word once, in order."""
        if event:
            self._events += 1
        if pos > self._last and length > 0 and self._cb is not None:
            self._last = pos
            self._cb(None, pos, length)

    def runAndWait(self) -> None:
        """Speak the text and wait until done or stopped, reporting words as SAPI reaches them."""
        import pythoncom

        if self._stopped:
            return
        self._last = -1
        self._voice.Speak(self._text, 1 | 2)  # SVSFlagsAsync | SVSFPurgeBeforeSpeak
        while True:
            pythoncom.PumpWaitingMessages()  # delivers the word events on this thread
            done = self._voice.WaitUntilDone(self.POLL_MS)
            if self._stopped:
                self._voice.Speak("", 1 | 2)  # stop at once
                return
            if not self._events:  # no events (yet): read the word from the status
                st = self._voice.Status
                self._word(int(st.InputWordPosition), int(st.InputWordLength))
            if done:
                pythoncom.PumpWaitingMessages()  # the last events
                return

    def stop(self) -> None:
        """Stop speaking (from another thread)."""
        self._stopped = True  # the speaking thread sees this within POLL_MS and stops the voice

    def diagnostics(self) -> dict:
        """What happened, for finding problems on a particular computer."""
        info = {"mode": self.mode, "events": self._events, "last_word_at": self._last}
        try:
            st = self._voice.Status
            info.update(running=st.RunningState, word_pos=st.InputWordPosition, word_len=st.InputWordLength,
                        last_result=st.LastHResult, voice=self._voice.Voice.GetDescription())
        except Exception as e:
            info["status_error"] = repr(e)
        return info

    def close(self) -> None:
        """Close the WAV file when writing to one."""
        if self._stream is not None:
            self._stream.Close()
            self._stream = None


def _lang_code(tag: str) -> list[str]:
    """ "nl-NL" -> ["nl", "nl-nl"] (the language, then the exact tag)."""
    t = (tag or "").strip().lower().replace("_", "-")
    return [t.split("-")[0], t] if t else []


class WinRtEngine:
    """The modern Windows speech engine (Windows 10/11).

    Unlike SAPI it sees every voice installed in Windows Settings (Time & language > Speech), so documents
    in Dutch, German, French, ... are read with a voice for their language. It makes the audio and reports
    when each word starts, so the highlight follows the voice exactly: the audio is played and the words
    are reported at their times. Offers the part of the pyttsx3 engine interface the Speaker uses.
    ``play=False`` makes the audio without playing it (tests on machines without sound).
    """

    DEFAULT_WPM = 170  # speaking rate 1.0

    def __init__(self, play: bool = True):
        """Use Windows' modern speech; ``play`` False only synthesises (tests, where there are no speakers)."""
        from winrt.windows.media.speechsynthesis import SpeechSynthesizer

        self._cls = SpeechSynthesizer
        self._synth = SpeechSynthesizer()
        self._synth.options.include_word_boundary_metadata = True
        self._play = play
        self._cb = None
        self._text = ""
        self._stopped = False
        self.last_wav = b""
        self.last_words: list[tuple[float, int, int]] = []  # (seconds, position, length) of the last text

    def getProperty(self, key: str):
        """pyttsx3-style: every installed modern voice with its language (``key`` = "voices")."""
        if key != "voices":
            return None
        return [_VoiceInfo(v.id, f"{v.display_name} ({v.language})", _lang_code(v.language))
                for v in self._cls.all_voices]

    def setProperty(self, key: str, value) -> None:
        """pyttsx3-style: set the speed (words per minute) or the voice (its id)."""
        if key == "rate":
            self._synth.options.speaking_rate = max(0.5, min(6.0, float(value) / self.DEFAULT_WPM))
        elif key == "voice":
            for v in self._cls.all_voices:
                if v.id == value:
                    self._synth.voice = v
                    break

    def connect(self, name: str, cb) -> None:
        """pyttsx3-style: the callback for each word ("started-word")."""
        if name == "started-word":
            self._cb = cb

    def say(self, text: str) -> None:
        """pyttsx3-style: the text to speak on the next :meth:`runAndWait`."""
        self._text = text

    async def _synthesize(self, text: str) -> tuple[bytes, list[tuple[float, int, int]]]:
        """The spoken text as WAV bytes, and when each word starts: (seconds, position in the text, length)."""
        from winrt.windows.media.core import SpeechCue
        from winrt.windows.storage.streams import DataReader

        stream = await self._synth.synthesize_text_to_stream_async(text)
        words = []
        for track in stream.timed_metadata_tracks:
            for cue in track.cues:
                c = cue.as_(SpeechCue)
                pos = c.start_position_in_input
                pos = getattr(pos, "value", pos)
                if pos is None:
                    continue
                end = c.end_position_in_input
                end = getattr(end, "value", end)
                length = (end - pos + 1) if end is not None else len(c.text or "")
                words.append((c.start_time.total_seconds(), int(pos), max(1, int(length))))
        words.sort()
        size = int(stream.size)
        reader = DataReader(stream.get_input_stream_at(0))
        await reader.load_async(size)
        buf = bytearray(size)
        reader.read_bytes(buf)
        return bytes(buf), words

    def to_wav(self, text: str) -> bytes:
        """The spoken text as WAV bytes (for saving as audio), without playing it."""
        import asyncio

        return asyncio.run(self._synthesize(text))[0]

    def runAndWait(self) -> None:
        """Synthesise the text, then play it and report each word at its time (or report them at once without
        playing).
        """
        import asyncio

        if self._stopped:
            return
        self.last_wav, self.last_words = asyncio.run(self._synthesize(self._text))
        if not self._play:
            for _, pos, length in self.last_words:
                if self._stopped:
                    return
                if self._cb is not None:
                    self._cb(None, pos, length)
            return
        self._play_and_follow()

    def _play_and_follow(self) -> None:
        """Play the WAV and call the word callback as each word's time comes; stops the sound when stopped."""
        play_following(self.last_wav, self.last_words, self._cb, lambda: self._stopped)

    def stop(self) -> None:
        """Stop speaking (from another thread)."""
        self._stopped = True


def _player() -> Optional[list[str]]:
    """A command that plays a WAV file on Linux or macOS (Windows plays it itself), or None."""
    import shutil

    for cmd in (["afplay"], ["paplay"], ["aplay", "-q"], ["pw-play"], ["ffplay", "-nodisp", "-autoexit", "-loglevel",
                                                                      "quiet"]):
        if shutil.which(cmd[0]):
            return cmd
    return None


def play_following(wav: bytes, words: list[tuple[float, int, int]], cb, stopped: Callable[[], bool]) -> None:
    """Play ``wav`` and call ``cb(None, position, length)`` as each word's time (seconds) comes; stops the sound
    as soon as ``stopped()`` is true."""
    import os
    import subprocess
    import tempfile

    duration = _wav_seconds(wav)
    fd, path = tempfile.mkstemp(suffix=".wav", prefix="dc-read-")
    proc = None
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(wav)
        if sys.platform == "win32":
            import winsound

            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        else:
            cmd = _player()
            if cmd is None:
                raise RuntimeError("no program to play sound was found (install pulseaudio-utils or alsa-utils)")
            proc = subprocess.Popen(cmd + [path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        t0 = time.monotonic()
        pending = list(words)
        while True:
            now = time.monotonic() - t0
            while pending and pending[0][0] <= now:
                _, pos, length = pending.pop(0)
                if cb is not None:
                    cb(None, pos, length)
            if stopped():
                return
            if now >= duration and (proc is None or proc.poll() is not None):
                return
            nxt = pending[0][0] - now if pending else max(0.0, duration - now)
            time.sleep(max(0.01, min(0.05, nxt)))
    finally:
        if sys.platform == "win32":
            try:
                import winsound

                winsound.PlaySound(None, 0)  # stop the sound
            except Exception:
                pass
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=1)
            except Exception:
                proc.kill()
        try:
            os.remove(path)
        except OSError:
            pass


def word_times(text: str, parts: list[tuple[float, list[str]]]) -> list[tuple[float, int, int]]:
    """When each word of ``text`` starts, for a voice that does not say so itself: ``parts`` are the pieces it
    spoke, each (seconds of sound, its sounds (phonemes) with " " between words). Each word gets time in
    proportion to its sounds, with a pause after commas and full stops; when the voice split the words
    differently (it says "2019" as two words), in proportion to its letters. (seconds, position, length)."""
    words = [(m.start(), m.end() - m.start(), m.group()) for m in re.finditer(r"\S+", text)]
    if not words:
        return []
    spoken: list[tuple[float, float]] = []  # (start, weight) of each spoken word, in the order said
    weights: list[list[float]] = []
    t0 = 0.0
    for seconds, phonemes in parts:
        groups, cur = [], 0.0
        for ph in phonemes:
            if ph == " ":
                groups.append(cur)
                cur = 0.0
            elif ph in ",;:":
                cur += 3.0  # a short pause
            elif ph in ".!?":
                cur += 5.0
            elif not ph.strip() or ph in "ˈˌː":
                continue  # stress and length marks take no time of their own
            else:
                cur += 1.0
        groups.append(cur)
        groups = [g for g in groups if g > 0]
        weights.append(groups)
        total = sum(groups) or 1.0
        acc = 0.0
        for g in groups:
            spoken.append((t0 + seconds * acc / total, g))
            acc += g
        t0 += seconds
    if len(spoken) == len(words):
        return [(start, pos, length) for (start, _), (pos, length, _) in zip(spoken, words)]
    total_s = sum(seconds for seconds, _ in parts)
    letters = [len(w) + (3 if w[-1] in ",;:" else 5 if w[-1] in ".!?" else 1) for _, _, w in words]
    out, acc, total = [], 0.0, float(sum(letters))
    for (pos, length, _), n in zip(words, letters):
        out.append((total_s * acc / total, pos, length))
        acc += n
    return out


class PiperEngine:
    """A natural (Piper) voice, offline: it makes the sound of each sentence on this device, plays it and reports
    each word as it comes (times worked out from the sounds of the words, see :func:`word_times`). Offers the
    part of the pyttsx3 engine interface the Speaker uses. ``play=False`` only makes the sound (tests)."""

    DEFAULT_WPM = 165  # speaking rate 1.0
    reports_words = True  # every word is reported (the Speaker need not guess the pace)
    _models: dict = {}  # loaded voices, kept: loading takes a second

    def __init__(self, key: str, play: bool = True):
        """Use the downloaded natural voice ``key`` (see :mod:`dyslexia_converter.voices`)."""
        from . import voices

        self.key = key
        self._path = str(voices.model_path(key))
        self._play = play
        self._cb = None
        self._text = ""
        self._stopped = False
        self._length = 1.0
        self.last_wav = b""
        self.last_words: list[tuple[float, int, int]] = []
        self._ready: dict[str, threading.Thread] = {}  # sentences being made in advance
        self._made: dict[str, tuple[bytes, list]] = {}

    def prepare(self, text: str) -> None:
        """Start making the sound of the next sentence while this one is said (no pause between them)."""
        if text in self._ready or not text.strip():
            return

        def make():
            try:
                self._made[text] = self.synthesize(text)
            except Exception:
                log.debug("preparing the next sentence failed", exc_info=True)

        th = threading.Thread(target=make, name="read-aloud-next", daemon=True)
        self._ready[text] = th
        th.start()

    def _voice(self):
        """The loaded voice (loaded once per app run)."""
        from piper import PiperVoice

        if self._path not in PiperEngine._models:
            PiperEngine._models[self._path] = PiperVoice.load(self._path)
        return PiperEngine._models[self._path]

    def getProperty(self, key: str):
        """pyttsx3-style: this voice (``key`` = "voices")."""
        from . import voices

        v = voices.BY_KEY.get(self.key)
        return [_VoiceInfo(voices.PREFIX + self.key, v.name if v else self.key, [v.language] if v else [])] \
            if key == "voices" else None

    def setProperty(self, key: str, value) -> None:
        """pyttsx3-style: the speed (words per minute); the voice is chosen when the engine is made."""
        if key == "rate":
            self._length = max(0.4, min(2.5, self.DEFAULT_WPM / max(1.0, float(value))))

    def connect(self, name: str, cb) -> None:
        """pyttsx3-style: the callback for each word ("started-word")."""
        if name == "started-word":
            self._cb = cb

    def say(self, text: str) -> None:
        """pyttsx3-style: the text to speak on the next :meth:`runAndWait`."""
        self._text = text

    def synthesize(self, text: str) -> tuple[bytes, list[tuple[float, int, int]]]:
        """The spoken text as WAV bytes, and when each word starts."""
        import io
        import wave

        from piper import SynthesisConfig

        voice = self._voice()
        audio, parts, rate = bytearray(), [], 22050
        for chunk in voice.synthesize(text, syn_config=SynthesisConfig(length_scale=self._length)):
            rate = chunk.sample_rate
            audio += chunk.audio_int16_bytes
            parts.append((len(chunk.audio_int16_bytes) / 2 / rate, list(chunk.phonemes or [])))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(rate)
            w.writeframes(bytes(audio))
        return buf.getvalue(), word_times(text, parts)

    def to_wav(self, text: str) -> bytes:
        """The spoken text as WAV bytes (for saving as audio), without playing it."""
        return self.synthesize(text)[0]

    def runAndWait(self) -> None:
        """Make the sound of the text, then play it and report each word at its time (or report them at once
        without playing)."""
        if self._stopped or not self._text.strip():
            return
        th = self._ready.pop(self._text, None)
        if th is not None:
            th.join()
        made = self._made.pop(self._text, None)
        self.last_wav, self.last_words = made if made is not None else self.synthesize(self._text)
        if not self._play:
            for _, pos, length in self.last_words:
                if self._stopped:
                    return
                if self._cb is not None:
                    self._cb(None, pos, length)
            return
        play_following(self.last_wav, self.last_words, self._cb, lambda: self._stopped)

    def stop(self) -> None:
        """Stop speaking (from another thread)."""
        self._stopped = True


def _wav_seconds(data: bytes) -> float:
    """Length of a WAV file's sound."""
    import io
    import wave

    try:
        with wave.open(io.BytesIO(data)) as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except Exception:
        return 0.0


@dataclass
class _VoiceInfo:
    """A voice as pyttsx3 describes it: id, name and languages."""
    id: str
    name: str
    languages: list


class Speaker:
    """Speaks sentences one after another on a background thread and reports progress.

    ``on_word(sentence, word)``, ``on_sentence(sentence)`` and ``on_done(finished)`` are called from the
    speech thread. ``stop()`` interrupts at once; reading can then start again from any sentence.
    """

    BASE_RATE = 165  # words per minute at speed 1.0: a calm reading pace
    WAIT_FOR_WORDS = 0.35  # seconds to wait for the engine to report words before pacing the highlight

    def __init__(self, engine_factory: Optional[Callable[[], object]] = None):
        """``engine_factory`` makes the speech engine (tests pass a fake); by default the best one for the
        platform.
        """
        self._factory = engine_factory
        self._thread: Optional[threading.Thread] = None
        self._stop = threading.Event()
        self._engine = None
        self._available: Optional[bool] = None
        self._voices: Optional[list[tuple[str, str, str]]] = None
        self.last_error = ""  # why speaking failed, for the user

    def _make(self, voice: Optional[str] = None):
        """A speech engine: a natural voice when ``voice`` is one, else on Windows the modern voices (exact word
        timings), else SAPI, else pyttsx3."""
        from . import voices as natural

        if self._factory is not None:
            return self._factory()
        nv = natural.voice_of(voice)
        if nv is not None:
            return PiperEngine(nv.key)
        if sys.platform == "win32":
            try:
                eng = WinRtEngine()  # all installed voices, exact word timings
                if eng.getProperty("voices"):
                    return eng
            except Exception:
                log.info("modern Windows speech unavailable, using SAPI", exc_info=True)
            try:
                return SapiEngine()
            except Exception:
                log.warning("Windows speech (SAPI) unavailable, trying pyttsx3", exc_info=True)
        from pyttsx3.engine import Engine

        # a new engine every time: pyttsx3.init() would hand back one made on another thread, and the
        # Windows speech engine must be used on the thread that created it
        return Engine()

    # ---------------------------------------------------------------- facts
    def available(self) -> bool:
        """Whether this device can speak at all (checked once; the voices are remembered)."""
        if self._available is None:
            _com_init()
            try:
                eng = self._make()
                self._voices = [(v.id, v.name, " ".join(str(x) for x in (getattr(v, "languages", None) or [])))
                                for v in eng.getProperty("voices")]
                self._available = True
                try:
                    eng.stop()
                except Exception:
                    pass
            except Exception as e:
                log.warning("No speech engine: %s", e, exc_info=True)
                self.last_error = f"{type(e).__name__}: {e}"
                self._available = False
                self._voices = []
            if self._factory is None:
                natural = self._natural_voices()
                if natural:  # natural voices first; they work without the computer's own voices too
                    self._voices = natural + (self._voices or [])
                    self._available = True
        return self._available

    @staticmethod
    def _natural_voices() -> list[tuple[str, str, str]]:
        """The downloaded natural voices, as (id, name, language)."""
        from . import voices as natural

        if not natural.supported():
            return []
        return [(v.id, f"{v.name} ({v.region}) - natural", v.language) for v in natural.installed()]

    def refresh(self) -> None:
        """Look for voices again (after a natural voice was downloaded or removed)."""
        self._available = None
        self._voices = None

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
            if score and vid.startswith("piper:"):
                score += 5  # a natural voice for the language sounds best
            if score > best_score:
                best, best_score = vid, score
        return best

    def render_many(self, texts: Iterable[str], speed: float = 1.0, voice: Optional[str] = None):
        """Speak ``texts`` into sound instead of the speakers: yields the WAV bytes of each text, in order (for
        saving as audio; runs on a worker thread). Uses the same voice and speed as reading aloud."""
        import os
        import tempfile

        com = _com_init()
        try:
            eng = self._make(voice)
            if isinstance(eng, SapiEngine):  # SAPI speaks into a file: one per text
                eng.close()
                eng = None
            else:
                eng.setProperty("rate", int(self.BASE_RATE * max(0.4, min(2.5, speed))))
                if voice:
                    try:
                        eng.setProperty("voice", voice)
                    except Exception:
                        pass
            for text in texts:
                if not text.strip():
                    continue
                if eng is not None and hasattr(eng, "to_wav"):
                    yield eng.to_wav(text)
                    continue
                fd, path = tempfile.mkstemp(suffix=".wav", prefix="dc-audio-")
                os.close(fd)
                try:
                    if eng is None:  # SAPI
                        sapi = SapiEngine(output_wav=path)
                        sapi.setProperty("rate", int(self.BASE_RATE * max(0.4, min(2.5, speed))))
                        if voice:
                            sapi.setProperty("voice", voice)
                        sapi.say(text)
                        sapi.runAndWait()
                        sapi.close()
                    else:  # pyttsx3 (eSpeak, macOS): its own way of saving
                        eng.save_to_file(text, path)
                        eng.runAndWait()
                    with open(path, "rb") as f:
                        yield f.read()
                finally:
                    try:
                        os.remove(path)
                    except OSError:
                        pass
        finally:
            if com is not None:
                com.CoUninitialize()

    @property
    def speaking(self) -> bool:
        """Whether a sentence is being read right now."""
        return self._thread is not None and self._thread.is_alive()

    # ---------------------------------------------------------------- control
    def start(self, sentences: list[Sentence], index: int, speed: float = 1.0, voice: Optional[str] = None,
              on_word: Callable[[int, int], None] = lambda s, w: None,
              on_sentence: Callable[[int], None] = lambda s: None,
              on_done: Callable[[bool], None] = lambda finished: None) -> None:
        """Read ``sentences`` from number ``index`` in a background thread.

        ``speed`` is relative to normal (1.0); ``voice`` is a voice id. The callbacks are called from the
        speech thread: ``on_word(sentence, word)`` as each word is said, ``on_sentence(sentence)`` at the
        start of each sentence and ``on_done(finished)`` at the end (False when stopped or failed;
        ``last_error`` says why).
        """
        self.stop()
        self._stop = threading.Event()
        stop = self._stop
        self.last_error = ""

        def run():
            """The speech thread: speak sentence by sentence, reporting words (paced by an estimate when the
            engine reports none).
            """
            finished = False
            com = _com_init()
            try:
                eng = self._make(voice)
                self._engine = eng
                eng.setProperty("rate", int(self.BASE_RATE * max(0.4, min(2.5, speed))))
                if voice:
                    try:
                        eng.setProperty("voice", voice)
                    except Exception:
                        pass
                current = {"s": index}
                real = {"seen": False}  # the engine reports the word it is saying
                # characters per second, to pace the highlight when the engine does not say which word it is
                # on; calibrated with the time each sentence really took
                pace = {"cps": self.BASE_RATE * max(0.4, min(2.5, speed)) * 6.0 / 60.0}

                def word_cb(name, location, length):
                    """The engine says a word: report which word of the current sentence it is."""
                    if not stop.is_set():
                        real["seen"] = True
                        s = current["s"]
                        on_word(s, sentences[s].word_at(location))

                def estimate(si: int, t0: float, sentence_done: threading.Event) -> None:
                    """Move the highlight along the sentence by the length of its words."""
                    if sentence_done.wait(self.WAIT_FOR_WORDS) or real["seen"]:
                        return
                    for wi, w in enumerate(sentences[si].words):
                        if wi == 0:
                            continue  # the first word is shown when the sentence starts
                        wait = w.start / pace["cps"] - (time.monotonic() - t0)
                        if (wait > 0 and sentence_done.wait(wait)) or stop.is_set() or real["seen"]:
                            return
                        on_word(si, wi)

                eng.connect("started-word", word_cb)
                for si in range(index, len(sentences)):
                    if stop.is_set():
                        break
                    if not sentences[si].words:
                        continue  # nothing left to say (only a citation)
                    current["s"] = si
                    on_sentence(si)
                    sentence_done = threading.Event()
                    t0 = time.monotonic()
                    pacer = None
                    if not real["seen"] and not getattr(eng, "reports_words", False):
                        pacer = threading.Thread(target=estimate, args=(si, t0, sentence_done), daemon=True)
                        pacer.start()
                    eng.say(sentences[si].text)
                    if hasattr(eng, "prepare") and si + 1 < len(sentences):
                        eng.prepare(sentences[si + 1].text)
                    eng.runAndWait()
                    took = time.monotonic() - t0
                    sentence_done.set()
                    if pacer is not None:
                        pacer.join(1.0)
                    if took > 0.5 and not stop.is_set():  # learn how fast this voice really speaks
                        pace["cps"] = 0.6 * pace["cps"] + 0.4 * (len(sentences[si].text) + 1) / took
                else:
                    finished = not stop.is_set()
            except Exception as e:  # tell the user instead of staying silent
                log.exception("reading aloud failed")
                self.last_error = f"{type(e).__name__}: {e}"
                finished = False
            finally:
                eng_done = self._engine
                self._engine = None
                if eng_done is not None and hasattr(eng_done, "close"):
                    try:
                        eng_done.close()
                    except Exception:
                        pass
                if com is not None:
                    com.CoUninitialize()
                on_done(finished)

        self._thread = threading.Thread(target=run, name="read-aloud", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop reading and wait (briefly) for the speech thread to end."""
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
