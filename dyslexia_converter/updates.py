"""Is there a newer version? Asks GitHub which release is the newest, at most once a day.

Only the address of the project's releases is requested: nothing about the reader, the computer or any document
is sent. It can be switched off in Settings; without an internet connection it quietly does nothing.
"""
from __future__ import annotations

import re
import time
from typing import Optional

from . import PROJECT_URL, __version__

LATEST_URL = PROJECT_URL.replace("https://github.com/", "https://api.github.com/repos/") + "/releases/latest"
CHECK_EVERY = 24 * 3600  # seconds between checks


def parse_version(text: str) -> tuple[int, ...]:
    """(1, 14, 1) from "v1.14.1" or "1.14.1"; () when there is no version number in it."""
    m = re.search(r"(\d+(?:\.\d+)*)", text or "")
    return tuple(int(p) for p in m.group(1).split(".")) if m else ()


def is_newer(latest: str, current: str = __version__) -> bool:
    """Whether release ``latest`` is newer than the version running (1.14.10 is newer than 1.14.9)."""
    a, b = parse_version(latest), parse_version(current)
    if not a or not b:
        return False
    width = max(len(a), len(b))
    return a + (0,) * (width - len(a)) > b + (0,) * (width - len(b))


def latest_release(timeout: float = 6.0) -> Optional[tuple[str, str]]:
    """(version, web page) of the newest release on GitHub, or None when it cannot be found out."""
    import httpx

    try:
        r = httpx.get(LATEST_URL, timeout=timeout, headers={"Accept": "application/vnd.github+json"},
                      follow_redirects=True)
        if r.status_code != 200:
            return None
        data = r.json()
        tag = str(data.get("tag_name") or "")
        number = ".".join(str(p) for p in parse_version(tag))  # "v1.14.1" or "Version-1.5" -> the number
        if not number or data.get("draft") or data.get("prerelease"):
            return None
        return number, str(data.get("html_url") or PROJECT_URL + "/releases/latest")
    except Exception:  # offline, blocked, rate-limited: try again another day
        return None


def check(ui: dict, now: Optional[float] = None, fetch=latest_release) -> Optional[tuple[str, str]]:
    """The newer release to tell the reader about, or None. Remembers in ``ui`` when it last asked (and the answer),
    so GitHub is asked at most once a day, and a version the reader dismissed is not shown again."""
    if not ui.get("check_updates", True):
        return None
    now = time.time() if now is None else now
    found = ui.get("update_latest")
    if now - float(ui.get("update_checked", 0)) >= CHECK_EVERY:
        found = fetch()
        ui["update_checked"] = now
        ui["update_latest"] = list(found) if found else None
    if not found:
        return None
    version, url = found[0], found[1]
    if not is_newer(version) or ui.get("update_dismissed") == version:
        return None
    return version, url
