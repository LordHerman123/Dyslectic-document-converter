"""Natural voices for reading aloud: Piper neural voices, downloaded on request and used offline.

The voices sound much more natural than most voices built into the computer. Each one is a file of about
60 MB from the Piper voice collection (https://huggingface.co/rhasspy/piper-voices); it is downloaded only
when the reader asks for it, checked against its published size and checksum, and kept in the app's data
folder. After that everything runs on this device: no text is ever sent anywhere.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote

from .settings import app_data_dir

BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main/"
PREFIX = "piper:"  # voice ids of natural voices, next to the computer's own voice ids


@dataclass(frozen=True)
class NaturalVoice:
    """One downloadable voice: its key, language, name, region, man or woman, and the files with their sizes
    and MD5 checksums (as published in the collection's voices.json)."""
    key: str
    language: str  # en, nl, de, ...
    name: str
    region: str
    woman: bool
    path: str  # of the .onnx file in the collection
    size: int
    md5: str
    config_size: int
    config_md5: str

    @property
    def id(self) -> str:
        """The voice id used for reading aloud."""
        return PREFIX + self.key

    @property
    def megabytes(self) -> int:
        """Download size, rounded."""
        return round((self.size + self.config_size) / 1e6)


CATALOG = [NaturalVoice(*v) for v in [
    ("en_GB-alba-medium", "en", "Alba", "Great Britain", True, "en/en_GB/alba/medium/en_GB-alba-medium.onnx",
     63201294, "c07f313752bb3aba8061041666251654", 4888, "dbb6f2ede31082710665221417906e13"),
    ("en_US-lessac-medium", "en", "Lessac", "United States", True,
     "en/en_US/lessac/medium/en_US-lessac-medium.onnx", 63201294, "2fc642b535197b6305c7c8f92dc8b24f", 4885,
     "c1f2b7bddefe113f3255ff9ef234cfd3"),
    ("en_US-ryan-medium", "en", "Ryan", "United States", False, "en/en_US/ryan/medium/en_US-ryan-medium.onnx",
     63201294, "8f06d3aff8ded5a7f13f907e6bec32ac", 4883, "f173a2b5202b3e4128ccc3ed8195306c"),
    ("nl_BE-nathalie-medium", "nl", "Nathalie", "Belgium", True,
     "nl/nl_BE/nathalie/medium/nl_BE-nathalie-medium.onnx", 63201294, "ab0c38b5f66764b59ad9e3e98b1c2172", 4879,
     "13c6e6c9511447e1906c25748a93f0bd"),
    ("nl_NL-pim-medium", "nl", "Pim", "Netherlands", False, "nl/nl_NL/pim/medium/nl_NL-pim-medium.onnx",
     63516050, "190b3e6463a931d3c583d2fa7cd0e4a0", 5037, "c4d22097fefa2afe275b9bb6ff4db865"),
    ("de_DE-thorsten-medium", "de", "Thorsten", "Germany", False,
     "de/de_DE/thorsten/medium/de_DE-thorsten-medium.onnx", 63201294, "a129b00fb3078df43c96bab6c94535c0", 4819,
     "843a7bd7272724f750534dd5a26d1aad"),
    ("fr_FR-siwis-medium", "fr", "Siwis", "France", True, "fr/fr_FR/siwis/medium/fr_FR-siwis-medium.onnx",
     63201294, "20e876e8c839e9b11a26085858f2300c", 4875, "a407e7e6901feb79c2ea2a5466076cce"),
    ("fr_FR-tom-medium", "fr", "Tom", "France", False, "fr/fr_FR/tom/medium/fr_FR-tom-medium.onnx",
     63511038, "5b460c2394a871e675f5c798af149412", 4959, "964d58602df7adf76c2401b070f68ea2"),
    ("es_ES-davefx-medium", "es", "Davefx", "Spain", False, "es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
     63201294, "dc515cd4ecc5f6f72fe14a941188fc9c", 4817, "dd157b5eaf6930bf949cf416d9a9307a"),
    ("it_IT-paola-medium", "it", "Paola", "Italy", True, "it/it_IT/paola/medium/it_IT-paola-medium.onnx",
     63511038, "3a44e73b12ca5d0c21a72e388b5847c8", 7099, "cd471a3757c88a7a4baee6207248b5d5"),
    ("pt_PT-tugão-medium", "pt", "Tugão", "Portugal", False, "pt/pt_PT/tugão/medium/pt_PT-tugão-medium.onnx",
     63201294, "0642048511ffe36c3b519520614b53f4", 5026, "c4113a1da477aa6db28420454c142ebd"),
    ("pt_BR-faber-medium", "pt", "Faber", "Brazil", False, "pt/pt_BR/faber/medium/pt_BR-faber-medium.onnx",
     63201294, "e0724a2f07965f6523d2a1e96b488a4c", 4855, "a1258e1e113c47d9a1486a9bef1daab4"),
]]
BY_KEY = {v.key: v for v in CATALOG}


class VoiceDownloadError(Exception):
    """A voice could not be downloaded (no internet, or the file was not what it should be)."""


def supported() -> bool:
    """Whether natural voices can be used here (the Piper engine is installed)."""
    try:
        import piper  # noqa: F401
    except Exception:
        return False
    return True


def voices_dir() -> Path:
    """Where downloaded voices are kept."""
    return app_data_dir() / "voices"


def model_path(key: str) -> Path:
    """The voice's model file (it has its settings next to it, with .json added)."""
    return voices_dir() / f"{key}.onnx"


def installed() -> list[NaturalVoice]:
    """The natural voices on this device (complete downloads only)."""
    return [v for v in CATALOG if model_path(v.key).is_file() and Path(str(model_path(v.key)) + ".json").is_file()]


def voice_of(voice_id: Optional[str]) -> Optional[NaturalVoice]:
    """The natural voice with this voice id, if it is one (and installed)."""
    if not voice_id or not voice_id.startswith(PREFIX):
        return None
    v = BY_KEY.get(voice_id[len(PREFIX):])
    return v if v is not None and v in installed() else None


def _fetch(url: str, dest: Path, size: int, md5: str, progress: Callable[[int], None],
           cancelled: Callable[[], bool]) -> None:
    """Download ``url`` to ``dest`` (through a temporary file), checking its size and checksum."""
    tmp = dest.with_name(dest.name + ".part")
    digest = hashlib.md5()
    got = 0
    req = urllib.request.Request(url, headers={"User-Agent": "DyslexiaConverter (natural voice download)"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
            while True:
                if cancelled():
                    raise VoiceDownloadError("cancelled")
                chunk = r.read(1 << 16)
                if not chunk:
                    break
                f.write(chunk)
                digest.update(chunk)
                got += len(chunk)
                progress(len(chunk))
        if got != size or digest.hexdigest() != md5:
            raise VoiceDownloadError("the downloaded file is damaged; try again")
        os.replace(tmp, dest)
    except OSError as e:
        raise VoiceDownloadError(f"no connection ({type(e).__name__})") from None
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def download(key: str, progress: Callable[[float], None] = lambda f: None,
             cancelled: Callable[[], bool] = lambda: False) -> NaturalVoice:
    """Download a voice from the catalogue (``progress`` gets 0..1). Raises :class:`VoiceDownloadError`."""
    v = BY_KEY[key]
    voices_dir().mkdir(parents=True, exist_ok=True)
    total = v.size + v.config_size
    done = [0]

    def step(n: int) -> None:
        done[0] += n
        progress(min(1.0, done[0] / total))

    url = BASE_URL + quote(v.path)
    # the settings first: a model without them does not count as installed
    _fetch(url + ".json", Path(str(model_path(key)) + ".json"), v.config_size, v.config_md5, step, cancelled)
    _fetch(url, model_path(key), v.size, v.md5, step, cancelled)
    return v


def remove(key: str) -> None:
    """Delete a downloaded voice."""
    for p in (model_path(key), Path(str(model_path(key)) + ".json")):
        try:
            p.unlink()
        except FileNotFoundError:
            pass


def sample_rate(key: str) -> int:
    """The voice's sample rate (from its settings)."""
    try:
        return int(json.loads(Path(str(model_path(key)) + ".json").read_text("utf-8"))["audio"]["sample_rate"])
    except Exception:
        return 22050
