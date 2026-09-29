"""What the app starts with."""
from dyslexia_converter.settings import SettingsStore
from dyslexia_converter.ui.app import ConverterApp


def test_every_start_is_in_selection_mode(isolated_home):
    """Tap to read is off at every start, also when it was left on last time: clicking the text selects it."""
    store = SettingsStore()
    store.save_ui({"tap_to_read": True, "app_language": "en"})
    app = ConverterApp(page=None)
    assert app.ui["tap_to_read"] is False


def test_app_font_is_remembered_and_standard_by_default(isolated_home):
    """The app starts in the Standard font; a font chosen in Settings is used again next time."""
    from dyslexia_converter.ui.app import APP_FONTS

    assert next(iter(APP_FONTS)) == "atkinson"
    assert ConverterApp(page=None).ui.get("app_font", "atkinson") == "atkinson"
    SettingsStore().save_ui({"app_font": "opendyslexic", "app_language": "en"})
    assert ConverterApp(page=None).ui["app_font"] == "opendyslexic"


def test_every_app_font_is_bundled():
    from dyslexia_converter.ui.app import APP_FONTS, ASSETS_DIR
    from pathlib import Path

    for family, file, _, _ in APP_FONTS.values():
        assert (Path(ASSETS_DIR) / "fonts" / file).is_file(), file


def test_a_file_given_at_start_is_opened(tmp_path):
    """Dropping a file on the app's icon (or "Open with") starts the app with the file's path: it is opened."""
    from dyslexia_converter.ui.app import file_from_args

    pdf, txt = tmp_path / "My paper.pdf", tmp_path / "notes.txt"
    pdf.write_bytes(b"%PDF-1.4")
    txt.write_text("x")
    assert file_from_args([str(pdf)]) == str(pdf)
    assert file_from_args([f'"{pdf}"']) == str(pdf)  # quoted, as Windows may pass it
    assert file_from_args(["--flag", str(txt), str(pdf)]) == str(pdf)
    assert file_from_args([str(tmp_path / "missing.epub")]) is None
    assert file_from_args([]) is None


def test_focus_mode_resizes_before_its_pages_are_built(isolated_home):
    """The window can report its size while focus mode is still reading the document: nothing is placed yet,
    and that is not an error (it was: 'FocusMode' object has no attribute 'marks')."""
    import asyncio

    app = ConverterApp(page=None)
    focus = app.focus
    focus.sizes = [(595.0, 842.0)]
    focus._resize(update=False)
    asyncio.run(focus.redraw(0))
