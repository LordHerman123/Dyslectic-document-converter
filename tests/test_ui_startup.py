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
