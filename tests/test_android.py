"""Pieces of the Android (phone and tablet) version that can be checked on a desktop."""
import threading
import time

from dyslexia_converter import speech


class _FakeJnius:
    """Just enough of pyjnius and Android's TextToSpeech to drive the Android speech engine."""

    class PythonJavaClass:
        pass

    @staticmethod
    def java_method(sig):
        return lambda f: f

    def __init__(self):
        self.spoken = []
        jn = self

        class Locale:
            def __init__(self, tag, name):
                self.tag, self.name = tag, name

            def toLanguageTag(self):
                return self.tag

            def getDisplayName(self):
                return self.name

        class Voice:
            def __init__(self, name, tag, lang, network=False):
                self.name, self.locale, self.network = name, Locale(tag, lang), network

            def getName(self):
                return self.name

            def getLocale(self):
                return self.locale

            def isNetworkConnectionRequired(self):
                return self.network

        class Voices:
            def toArray(self):
                return [Voice("nl-nl-x-lfc-local", "nl-NL", "Dutch (Netherlands)"),
                        Voice("en-gb-x-gba-local", "en-GB", "English (United Kingdom)"),
                        Voice("en-us-x-online", "en-US", "English (United States)", network=True)]

        class TTS:
            QUEUE_FLUSH = 0

            def __init__(self, context, listener):
                self.until, self.voice, self.rate = 0.0, None, 1.0
                threading.Timer(0.05, listener.onInit, args=(0,)).start()

            def getVoices(self):
                return Voices()

            def setVoice(self, v):
                self.voice = v.getName()

            def setSpeechRate(self, r):
                self.rate = r

            def speak(self, text, mode, params, uid):
                jn.spoken.append((text, self.voice, round(self.rate, 2)))
                self.until = time.monotonic() + 0.05

            def isSpeaking(self):
                return time.monotonic() < self.until

            def stop(self):
                self.until = 0.0

        class ActivityThread:
            @staticmethod
            def currentApplication():
                return object()

        self.classes = {"android.speech.tts.TextToSpeech": TTS, "android.app.ActivityThread": ActivityThread}

    def autoclass(self, name):
        return self.classes[name]


def test_android_voices_speak_offline_voices_at_the_chosen_speed(monkeypatch):
    jn = _FakeJnius()
    monkeypatch.setattr(speech.AndroidEngine, "_tts", None)
    eng = speech.AndroidEngine(jn)
    voices = eng.getProperty("voices")
    assert [(v.id, v.languages[0]) for v in voices] == [("nl-nl-x-lfc-local", "nl"), ("en-gb-x-gba-local", "en")]
    sentences = [speech.Sentence([speech.Word("Hallo", 0, [], 0), speech.Word("daar.", 0, [], 6)])]
    words, done = [], []
    sp = speech.Speaker(lambda: speech.AndroidEngine(jn))
    assert sp.voice_for("nl") == "nl-nl-x-lfc-local"
    sp.start(sentences * 2, 0, 1.5, "nl-nl-x-lfc-local", on_sentence=words.append, on_done=done.append)
    sp._thread.join(5)
    assert done == [True]
    assert jn.spoken == [("Hallo daar.", "nl-nl-x-lfc-local", 1.5)] * 2
    assert words == [0, 1]  # the highlight moves with each sentence (and is paced along it)


def test_android_is_recognised(monkeypatch):
    monkeypatch.setenv("FLET_PLATFORM", "android")
    assert speech.on_android()
    monkeypatch.setenv("FLET_PLATFORM", "windows")
    assert speech.on_android() == (speech.sys.platform == "android")
