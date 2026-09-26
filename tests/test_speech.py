"""Reading aloud: sentences with their place on the page, word tracking, stopping, and choosing a voice."""
import threading
import time

import pymupdf

from dyslexia_converter import pipeline, speech
from dyslexia_converter.settings import FormatSettings


def make_pdf(pages):
    """A PDF with the given lines of text per page, plus a page number at the bottom."""
    doc = pymupdf.open()
    for n, lines in enumerate(pages):
        page = doc.new_page(width=595, height=842)
        y = 80
        for line in lines:
            page.insert_text((72, y), line, fontsize=12)
            y += 18
        page.insert_text((290, 820), str(n + 1), fontsize=9)
    return doc.tobytes()


def test_sentences_words_and_pages():
    pdf = make_pdf([["The first sentence is short. The second one, e.g. with an", "abbreviation, runs on to the",
                     "next line and is hyphen-", "ated here. Is it done?"],
                    ["A new page starts here."]])
    units = speech.reading_units(pdf)
    texts = [s.text for s in units]
    assert texts[0] == "The first sentence is short."
    assert texts[1].startswith("The second one, e.g. with an abbreviation") and "hyphenated here." in texts[1]
    assert texts[2] == "Is it done?"
    assert texts[-1] == "A new page starts here." and units[-1].page == 1
    assert not any(w.text in ("1", "2") for s in units for w in s.words)  # page numbers are not read
    joined = next(w for w in units[1].words if w.text == "hyphenated")
    assert len(joined.rects) == 2  # highlighted on both lines
    # where reading starts for a page, and pages that are skipped (the contents)
    assert speech.first_sentence_on(units, 1) == len(units) - 1
    assert speech.first_sentence_on(units, 99) == len(units) - 1
    assert [s.page for s in speech.reading_units(pdf, skip_pages=frozenset({0}))] == [1]
    assert speech.reading_units(make_pdf([[]])) == []  # nothing to read


def test_word_positions_from_either_kind_of_engine():
    s = speech.Sentence([speech.Word(w, 0, [(0, 0, 1, 1)]) for w in ("Hello", "there,", "reader.")])
    pos = 0
    for w in s.words:
        w.start, pos = pos, pos + len(w.text) + 1
    for zero_based in (0, 6, 13):  # Windows counts from 0
        assert s.word_at(zero_based) == [0, 6, 13].index(zero_based)
    for one_based in (1, 7, 14):  # eSpeak counts from 1
        assert s.word_at(one_based) == [1, 7, 14].index(one_based)
    assert s.word_at(999) == 2


def test_very_long_sentences_are_read_in_parts():
    pdf = make_pdf([[" ".join(["word"] * 10)] * 16])
    units = speech.reading_units(pdf, max_words=50)
    assert all(len(s.words) <= 50 for s in units) and sum(len(s.words) for s in units) == 160


class FakeEngine:
    instances = []

    def __init__(self, delay=0.0, fail=False):
        if fail:
            raise RuntimeError("no speech engine")
        self.delay, self.cb, self.said, self.props, self.stopped = delay, None, [], {}, False
        FakeEngine.instances.append(self)

    def getProperty(self, key):
        class V:
            def __init__(self, vid, name, langs):
                self.id, self.name, self.languages = vid, name, langs
        return [V("sit/cmn", "Chinese (Mandarin, latin as English)", ["cmn"]),
                V("TTS_MS_NL-NL_FRANK", "Microsoft Frank - Dutch (Netherlands)", []),
                V("gmw/en-029", "English (Caribbean)", ["en-029"]),
                V("gmw/en", "English (Great Britain)", ["en-gb"])]

    def setProperty(self, key, value):
        self.props[key] = value

    def connect(self, name, cb):
        self.cb = cb

    def say(self, text):
        self.said.append(text)

    def runAndWait(self):
        pos = 0
        for w in self.said[-1].split(" "):
            if self.stopped:
                return
            self.cb(None, pos, len(w))
            pos += len(w) + 1
            time.sleep(self.delay)

    def stop(self):
        self.stopped = True


def units_of(*sentences):
    out = []
    for text in sentences:
        s = speech.Sentence([speech.Word(w, 0, [(0, 0, 1, 1)]) for w in text.split()])
        pos = 0
        for w in s.words:
            w.start, pos = pos, pos + len(w.text) + 1
        out.append(s)
    return out


def test_speaker_reads_from_a_sentence_and_reports_words():
    sp = speech.Speaker(engine_factory=FakeEngine)
    assert sp.available()
    units = units_of("One two.", "Three four five.", "Six.")
    words, done = [], threading.Event()
    result = {}
    sp.start(units, 1, speed=2.0, voice="gmw/en", on_word=lambda s, w: words.append((s, w)),
             on_done=lambda finished: (result.update(finished=finished), done.set()))
    assert done.wait(5)
    assert words == [(1, 0), (1, 1), (1, 2), (2, 0)] and result["finished"] is True
    eng = FakeEngine.instances[-1]
    assert eng.said == ["Three four five.", "Six."]
    assert eng.props["rate"] == int(speech.Speaker.BASE_RATE * 2.0) and eng.props["voice"] == "gmw/en"


def test_speaker_stops_at_once():
    sp = speech.Speaker(engine_factory=lambda: FakeEngine(delay=0.05))
    units = units_of(*["a b c d e f g h i j"] * 20)
    done, result = threading.Event(), {}
    sp.start(units, 0, on_done=lambda finished: (result.update(finished=finished), done.set()))
    time.sleep(0.2)
    sp.stop()
    assert done.wait(3) and result["finished"] is False and not sp.speaking
    assert len(FakeEngine.instances[-1].said) < 5
    sp.stop()  # stopping twice is fine


def test_no_speech_engine_and_choosing_voices():
    assert not speech.Speaker(engine_factory=lambda: FakeEngine(fail=True)).available()
    assert speech.Speaker(engine_factory=lambda: FakeEngine(fail=True)).voices() == []
    sp = speech.Speaker(engine_factory=FakeEngine)
    assert sp.voice_for("en") == "gmw/en"  # not the Chinese voice that "reads Latin as English"
    assert sp.voice_for("nl") == "TTS_MS_NL-NL_FRANK"  # Windows names say the language
    assert sp.voice_for("de") is None
    assert len(sp.voices()) == 4


def test_converted_document_can_be_read(paper):
    data = pipeline.load(paper).export("pdf", FormatSettings(include_contents=False))
    units = speech.reading_units(data)
    assert len(units) > 5 and all(s.words for s in units)
    text = " ".join(s.text for s in units)
    assert "  " not in text and len(text) > 500
