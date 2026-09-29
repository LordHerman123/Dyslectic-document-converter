"""The automatic app check: the real app, driven through its screens without a window.

Unit tests check the parts; this walks through what a reader does (open a document, read it in focus mode and in
the reading view, change the page colour and text size, turn pages, leave again) with the app's own code, on a
headless Flet page: everything the app sends to the window is built (and thrown away) exactly as in the real app.
A crash like "'FocusMode' object has no attribute 'marks'" (1.14.0) is caught here before a release.
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
from flet.messaging.connection import Connection
from flet.messaging.session import Session
from flet.pubsub.pubsub_hub import PubSubHub

from dyslexia_converter.ui.app import ConverterApp


class NullConnection(Connection):
    """A connection to no window: every message is encoded exactly as for a real window (encoding is also where
    Flet remembers what the window has, to send only changes next time), then counted instead of sent."""

    def __init__(self, loop):
        super().__init__()
        self.loop = loop
        self.executor = ThreadPoolExecutor(4)
        self.pubsubhub = PubSubHub(loop, self.executor)
        self.sent = 0
        self.bytes = 0

    @staticmethod
    def encode(value) -> bytes:
        import msgpack
        from flet.controls.base_control import BaseControl
        from flet.messaging.protocol import configure_encode_object_for_msgpack

        return msgpack.packb(value, default=configure_encode_object_for_msgpack(BaseControl))

    def send_message(self, message):
        self.sent += 1
        self.bytes += len(self.encode([message.action, message.body]))


@pytest.fixture
def headless(monkeypatch):
    """Run ``scenario(app)`` with the app on a headless page (calls that wait for the window get no answer at
    once, as from a window that does nothing)."""
    async def no_answer(self, control_id, method_name, args, timeout=None):
        return None

    monkeypatch.setattr(Session, "invoke_method", no_answer)

    def run(scenario, timeout=120):
        async def main():
            conn = NullConnection(asyncio.get_running_loop())
            session = Session(conn)  # kept here: the page only holds a weak reference to its session
            conn.encode(session.get_page_patch())  # what a window gets when it connects: the page is on screen
            page = session.page
            app = ConverterApp(page)
            app.build()
            page.update()
            await asyncio.wait_for(scenario(app), timeout)
            assert conn.sent > 0
            return app
        return asyncio.run(main())
    return run


async def _settle(seconds=0.5):
    await asyncio.sleep(seconds)


async def _read_everywhere(app, path):
    """Open a document and go through focus mode and the reading view like a reader would."""
    app.source_path = str(path)
    await app.load_document()
    assert app.session is not None and app.converted_pdf, "the document did not convert"
    # focus mode: open (while the window keeps reporting its size, as a real one does), let pages draw, change
    # colour (light and dark), zoom, layout, turn a page, leave
    f = app.focus
    opening = asyncio.ensure_future(f.open())
    size = 900
    while not opening.done():
        size += 7

        class Resized:
            width, height = size, 700
        f.on_body_size(Resized())
        await asyncio.sleep(0)
    await opening
    assert f.active
    for _ in range(40):  # the first pages are drawn behind the loading screen
        await _settle(0.25)
        if not f.loading.visible:
            break
    assert not f.loading.visible
    for tint in ("cream", "dark", "white"):
        class E:  # a click on a page colour button
            control = type("C", (), {"data": tint})()
        f.on_tint(E())
        await _settle(0.2)
    f._zoom_by(1.2)
    await f.on_layout(None)
    await f.turn(1)
    await f.on_layout(None)
    await f.close()
    assert not f.active
    # the reading view: open, larger text, more spacing, width, colour, back to the pages and out
    r = app.reflow
    await r.open()
    assert r.active and r.items
    r._size_by(2)
    r._line_by(0.15)
    r.on_width(None)

    class T:
        control = type("C", (), {"data": "green"})()
    r.on_tint(T())
    await _settle(0.3)
    await r.on_pages()
    assert app.focus.active and not r.active
    await app.focus.close()


def test_app_check_pdf(headless, paper):
    headless(lambda app: _read_everywhere(app, paper))


def test_app_check_word_and_epub(headless, tmp_path):
    from test_structured import _docx, _epub

    docx, epub = tmp_path / "plants.docx", tmp_path / "book.epub"
    _docx(docx)
    _epub(epub)

    async def scenario(app):
        await _read_everywhere(app, docx)
        await _read_everywhere(app, epub)
        # reopening a document goes back to where it was left
        await app.reflow.open()
        app.reflow.current = 3
        await app.reflow.close()
        await app.reflow.open()
        assert app.reflow.current == 3
        await app.reflow.close()
    headless(scenario)
