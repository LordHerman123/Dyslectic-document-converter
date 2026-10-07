"""When the system's file window cannot be shown (Linux without D-Bus, for example), the app says so and goes on
instead of stopping with an error."""
from test_app_check import headless  # noqa: F401  (the fixture)


async def _scenario(app):
    said = []
    app.notify = lambda msg, error=False, **kw: said.append((msg, error))

    async def broken(**kw):
        raise RuntimeError("SocketException: Connection failed, address = /run/user/0/bus")

    app.file_picker.pick_files = broken
    app.file_picker.save_file = broken
    await app.on_open(None)  # nothing raised
    assert app.source_path is None or app.source_path == ""
    await app.save_bytes(b"%PDF-1.4", "x.pdf", "pdf")  # nothing raised either
    assert len(said) == 2 and all(err for _, err in said) and "drop a file" in said[0][0]


def test_a_file_window_that_cannot_open_does_not_stop_the_app(headless):  # noqa: F811
    headless(_scenario, timeout=60)
