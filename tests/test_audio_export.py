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
