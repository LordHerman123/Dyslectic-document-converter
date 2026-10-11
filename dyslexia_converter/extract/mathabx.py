"""mathabx maths fonts (TeX-matha, -mathb, -mathx): their symbols by character code.

The Type 1 versions of these fonts carry Cork (T1) glyph names as placeholders ("abreve" for code 160) and
pdfTeX writes no Unicode map for them, so a PDF reader returns the T1 letter of each code ("ă" for a less-
than sign). The code is recovered from that letter, and the symbol from the code, after the font's own
declarations (mathabx.dcl and the Metafont driver files of the mathabx package by Anthony Phan).
Codes not listed here are left as they are.
"""
from __future__ import annotations

import re

FONT_RE = re.compile(r"^(TEX-)?MATH([ABX])\d+$", re.I)


def _table(spec: str) -> dict[int, str]:
    """'00+ 01− ...' (tab- or line-separated) -> {0: '+', 1: '−', ...}; an empty entry draws only part of a symbol."""
    out = {}
    for item in re.split(r"[\t\n]", spec):
        if item:
            out[int(item[:2], 16)] = item[2:]
    return out


# the T1 letter a PDF reader gives for each code (by its glyph name)
_T1 = '`´ˆ˜¨˝˚ˇ˘¯˙¸˛‚‹›“”„«»–—\x00‰ıȷﬀﬁﬂﬃﬄ␣!"#$%&’()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_‘abcdefghijklmnopqrstuvwxyz{|}~-ĂĄĆČĎĚĘĞĹĽŁŃŇŊŐŔŘŚŠŞŤŢŰŮŸŹŽŻĲİđ§ăąćčďěęğĺľłńňŋőŕřśšşťţűůÿźžżĳ¡¿£ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖŒØÙÚÛÜÝÞ\x00àáâãäåæçèéêëìíîïðñòóôõöœøùúûüýþß'
CODE = {}
for _code, _ch in enumerate(_T1):
    if _ch != "\x00":
        CODE.setdefault(_ch, _code)
CODE["\uf6be"] = 26  # another reading of "dotlessj"

MATHA = _table("""
00+	01−	02×	03÷	04·	05∘	06∗	08±	09∓	0A⋉	0B⋊	0C⋄	0D∙	0E⋆	10=	11≡	12∼	13≈	14≃	15≅	16≍	17∣	18≠	19≢	1A≁
1D≇	1F∤	20¬	21≪	22≫	23#	24⊢	25⊣	26⊬	28⊨	2A⊭	2C⊩	30°	31′	32″	33‴	35♭	36♮	37♯	38∞	39∝	3A†	3B‡	3C∑	3D∏
3E⨿	3F√	40∀	41∁	42∂	44∃	45∄	48∅	4A⊤	4B⊥	50∈	51∋	52∉	54∉	58∩	59∪	5A⊎	5B⊓	5C⊔	5E∧	5F∨	60⊕	61⊖	62⊗	64⊙
6D⊘	70(	71)	72[	73]	74{	75}	76⟦	77⟧	78⟨	79⟩	7A\	7B/	7C|	7D‖	80⊂	81⊃	82⊄	83⊅	84⊆	85⊇	86⊈	87⊉	88⊊	89⊋
8C⫅	8D⫆	94⋐	95⋑	98◁	99▷	9C⊴	9D⊵	A0<	A1>	A2≮	A3≯	A4≤	A5≥	A6≰	A7≱	A8⩽	A9⩾	AE≦	AF≧	B2≨	B3≩	B6⪕	B7⪖	BA≶
BB≷	C0≲	C1≳	C6⪅	C7⪆	CE⋘	CF⋙	D0←	D1→	D2↑	D3↓	D4↖	D5↗	D6↙	D7↘	D8↔	D9↕	DA↚	DB↛	DC↮	E0↼	E1⇀	E2↽	E3⇁	E8⇋
E9⇌	F0⇐	F1⇒	F2⇑	F3⇓	F4⇔	F5⇕	F6⇍	F7⇏	F8⇎
""")

MATHB = _table("""
00∔	05□	0B⋇	0E★	13≓	14≒	15≔	16≕	1A≗	1C≜	20≬	21⌣	22⌢	26⋔	27⋈	36∴	37∵	38˚	39˙	3A¨	3D∠	3E∡	58⊼	59⊻	5C⋒
5D⋓	60⊞	61⊟	62⊠	64⊡	70⟮	71⟯	72⌈	73⌉	74⌊	75⌋	78⌜	79⌝	7A⌞	7B⌟	7E|	80⊏	81⊐	84⊑	85⊒	A0≺	A1≻	A2⊀	A3⊁	A4≼
A5≽	A8⪯	A9⪰	C0≾	C1≿	D0⇇	D1⇉	D4⇆	D5⇄	E8↰	E9↱	EC↫	ED↬	F0↶	F1↷	F6↺	F7↻
""")

MATHX = _table("""
00(	01(	02(	03(	04(	05(	06	08)	09)	0A)	0B)	0C)	0D)	0E	10[	11[	12[	13[	14[	15[	16	18]	19]	1A]	1B]
1C]	1D]	1E	20{	21{	22{	23{	24{	25{	26	27	28}	29}	2A}	2B}	2C}	2D}	2E	2F	30⟦	31⟦	32⟦	33⟦	34⟦	35⟦	36
38⟧	39⟧	3A⟧	3B⟧	3C⟧	3D⟧	3E	40⟨	41⟨	42⟨	43⟨	44⟩	45⟩	46⟩	47⟩	48\	49\	4A\	4B\	4C/	4D/	4E/	4F/	50⌈	51⌈
52⌈	53⌈	54⌉	55⌉	56⌉	57⌉	58⌊	59⌊	5A⌊	5B⌊	5C⌋	5D⌋	5E⌋	5F⌋	60√	61√	62√	63√	64√	65√	66	67√	70ˆ	71ˇ	72˜
73¯	78ˆ	79ˆ	7Aˆ	7Bˆ	7Cˇ	7Dˇ	7Eˇ	7Fˇ	80˜	81˜	82˜	83˜	84¯	85¯	86¯	87¯	91⨉	93⋂	94⋃	95⨄	96⨅	97⨆	99⋀	9A⋁
A1⨉	A3⋂	A4⋃	A5⨄	A6⨅	A7⨆	A9⋀	AA⋁	B0∑	B1∏	B2∐	B3∫	B4∬	B5∭	B6∮	B7∯	B8∑	B9∏	BA∐	BB∫	BC∬	BD∭	BE∮	BF∯
""")

_FAMILIES = {"A": MATHA, "B": MATHB, "X": MATHX}


def symbol(font: str, ch: str):
    """The symbol a mathabx character shows, or None when the font is not mathabx or the code is unknown."""
    m = FONT_RE.match(font)
    if not m or ch not in CODE:
        return None
    return _FAMILIES[m.group(2).upper()].get(CODE[ch])
