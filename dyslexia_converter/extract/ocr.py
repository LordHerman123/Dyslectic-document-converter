"""OCR engine abstraction.

The desktop build uses Tesseract (via ``pytesseract``). Other platforms can
provide a different engine (for example Google ML Kit on Android) by
implementing :class:`OcrEngine` and passing it to the pipeline.
"""
from __future__ import annotations

import io
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol


@dataclass
class OcrWord:
    text: str
    bbox: tuple[float, float, float, float]  # pixels in the supplied image
    confidence: float  # 0..100
    block: int
    paragraph: int
    line: int


@dataclass
class OcrRegion:
    """A non-text region (picture) reported by the OCR engine."""

    bbox: tuple[float, float, float, float]


@dataclass
class OcrResult:
    words: list[OcrWord]
    regions: list[OcrRegion]


class OcrEngine(Protocol):
    name: str

    def available(self) -> bool: ...

    def languages(self) -> list[str]: ...

    def recognize(self, png: bytes, languages: list[str]) -> OcrResult: ...


LANG_CODES = {"en": "eng", "nl": "nld", "de": "deu", "fr": "fra", "es": "spa", "it": "ita", "pt": "por"}


def _app_dirs() -> list[Path]:
    """Folders of the running app (the packaged .exe folder, or the source checkout)."""
    dirs = []
    if getattr(sys, "frozen", False):
        dirs.append(Path(sys.executable).resolve().parent)
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            dirs.append(Path(meipass))
    dirs.append(Path(__file__).resolve().parents[2])
    return dirs


def find_tesseract() -> Optional[str]:
    """Locate the Tesseract program.

    Order: a copy bundled with the app (``tesseract/`` next to the .exe),
    ``DYSLEXIA_CONVERTER_TESSERACT``, the system PATH, then the usual install
    folders (the Windows installer does not always add itself to PATH).
    """
    exe = "tesseract.exe" if os.name == "nt" else "tesseract"
    for d in _app_dirs():
        for sub in ("tesseract", "Tesseract-OCR", "_internal/tesseract"):
            cand = d / sub / exe
            if cand.is_file():
                tessdata = cand.parent / "tessdata"
                if tessdata.is_dir():
                    os.environ["TESSDATA_PREFIX"] = str(tessdata)  # use the bundled language data
                return str(cand)
    env = os.environ.get("DYSLEXIA_CONVERTER_TESSERACT")
    if env and Path(env).is_file():
        return env
    found = shutil.which("tesseract")
    if found:
        return found
    candidates = []
    if os.name == "nt":
        for var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            base = os.environ.get(var)
            if base:
                candidates += [Path(base) / "Tesseract-OCR" / exe, Path(base) / "Programs" / "Tesseract-OCR" / exe]
    else:
        candidates += [Path("/opt/homebrew/bin/tesseract"), Path("/usr/local/bin/tesseract"), Path("/usr/bin/tesseract")]
    for cand in candidates:
        if cand.is_file():
            return str(cand)
    return None


class TesseractEngine:
    name = "Tesseract"

    def __init__(self, cmd: Optional[str] = None):
        self._cmd = cmd or find_tesseract()
        # Pages are OCR'd in parallel; one thread per Tesseract process avoids
        # the heavy slowdown of several multi-threaded Tesseracts competing.
        os.environ.setdefault("OMP_THREAD_LIMIT", "1")

    def available(self) -> bool:
        try:
            import pytesseract
        except ImportError:
            return False
        if self._cmd and Path(self._cmd).is_file():
            pytesseract.pytesseract.tesseract_cmd = self._cmd
            return True
        return False

    def languages(self) -> list[str]:
        import pytesseract
        try:
            installed = set(pytesseract.get_languages(config=""))
        except Exception:
            return []
        return [k for k, v in LANG_CODES.items() if v in installed]

    def orientation(self, png: bytes) -> int:
        """Clockwise rotation (0/90/180/270) needed to make the text upright; 0 if unknown."""
        import pytesseract
        from PIL import Image

        try:
            img = Image.open(io.BytesIO(png))
            img.thumbnail((1600, 1600))
            osd = pytesseract.image_to_osd(img, config="--psm 0")
        except Exception:
            return 0
        for line in osd.splitlines():
            if line.startswith("Rotate:"):
                try:
                    return int(line.split(":")[1].strip()) % 360
                except ValueError:
                    return 0
        return 0

    def recognize(self, png: bytes, languages: list[str]) -> OcrResult:
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(png))
        codes = "+".join(LANG_CODES.get(l, l) for l in languages) or "eng"
        data = pytesseract.image_to_data(img, lang=codes, config="--psm 3",
                                          output_type=pytesseract.Output.DICT)
        words: list[OcrWord] = []
        blocks: dict[int, list] = {}
        for i in range(len(data["text"])):
            level = data["level"][i]
            box = (data["left"][i], data["top"][i],
                   data["left"][i] + data["width"][i], data["top"][i] + data["height"][i])
            bn = data["block_num"][i]
            if level == 2:
                blocks.setdefault(bn, [box, 0])
            text = (data["text"][i] or "").strip()
            if level == 5 and text:
                try:
                    conf = float(data["conf"][i])
                except (TypeError, ValueError):
                    conf = -1.0
                words.append(OcrWord(text, box, conf, bn, data["par_num"][i], data["line_num"][i]))
                if bn in blocks:
                    blocks[bn][1] += 1
        regions = [OcrRegion(b[0]) for b in blocks.values() if b[1] == 0]
        return OcrResult(words, regions)


def default_engine() -> Optional[OcrEngine]:
    if os.environ.get("DYSLEXIA_CONVERTER_NO_OCR"):
        return None  # testing / very slow machines: rely on text layers only
    eng = TesseractEngine()
    return eng if eng.available() else None
