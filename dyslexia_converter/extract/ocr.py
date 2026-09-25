"""OCR engine abstraction.

The desktop build uses Tesseract (via ``pytesseract``). Other platforms can
provide a different engine (for example Google ML Kit on Android) by
implementing :class:`OcrEngine` and passing it to the pipeline.
"""
from __future__ import annotations

import io
import shutil
from dataclasses import dataclass
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


LANG_CODES = {"en": "eng", "nl": "nld", "de": "deu", "fr": "fra", "es": "spa"}


class TesseractEngine:
    name = "Tesseract"

    def __init__(self, cmd: Optional[str] = None):
        self._cmd = cmd

    def available(self) -> bool:
        try:
            import pytesseract
        except ImportError:
            return False
        if self._cmd:
            pytesseract.pytesseract.tesseract_cmd = self._cmd
            return True
        return shutil.which("tesseract") is not None

    def languages(self) -> list[str]:
        import pytesseract
        try:
            installed = set(pytesseract.get_languages(config=""))
        except Exception:
            return []
        return [k for k, v in LANG_CODES.items() if v in installed]

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
    eng = TesseractEngine()
    return eng if eng.available() else None
