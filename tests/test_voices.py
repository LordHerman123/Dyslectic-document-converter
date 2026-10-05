"""Natural (Piper) voices: the catalogue, downloading safely, choosing them, and when each word is said."""
import hashlib
import io
import os
from pathlib import Path

import pytest

from dyslexia_converter import speech, voices


def test_word_times_follow_the_sounds_of_the_words():
    text = "The cat, sat."
    # three spoken words: "the" (2 sounds), "cat," (3 + a pause), "sat." (3 + a full stop)
    parts = [(2.0, ["ð", "ə", " ", "k", "ˈ", "a", "t", ",", " ", "s", "a", "t", "."])]
    times = speech.word_times(text, parts)
    assert [(text[p:p + n]) for _, p, n in times] == ["The", "cat,", "sat."]
    starts = [round(t, 3) for t, _, _ in times]
    assert starts[0] == 0.0 and starts[0] < starts[1] < starts[2] < 2.0
    assert starts[2] - starts[1] > starts[1] - starts[0]  # "cat," takes longer than "the" (the comma pause)


def test_word_times_fall_back_to_letters_when_the_voice_splits_words_differently():
    text = "In 2013 it rained."
    parts = [(3.0, list("ɪn twɛnti θɜːtiːn ɪt ɹeɪnd."))]  # "2013" is said as two words
    times = speech.word_times(text, parts)
    assert [text[p:p + n] for _, p, n in times] == ["In", "2013", "it", "rained."]
    assert times[0][0] == 0.0 and all(a[0] < b[0] for a, b in zip(times, times[1:])) and times[-1][0] < 3.0


def _install(home: Path, key: str) -> None:
    d = home / "voices"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{key}.onnx").write_bytes(b"model")
    (d / f"{key}.onnx.json").write_text('{"audio": {"sample_rate": 16000}}', "utf-8")


def test_installed_voices_are_found_and_chosen_first(isolated_home, monkeypatch):
    assert voices.installed() == []
    _install(isolated_home, "nl_NL-pim-medium")
    (isolated_home / "voices" / "en_US-ryan-medium.onnx").write_bytes(b"half")  # no settings: not complete
    assert [v.key for v in voices.installed()] == ["nl_NL-pim-medium"]
    assert voices.voice_of("piper:nl_NL-pim-medium").name == "Pim"
    assert voices.voice_of("piper:en_US-ryan-medium") is None and voices.voice_of("gmw/nl") is None
    assert voices.sample_rate("nl_NL-pim-medium") == 16000

    class SystemVoices:  # the computer's own voices
        def getProperty(self, key):
            return [speech._VoiceInfo("gmw/nl", "Dutch", ["nl"]), speech._VoiceInfo("gmw/en", "English", ["en"])]

        def stop(self):
            pass

    monkeypatch.setattr(voices, "supported", lambda: True)
    sp = speech.Speaker()
    monkeypatch.setattr(speech.Speaker, "_make", lambda self, voice=None: (
        speech.PiperEngine(voices.voice_of(voice).key, play=False) if voices.voice_of(voice) else SystemVoices()))
    assert sp.voices()[0] == ("piper:nl_NL-pim-medium", "Pim (Netherlands) - natural")
    assert sp.voice_for("nl") == "piper:nl_NL-pim-medium"  # a natural voice wins for its language
    assert sp.voice_for("en") == "gmw/en"
    voices.remove("nl_NL-pim-medium")
    sp.refresh()
    assert sp.voice_for("nl") == "gmw/nl" and voices.installed() == []


def test_a_voice_is_downloaded_checked_and_a_damaged_one_is_refused(isolated_home, monkeypatch):
    model, config = b"m" * 1000, b'{"audio": {"sample_rate": 22050}}'
    real = voices.BY_KEY["it_IT-paola-medium"]
    fake = voices.NaturalVoice(real.key, real.language, real.name, real.region, real.woman, real.path,
                               len(model), hashlib.md5(model).hexdigest(), len(config),
                               hashlib.md5(config).hexdigest())
    monkeypatch.setitem(voices.BY_KEY, real.key, fake)
    monkeypatch.setattr(voices, "CATALOG", [fake])
    urls = []

    def urlopen(req, timeout=0):
        urls.append(req.full_url)
        return io.BytesIO(config if req.full_url.endswith(".json") else model)

    monkeypatch.setattr(voices.urllib.request, "urlopen", urlopen)
    seen = []
    voices.download(real.key, seen.append)
    assert urls[0].startswith(voices.BASE_URL) and urls[1].endswith("it_IT-paola-medium.onnx")
    assert seen[-1] == 1.0 and [v.key for v in voices.installed()] == [real.key]

    voices.remove(real.key)
    model = b"x" * 1000  # same size, wrong content
    with pytest.raises(voices.VoiceDownloadError):
        voices.download(real.key)
    assert voices.installed() == [] and not any(p.suffix == ".part" for p in (isolated_home / "voices").iterdir())

    with pytest.raises(voices.VoiceDownloadError, match="cancelled"):
        voices.download(real.key, cancelled=lambda: True)


def test_every_language_of_the_app_has_a_natural_voice():
    assert {v.language for v in voices.CATALOG} >= {"en", "nl", "de", "fr", "es", "it", "pt"}
    assert all(v.megabytes > 50 and len(v.md5) == 32 and v.path.endswith(v.key + ".onnx") for v in voices.CATALOG)


MODEL = os.environ.get("PIPER_TEST_MODEL", "")


@pytest.mark.skipif(not (MODEL and Path(MODEL).is_file() and voices.supported()),
                    reason="set PIPER_TEST_MODEL to a downloaded Piper voice (.onnx) to test real speech")
def test_a_natural_voice_speaks_and_reports_every_word(isolated_home):
    import shutil

    key = Path(MODEL).stem
    (isolated_home / "voices").mkdir()
    for suffix in ("", ".json"):
        shutil.copy(MODEL + suffix, isolated_home / "voices" / (key + ".onnx" + suffix))
    sentences = [speech.Sentence([speech.Word(w, i, []) for i, w in enumerate(t.split())])
                 for t in ("Papers were accepted.", "Most of them, sadly, were fake.")]
    for s in sentences:
        pos = 0
        for w in s.words:
            w.start = s.text.index(w.text, pos)
            pos = w.start + len(w.text)
    said = []
    sp = speech.Speaker(lambda: speech.PiperEngine(key, play=False))
    done = []
    sp.start(sentences, 0, 1.0, "piper:" + key, on_word=lambda s, w: said.append((s, w)), on_done=done.append)
    sp._thread.join(30)
    assert done == [True]
    assert said == [(0, 0), (0, 1), (0, 2), (1, 0), (1, 1), (1, 2), (1, 3), (1, 4), (1, 5)]
