import hashlib
import shutil
from pathlib import Path

import pytest

from make_samples import make_paper, make_scanned


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Keep settings, dictionaries, keys and caches out of the real user profile."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("DYSLEXIA_CONVERTER_HOME", str(home))
    for var in ("ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    return home


@pytest.fixture(scope="session")
def samples(tmp_path_factory):
    d = tmp_path_factory.mktemp("samples")
    make_paper(d / "sample_paper.pdf")
    make_scanned(d / "sample_paper.pdf", d / "sample_scanned.pdf", dpi=150)
    return d


@pytest.fixture(scope="session")
def paper(samples):
    return samples / "sample_paper.pdf"


@pytest.fixture(scope="session")
def scanned(samples):
    return samples / "sample_scanned.pdf"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


needs_tesseract = pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract not installed")
