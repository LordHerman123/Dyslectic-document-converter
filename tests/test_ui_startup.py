"""What the app starts with."""
from dyslexia_converter.settings import SettingsStore
from dyslexia_converter.ui.app import ConverterApp


def test_every_start_is_in_selection_mode(isolated_home):
    """Tap to read is off at every start, also when it was left on last time: clicking the text selects it."""
    store = SettingsStore()
    store.save_ui({"tap_to_read": True, "app_language": "en"})
    app = ConverterApp(page=None)
    assert app.ui["tap_to_read"] is False
