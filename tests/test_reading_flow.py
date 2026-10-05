"""Reading aloud as a reader uses it: play, pause, play again, quick repeated presses, stop, changing options and
speed while reading, the ruler and the marks in focus mode, the main view and the reading view.

The voice is a fake engine that speaks on its own thread at a steady pace and reports each word, like the real
ones; it never makes a sound. Every step checks what the reader sees: the play/pause button, whether the ruler
moved to the sentence being read, and whether the marks follow (and stop when paused)."""
import asyncio
import time

import flet as ft
import pytest

from dyslexia_converter import speech
from test_app_check import _settle, headless  # noqa: F401  (the fixture)


class PacedEngine:
    """A speech engine that says one word every ``delay`` seconds on the reading thread and reports it."""
    made = []

    def __init__(self, delay=0.04):
        self.delay, self.cb, self.text, self.stopped = delay, None, "", False
        PacedEngine.made.append(self)

    def getProperty(self, key):
        class V:
            id, name, languages = "fake/en", "Fake English", ["en"]
        return [V()] if key == "voices" else None

    def setProperty(self, key, value):
        pass

    def connect(self, name, cb):
        self.cb = cb

    def say(self, text):
        self.text = text

    def runAndWait(self):
        pos = 0
        for w in self.text.split(" "):
            if self.stopped:
                return
            if self.cb:
                self.cb(None, pos, len(w))
            pos += len(w) + 1
            time.sleep(self.delay)

    def stop(self):
        self.stopped = True


def _speaker():
    PacedEngine.made = []
    return speech.Speaker(engine_factory=PacedEngine)


async def _until(cond, timeout=3.0):
    """Wait until ``cond()`` holds (the app works on its own event loop and threads)."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < timeout:
        if cond():
            return True
        await asyncio.sleep(0.02)
    return cond()


def _playing(app) -> bool:
    return app._reading and app.read_btn.icon == ft.Icons.PAUSE_ROUNDED and app.speaker.speaking


def _paused(app) -> bool:
    return not app._reading and app.read_btn.icon == ft.Icons.PLAY_ARROW_ROUNDED


async def _focus_with_ruler(app, path):
    app.speaker = _speaker()
    app._speech_allowed = lambda: True
    app.source_path = str(path)
    await app.load_document()
    f = app.focus
    await f.open()
    await _until(lambda: not f.loading.visible, 10)
    await f.on_ruler(None)
    assert f.ruler, "the ruler could not be switched on"
    return f


async def _scenario_focus(app, path):
    f = await _focus_with_ruler(app, path)
    assert not app.read_btn.disabled and not app.stop_btn.disabled is False  # stop: nothing to stop yet

    # 1. play starts at once, the ruler jumps to the sentence being read and the marks show
    await app.on_read(None)
    assert _playing(app), "play did not start reading"
    assert await _until(lambda: f._reading is not None and f._reading[1]), "nothing is marked"
    start_page, start_line = f.ruler
    words = app._read_units[app._read_pos].words
    assert start_page == words[0].page
    # 2. the ruler and the marks follow the voice
    first = f._reading[2]
    assert await _until(lambda: f._reading[2] != first), "the marked word does not move along"

    # 3. pause: the button shows play and nothing moves any more
    await app.on_read(None)
    assert _paused(app)
    await _settle(0.3)
    frozen = (f.ruler, f._reading)
    await _settle(0.4)
    assert (f.ruler, f._reading) == frozen, "the marks still move after pausing"

    # 4. play again continues (not from the start)
    pos = app._read_pos
    await app.on_read(None)
    assert _playing(app) and app._read_pos >= pos

    # 5. many quick presses: it ends in the state of the last press, with one voice speaking
    for _ in range(8):
        await app.on_read(None)
        await asyncio.sleep(0.01)
    assert app._reading  # playing, then 8 presses: playing again
    assert await _until(lambda: app.speaker.speaking)
    await _settle(0.5)
    assert _playing(app), "after quick presses the button and the voice disagree"
    alive = [e for e in PacedEngine.made if not e.stopped]
    assert len(alive) == 1, f"{len(alive)} voices are speaking at once"

    # 6. changing a reading option or the speed while reading keeps reading
    for chip in app._option_chips:
        if chip.data == "skip_citations":
            class Tap:
                control = chip
            await chip.on_select(Tap())
    assert await _until(lambda: _playing(app)), "reading stopped after changing an option"

    class Speed:
        control = type("C", (), {"value": 1.5})()
    await app.on_read_speed(Speed())
    assert await _until(lambda: _playing(app)), "reading stopped after changing the speed"
    assert await _until(lambda: f._reading is not None and f._reading[1])

    # 7. the toggles: no marks, and a ruler that stays where it is
    app.ui["reading_highlight"], app.ui["ruler_follows"] = False, False
    await _settle(0.3)
    still = f.ruler
    await _settle(0.4)
    assert f.ruler == still and f._reading is not None and not f._reading[1]
    app.ui["reading_highlight"], app.ui["ruler_follows"] = True, True

    # 8. stop: everything back to the start
    await app.on_read_stop(None)
    assert _paused(app) and app._read_pos is None and app.stop_btn.disabled
    await _settle(0.3)
    assert f._reading is None
    await f.close()


async def _scenario_main_view(app, path):
    app.speaker = _speaker()
    app._speech_allowed = lambda: True
    app.source_path = str(path)
    await app.load_document()
    await app.on_read(None)
    assert _playing(app)
    await _settle(0.3)
    await app.on_read(None)
    await app.on_read(None)  # pause and play straight away
    await _settle(0.4)
    assert _playing(app)
    await app.on_read_stop(None)
    assert _paused(app)


async def _scenario_reading_view(app, path):
    app.speaker = _speaker()
    app._speech_allowed = lambda: True
    app.source_path = str(path)
    await app.load_document()
    r = app.reflow
    await r.open()
    await r.on_read(None)
    assert r._reading and r.read_btn.icon == ft.Icons.PAUSE_ROUNDED
    assert await _until(lambda: r._lit is not None), "nothing is marked in the reading view"
    for _ in range(5):  # quick presses
        await r.on_read(None)
    assert not r._reading  # an odd number of presses after playing: paused
    await _settle(0.3)
    lit = r._lit
    await _settle(0.3)
    assert r._lit == lit
    await r.on_read(None)
    await _settle(0.4)
    assert r._reading and app.speaker.speaking
    alive = [e for e in PacedEngine.made if not e.stopped]
    assert len(alive) == 1
    await r.on_stop(None)
    assert not r._reading
    await r.close()


async def _scenario_greyed_out(app, path):
    # before a document is open, the reading controls are greyed out (they work once one is open)
    assert app.read_btn.disabled and app.tap_btn.disabled and app.audio_btn.disabled
    assert app.read_along_btn.disabled
    ruler_chip = next(c for c in app._option_chips if c.data == "ruler_follows")
    assert not ruler_chip.visible  # the ruler only exists in focus mode: left out of the main screen
    app.speaker = _speaker()
    app._speech_allowed = lambda: True
    app.source_path = str(path)
    await app.load_document()
    assert not app.read_btn.disabled and not app.audio_btn.disabled and app.stop_btn.disabled
    assert app.audio_btn.visible and any(i.on_click == app.on_audio_export for i in app.export_menu.items)
    await app.focus.open()
    assert ruler_chip.visible and not app.audio_btn.visible  # focus mode: the ruler option, but no MP3
    focus_menu = next(c for c in app.focus.top.content.controls if isinstance(c, ft.PopupMenuButton)
                      and any(getattr(i, "on_click", None) == app.on_export for i in (c.items or [])))
    assert not any(getattr(i, "on_click", None) == app.on_audio_export for i in focus_menu.items)
    await app.focus.close()
    assert not ruler_chip.visible and app.audio_btn.visible
    # no voices at all: the controls that could never work are left out; the red note says why
    app.speaker.voices = lambda: []
    app._update_read_buttons()
    assert not app.read_btn.visible and not app.tap_btn.visible and not app.audio_btn.visible
    assert not app.voice_dd.visible and not app.speed_slider.visible


async def _scenario_ruler_switches_on(app, path):
    app.speaker = _speaker()
    app._speech_allowed = lambda: True
    app.source_path = str(path)
    await app.load_document()
    f = app.focus
    await f.open()
    await _until(lambda: not f.loading.visible, 10)
    assert not f.ruler
    # reading starts with "Ruler follows" on: the ruler switches on at the first sentence read
    await app.on_read(None)
    assert _playing(app)
    first = app._read_units[app._read_pos].words[0]
    assert f.ruler and f.ruler[0] == first.page and f.ruler_toggle.selected
    await app.on_read_stop(None)
    # switching "Ruler follows" on (with the ruler off) switches the ruler on, at the spot being read
    await f.on_ruler(None)
    assert not f.ruler
    chip = next(c for c in app._option_chips if c.data == "ruler_follows")

    class Tap:
        control = chip
    await chip.on_select(Tap())  # off
    assert not f.ruler
    await app.on_read(None)
    assert _playing(app) and not f.ruler  # off: reading does not switch the ruler on
    assert await _until(lambda: app._read_pos is not None)
    await chip.on_select(Tap())  # on, while reading
    assert f.ruler and f.ruler[0] == app._read_units[app._read_pos].words[0].page
    assert _playing(app)  # and reading goes on
    await app.on_read_stop(None)
    await f.close()


@pytest.mark.parametrize("scenario", [_scenario_focus, _scenario_main_view, _scenario_reading_view,
                                      _scenario_greyed_out, _scenario_ruler_switches_on])
def test_reading_aloud_behaves_like_a_reader_expects(headless, paper, scenario):  # noqa: F811
    headless(lambda app: scenario(app, paper), timeout=120)
