"""The check for a new version: at most once a day, only when switched on, a dismissed version stays quiet."""
from dyslexia_converter import __version__, updates


def test_version_numbers_compare_as_numbers():
    assert updates.parse_version("v1.14.1") == (1, 14, 1)
    assert updates.is_newer("1.14.10", "1.14.9")
    assert updates.is_newer("v2.0", "1.99.99")
    assert not updates.is_newer("1.14.1", "1.14.1")
    assert not updates.is_newer("1.14", "1.14.0")
    assert not updates.is_newer("latest", "1.0")  # no version number: never announced


def test_github_is_asked_at_most_once_a_day():
    calls = []

    def fetch():
        calls.append(1)
        return "999.0.0", "https://example.org/release"

    ui = {}
    start = 1_700_000_000.0  # a real time: never asked before, so the first check asks
    assert updates.check(ui, now=start, fetch=fetch) == ("999.0.0", "https://example.org/release")
    assert updates.check(ui, now=start + 3600, fetch=fetch) == ("999.0.0", "https://example.org/release")
    assert len(calls) == 1  # the answer of an hour ago is used
    updates.check(ui, now=start + updates.CHECK_EVERY, fetch=fetch)
    assert len(calls) == 2


def test_nothing_is_shown_when_up_to_date_switched_off_or_dismissed():
    now = 1_700_000_000.0
    newer = lambda: ("999.0.0", "u")  # noqa: E731
    assert updates.check({}, now=now, fetch=lambda: (__version__, "u")) is None
    assert updates.check({}, now=now, fetch=lambda: None) is None  # offline
    calls = []
    assert updates.check({"check_updates": False}, now=now, fetch=lambda: calls.append(1)) is None
    assert not calls  # switched off: GitHub is not even asked
    assert updates.check({"update_dismissed": "999.0.0"}, now=now, fetch=newer) is None
    assert updates.check({}, now=now, fetch=newer) == ("999.0.0", "u")


def test_the_request_goes_to_the_project_releases_only():
    assert updates.LATEST_URL == ("https://api.github.com/repos/LordHerman123/Dyslectic-document-converter/"
                                  "releases/latest")
