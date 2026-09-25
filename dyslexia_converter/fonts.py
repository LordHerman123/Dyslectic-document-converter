"""Font discovery and registration.

Open-licensed fonts (Atkinson Hyperlegible, OpenDyslexic, Liberation Sans/Serif,
DejaVu Sans) are bundled. Proprietary fonts (Arial, Verdana, Tahoma, and Times New
Roman for formulas) are used from the operating system when installed; otherwise a
metrically similar free font is substituted and the substitution is reported to the user.

No font is claimed to be universally best for dyslexia.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

ASSET_DIR = Path(__file__).parent / "assets" / "fonts"


@dataclass(frozen=True)
class FontFamily:
    name: str
    regular: str
    bold: str
    italic: str
    bold_italic: str
    substitute_note: str = ""  # non-empty when a substitute font is used


_BUNDLED = {
    "Atkinson Hyperlegible": ("AtkinsonHyperlegible-Regular.ttf", "AtkinsonHyperlegible-Bold.ttf",
                              "AtkinsonHyperlegible-Italic.ttf", "AtkinsonHyperlegible-BoldItalic.ttf"),
    "OpenDyslexic": ("OpenDyslexic-Regular.ttf", "OpenDyslexic-Bold.ttf",
                     "OpenDyslexic-Italic.ttf", "OpenDyslexic-BoldItalic.ttf"),
    "Liberation Sans": ("LiberationSans-Regular.ttf", "LiberationSans-Bold.ttf",
                        "LiberationSans-Italic.ttf", "LiberationSans-BoldItalic.ttf"),
    "Liberation Serif": ("LiberationSerif-Regular.ttf", "LiberationSerif-Bold.ttf",
                         "LiberationSerif-Italic.ttf", "LiberationSerif-BoldItalic.ttf"),
    "DejaVu Sans": ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
}

# System font file names (Windows / macOS / Linux msttcorefonts)
_SYSTEM = {
    "Arial": (("arial.ttf", "Arial.ttf"), ("arialbd.ttf", "Arial Bold.ttf", "Arial_Bold.ttf"),
              ("ariali.ttf", "Arial Italic.ttf", "Arial_Italic.ttf"),
              ("arialbi.ttf", "Arial Bold Italic.ttf", "Arial_Bold_Italic.ttf")),
    "Verdana": (("verdana.ttf", "Verdana.ttf"), ("verdanab.ttf", "Verdana Bold.ttf", "Verdana_Bold.ttf"),
                ("verdanai.ttf", "Verdana Italic.ttf", "Verdana_Italic.ttf"),
                ("verdanaz.ttf", "Verdana Bold Italic.ttf", "Verdana_Bold_Italic.ttf")),
    "Tahoma": (("tahoma.ttf", "Tahoma.ttf"), ("tahomabd.ttf", "Tahoma Bold.ttf", "Tahoma_Bold.ttf"),
               ("tahoma.ttf", "Tahoma.ttf"), ("tahomabd.ttf", "Tahoma Bold.ttf", "Tahoma_Bold.ttf")),
    "Times New Roman": (("times.ttf", "Times New Roman.ttf", "Times_New_Roman.ttf"),
                        ("timesbd.ttf", "Times New Roman Bold.ttf", "Times_New_Roman_Bold.ttf"),
                        ("timesi.ttf", "Times New Roman Italic.ttf", "Times_New_Roman_Italic.ttf"),
                        ("timesbi.ttf", "Times New Roman Bold Italic.ttf", "Times_New_Roman_Bold_Italic.ttf")),
}
_SUBSTITUTES = {"Arial": "Liberation Sans", "Verdana": "DejaVu Sans", "Tahoma": "DejaVu Sans",
                "Times New Roman": "Liberation Serif"}

FONT_CHOICES = ["DejaVu Sans", "Atkinson Hyperlegible", "OpenDyslexic", "Verdana", "Arial", "Tahoma", "Liberation Sans"]
FALLBACK_FAMILY = "DejaVu Sans"  # wide Unicode coverage, used per character
# formulas are set like in most papers: Times New Roman (or its free metric twin Liberation Serif)
MATH_FAMILY = "Times New Roman"


def _system_font_dirs() -> list[Path]:
    dirs: list[Path] = []
    if sys.platform.startswith("win"):
        dirs.append(Path(os.environ.get("WINDIR", "C:\\Windows")) / "Fonts")
        local = os.environ.get("LOCALAPPDATA")
        if local:
            dirs.append(Path(local) / "Microsoft" / "Windows" / "Fonts")
    elif sys.platform == "darwin":
        dirs += [Path("/Library/Fonts"), Path("/System/Library/Fonts/Supplemental"),
                 Path.home() / "Library" / "Fonts"]
    else:
        dirs += [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts",
                 Path.home() / ".local/share/fonts", Path("/system/fonts")]
    return [d for d in dirs if d.is_dir()]


@lru_cache(maxsize=None)
def _system_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for d in _system_font_dirs():
        for root, _dirs, files in os.walk(d):
            for f in files:
                if f.lower().endswith(".ttf"):
                    index.setdefault(f.lower(), os.path.join(root, f))
    return index


def _find_system(candidates: tuple[str, ...]) -> Optional[str]:
    index = _system_index()
    for c in candidates:
        if c.lower() in index:
            return index[c.lower()]
    return None


@lru_cache(maxsize=None)
def get_family(name: str) -> FontFamily:
    if name in _BUNDLED:
        paths = [str(ASSET_DIR / f) for f in _BUNDLED[name]]
        return FontFamily(name, *paths)
    if name in _SYSTEM:
        found = [_find_system(c) for c in _SYSTEM[name]]
        if found[0]:
            reg = found[0]
            bold = found[1] or reg
            return FontFamily(name, reg, bold, found[2] or reg, found[3] or bold)
        sub = _SUBSTITUTES[name]
        fam = get_family(sub)
        note = f"{name} is not installed on this device; using the similar free font {sub} instead."
        return FontFamily(name, fam.regular, fam.bold, fam.italic, fam.bold_italic, note)
    return get_family("Atkinson Hyperlegible")


def font_path(family: str, bold: bool = False, italic: bool = False) -> str:
    fam = get_family(family)
    if bold and italic:
        return fam.bold_italic
    if bold:
        return fam.bold
    if italic:
        return fam.italic
    return fam.regular
