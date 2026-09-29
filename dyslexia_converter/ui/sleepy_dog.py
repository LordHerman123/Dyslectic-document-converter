"""Bobby, the little sleeping labradoodle shown while focus mode prepares its pages and before a PDF is open.

The animation is ``assets/sleepy_dog.webp`` (drawn by ``tools/make_sleepy_dog.py``); its background is transparent,
so it suits the light and the dark theme.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import flet as ft

_ASSET = Path(__file__).resolve().parent.parent / "assets" / "sleepy_dog.webp"


@lru_cache(maxsize=1)
def _dog_bytes() -> bytes:
    try:
        return _ASSET.read_bytes()
    except OSError:  # a build without the picture still works, just without the dog
        return b""


def sleepy_dog(width: float = 240) -> ft.Control:
    """The dog, ``width`` pixels wide (nothing when the picture is missing)."""
    data = _dog_bytes()
    if not data:
        return ft.Container(width=0, height=0)
    return ft.Image(src=data, width=width, height=width * 170 / 240, fit=ft.BoxFit.CONTAIN,
                    semantics_label="Bobby the labradoodle, asleep")
