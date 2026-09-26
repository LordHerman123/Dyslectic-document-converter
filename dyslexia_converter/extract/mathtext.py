"""Mathematics in PDF text: which fonts carry maths, and how their characters map to Unicode.

TeX papers set maths in special fonts (Computer Modern Math Italic/Symbols/Extension, the AMS fonts,
STIX, Cambria Math, ...). Most of their characters come out of the PDF as proper Unicode, but a few
fonts use their own codes: the big-operator font CMEX gives 'P' for a sum sign and control characters
for large brackets, and the AMS blackboard font gives a plain 'R' for the real numbers.
The author's text is never touched by this: it only affects maths fonts.
"""
from __future__ import annotations

import re

# fonts that only ever hold mathematics
MATH_FONT_RE = re.compile(
    r"^(CMMI|CMMIB|CMSY|CMBSY|CMEX|MSAM|MSBM|EUFM|EUFB|EURM|EUSM|EUSB|EUEX|RSFS|STMARY|WASY|LASY|"
    r"TXMI|TXSY|TXEX|PXMI|PXSY|PXEX|NTXMI|NTXSY|NTXEX|ZXMI|ZXSY|MNSYMBOL|ESINT|"
    r"MTMI|MTMIB|MTMIS|MTSY|MTSYN|MTSYB|MTEX|MTEXB|MTMS|MTGU|MT2\w+|RMTMI|RMTSY|RMTEX|"
    r"STIXMATH|STIXTWOMATH|XITSMATH|LATINMODERNMATH|TEXGYRE\w*MATH|ASANAMATH|LIBERTINUSMATH|"
    r"CAMBRIAMATH|CAMBRIA-MATH|SYMBOL|STANDARDSYM|ZPTMCM|ZPZCM|RTXMI|RTXSY|MT-?EXTRA|EUCLID|MATHEMATICAL|"
    r"MATHPI|UNIVERSALMATH)",
    re.I)
# TeX text fonts that also appear inside formulas (digits, operators, function names)
TEX_TEXT_FONT_RE = re.compile(r"^(CMR|CMBX|CMSL|CMTI|CMSS|LMROMAN|LMRoman|SFRM|SFBX)", re.I)


def base_font(name: str) -> str:
    """'ABCDEF+CMMI10' -> 'CMMI10'."""
    return name.split("+", 1)[-1]


def is_math_font(name: str) -> bool:
    return bool(MATH_FONT_RE.match(base_font(name).replace(" ", "")))


def is_math_italic(name: str) -> bool:
    """Math italic fonts: their letters are variables and are shown in italic."""
    return bool(re.match(r"^(CMMI|TXMI|PXMI|NTXMI|ZXMI|EURM|MTMI|RMTMI)", base_font(name), re.I))


# AMS blackboard bold (MSBM) and TeX calligraphic capitals (CMSY) are stored as plain letters
_DOUBLE_STRUCK = {"C": "ℂ", "H": "ℍ", "N": "ℕ", "P": "ℙ", "Q": "ℚ", "R": "ℝ", "Z": "ℤ"}
_SCRIPT = {"B": "ℬ", "E": "ℰ", "F": "ℱ", "H": "ℋ", "I": "ℐ", "L": "ℒ", "M": "ℳ", "R": "ℛ"}

# TeX math extension font (CMEX): big delimiters, operators and radicals, by character code
_CMEX: dict[int, str] = {}
for codes, ch in [((0x00, 0x10, 0x12, 0x20, 0x30, 0x40), "("), ((0x01, 0x11, 0x13, 0x21, 0x31, 0x41), ")"),
                  ((0x02, 0x14, 0x22, 0x32, 0x36, 0x68), "["), ((0x03, 0x15, 0x23, 0x33, 0x37, 0x69), "]"),
                  ((0x04, 0x16, 0x24, 0x6A), "⌊"), ((0x05, 0x17, 0x25, 0x6B), "⌋"),
                  ((0x06, 0x18, 0x26, 0x6C), "⌈"), ((0x07, 0x19, 0x27, 0x6D), "⌉"),
                  ((0x08, 0x1A, 0x28, 0x38, 0x3A, 0x3C, 0x6E), "{"), ((0x09, 0x1B, 0x29, 0x39, 0x3B, 0x3D, 0x6F), "}"),
                  ((0x0A, 0x1C, 0x2A, 0x44), "⟨"), ((0x0B, 0x1D, 0x2B, 0x45), "⟩"),
                  ((0x0C, 0x42, 0x43), "|"), ((0x0D, 0x77), "‖"), ((0x0E, 0x1E, 0x2C), "/"),
                  ((0x0F, 0x1F, 0x2D), "\\"), ((0x46, 0x47), "⨆"), ((0x48, 0x49), "∮"),
                  ((0x4A, 0x4B), "⨀"), ((0x4C, 0x4D), "⨁"), ((0x4E, 0x4F), "⨂"),
                  ((0x50, 0x58), "∑"), ((0x51, 0x59), "∏"), ((0x52, 0x5A), "∫"), ((0x53, 0x5B), "⋃"),
                  ((0x54, 0x5C), "⋂"), ((0x55, 0x5D), "⨄"), ((0x56, 0x5E), "⋀"), ((0x57, 0x5F), "⋁"),
                  ((0x60, 0x61), "∐"), ((0x70, 0x71, 0x72, 0x73, 0x74), "√")]:
    for c in codes:
        _CMEX[c] = ch


def math_char(font: str, ch: str) -> str:
    """Unicode for one character of a maths font ("" for pieces that only draw part of a symbol)."""
    name = base_font(font).upper()
    o = ord(ch)
    if 0xE000 <= o <= 0xF8FF:  # private-use pieces of large brackets
        return ""
    if name.startswith(("CMEX", "TXEX", "PXEX", "NTXEX", "EUEX", "MTEX", "RMTEX")):
        if o in _CMEX:
            return _CMEX[o]
        if 0x62 <= o <= 0x67 or 0x3E <= o <= 0x3F or 0x74 < o <= 0x7F:
            return ""  # wide accents, brace middles/tips, radical extensions
        return ch if ch.isprintable() and o > 0x20 else ""
    if name.startswith(("MSBM", "TXMIA", "BBOLD", "DSROM")) and ch in _DOUBLE_STRUCK:
        return _DOUBLE_STRUCK[ch]
    if name.startswith(("CMSY", "CMBSY", "MTSY")) and ch == "7":
        return ""  # the bar of a "maps to" arrow; the arrow follows as its own character
    if name.startswith(("CMSY", "CMBSY", "TXSY", "PXSY", "RSFS", "EUSM", "EUSB")) and "A" <= ch <= "Z":
        # calligraphic and script capitals
        return _SCRIPT.get(ch, ch)
    if o < 0x20:
        return ""
    return ch


def math_text(font: str, text: str) -> str:
    return "".join(math_char(font, c) for c in text)
