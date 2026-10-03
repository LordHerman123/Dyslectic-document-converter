"""Saving text as audio (MP3)."""
import io
import wave

import numpy as np
import pytest

from dyslexia_converter import audio_export as ae
from dyslexia_converter import speech

pytestmark = pytest.mark.skipif(not ae.supported(), reason="the MP3 encoder (lameenc) is not installed")


def _wav(seconds: float, rate: int = 22050, channels: int = 1) -> bytes:
    t = np.arange(int(seconds * rate)) / rate
    x = (np.sin(2 * np.pi * 220 * t) * 8000).astype("<i2")
    if channels == 2:
        x = np.repeat(x, 2)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(x.tobytes())
    return buf.getvalue()


def test_sentences_are_grouped_into_parts():
    sentences = ae.split_sentences("One two. Three four!  Five six? Seven.")
    assert sentences == ["One two.", "Three four!", "Five six?", "Seven."]
    assert ae.parts(sentences, 20) == ["One two. Three four!", "Five six? Seven."]
    assert ae.parts(["x" * 50, "short."], 20) == ["x" * 50, "short."]
    assert round(ae.minutes(["word " * 165], 1.0), 2) == 1.0 and round(ae.minutes(["word " * 165], 2.0), 2) == 0.5


def test_parts_are_spoken_into_one_mp3_with_progress():
    seen = []
    mp3 = ae.export_mp3(["First part.", "Second, longer part."],
                        lambda ts: (_wav(1.0, 22050) if i == 0 else _wav(0.5, 44100, 2) for i, _ in enumerate(ts)),
                        seen.append)
    assert mp3[:3] == b"ID3" or (mp3[0] == 0xFF and mp3[1] & 0xE0 == 0xE0)  # an MP3 frame
    # about 1 + 0.5 seconds of sound and two short pauses, at 64 kbit/s
    assert 12_000 < len(mp3) < 20_000
    assert seen[-1] == 1.0 and seen == sorted(seen)


def test_cancelling_and_nothing_to_read():
    with pytest.raises(ae.AudioExportError, match="cancelled"):
        ae.export_mp3(["a."], lambda ts: (_wav(0.2) for _ in ts), cancelled=lambda: True)
    with pytest.raises(ae.AudioExportError):
        ae.export_mp3([], lambda ts: iter(()))


def test_the_speaker_renders_with_the_reading_voice_and_speed():
    made = []

    class Engine:
        def __init__(self):
            self.props = {}

        def setProperty(self, k, v):
            self.props[k] = v

        def to_wav(self, text):
            made.append((text, dict(self.props)))
            return _wav(0.1)

    sp = speech.Speaker(Engine)
    out = list(sp.render_many(["One.", "", "Two."], 1.5, "voice-x"))
    assert len(out) == 2 and [t for t, _ in made] == ["One.", "Two."]
    assert made[0][1] == {"rate": int(speech.Speaker.BASE_RATE * 1.5), "voice": "voice-x"}


def _sentence(text, page=0):
    return speech.Sentence([speech.Word(w, page, [(0, 0, 1, 1)]) for w in text.split()])


def test_citations_are_left_out_and_the_highlight_keeps_its_words():
    s = [_sentence("Big data matters (Kitchin, 2014). Really, as in [3], yes."), _sentence("(Smith, 2019)"),
         _sentence("Another sentence [Note 2] here.")]
    out, maps = speech.prepare_reading(s, skip_citations=True)
    assert out[0].text == "Big data matters. Really, as in, yes."
    assert maps[0] == [0, 1, 2, 5, 6, 7, 9]  # "Really," is word 5 of the original sentence
    assert out[1].words == [] and out[2].text == "Another sentence here."
    assert [w.start for w in out[0].words] == [0, 4, 9, 18, 26, 29, 33]  # positions for the engine's word events
    same, maps = speech.prepare_reading(s)
    assert [x.text for x in same] == [x.text for x in s] and maps[0] == list(range(10))
    assert len(speech.prepare_reading(s, end=1)[0]) == 1  # the reference list from sentence 1 on is left out
    assert ae.strip_citations("Shown before (see Smith, 2019; Lee 2020), and [12-14].") == "Shown before, and."


def test_the_end_part_is_found_from_the_headings():
    units = [_sentence(t, p) for t, p in [("Introduction", 0), ("Text here.", 0), ("References", 1),
                                           ("Smith J (2019) A paper.", 1), ("Notes", 2), ("1 A note.", 2)]]
    toc = [(1, "Introduction", 1), (1, "References", 2), (1, "Notes", 3)]
    assert ae.end_part_start(units, toc) == 2
    assert ae.end_part_start(units, [(1, "Introduction", 1)]) is None
