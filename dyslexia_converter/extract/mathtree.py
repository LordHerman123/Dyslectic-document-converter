"""The structure of a display formula, read from the PDF's own glyphs (no OCR), written as linear text.

A born-digital PDF gives every symbol of a formula with its position, size and font, and draws fraction bars and
radical lines as thin rules. This module arranges those pieces into a layout tree the way the formula was typeset
(baseline-structure analysis after Zanibbi et al. 2002, applied to PDF glyphs as in Baker, Sexton & Sorge 2009/2010):

* a rule with symbols above and below is a fraction, a rule over a radical sign is the radical's extent;
* smaller symbols raised or lowered after a symbol are its super- and subscripts (recursively);
* symbols directly above or below a big operator (∑, ∏, lim, max, ...) are its limits;
* tall brackets around several rows are a matrix, a tall brace with rows after it is a "cases" block;
* accents over a symbol, rows of an aligned derivation, and a trailing equation number are recognised.

The result is linear text that keeps the structure:  ``A = softmax((QK^T)/(√d_k))V``,  ``∑_(i=1)^n x_i``.

It never invents anything: every printed symbol is used exactly once and nothing else is added except brackets,
``^ _ /`` and the words ``matrix``, ``cases``, ``hat``, ``bar``, ``tilde``. When a piece cannot be placed with
confidence the function returns None and the caller keeps its previous text.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from typing import Optional

import pymupdf

from .mathtext import base_font, is_math_font, is_math_italic, math_char

# each part of the structure analysis can be switched off, to measure what it contributes (all on in normal use)
ENABLED = {"fractions": True, "radicals": True, "limits": True, "scripts": True, "matrices": True,
           "accents": True, "rows": True, "number": True}

LOG: list[str] = []  # why recent formulas fell back (for diagnosis)
BIG_OPS = set("∑∏∐⋃⋂⨁⨂⨀⨄⋀⋁")
LIMIT_WORDS = {"lim", "max", "min", "argmax", "argmin", "sup", "inf", "limsup", "liminf"}
FUNCTION_WORDS = {"lim", "log", "ln", "exp", "sin", "cos", "tan", "tanh", "max", "min", "argmax", "argmin",
                  "softmax", "sup", "inf", "det", "rank", "concat", "relu", "sigmoid", "diag"}
NEGATED = {"=": "≠", "∈": "∉", "<": "≮", ">": "≯", "≤": "≰", "≥": "≱", "≡": "≢", "∼": "≁", "≈": "≉", "⊂": "⊄",
           "⊆": "⊈", "∃": "∄"}
ACCENTS = {"ˆ": "hat", "^": "hat", "˜": "tilde", "~": "tilde", "¯": "bar", "ˉ": "bar", "˙": "dot", "¨": "ddot"}
OPEN, CLOSE = "([{⟨⌊⌈|‖", ")]}⟩⌋⌉|‖"
PAIRS = {"(": ")", "[": "]", "{": "}", "|": "|", "‖": "‖", "⟨": "⟩"}
EXT_FONT = re.compile(r"^(CMEX|TXEX|PXEX|NTXEX|EUEX|MTEX|RMTEX)", re.I)
NUMBER = re.compile(r"^\((\d{1,3}[a-z]?)\)$")


class Unsure(Exception):
    """A piece of the formula could not be placed with confidence."""


@dataclass
class Atom:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    base: float  # baseline (for built pieces: the baseline they sit on)
    size: float
    kind: str = "sym"  # sym / word / big / rule / node
    upright: bool = False
    accent: str = ""  # for accent glyphs
    single: bool = True  # written as one token (needs no brackets as a script, numerator, ...)
    glyphs: int = 1
    top: float = 0.0  # big glyphs: their origin (TeX hangs them from it)

    @property
    def cx(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def cy(self) -> float:
        return (self.y0 + self.y1) / 2


def _group(text: str, single: bool) -> str:
    return text if single else f"({text})"


def _is_single(text: str) -> bool:
    t = text.strip()
    return bool(re.fullmatch(r"[^\W\d_]|\d+(?:\.\d+)?|[^\w\s()]", t)) or t.lower() in FUNCTION_WORDS \
        or bool(re.fullmatch(r"\(.*\)", t) and _balanced_outer(t))


def _balanced_outer(t: str) -> bool:
    """'(a+b)' is one bracketed group; '(a)+(b)' is not."""
    depth = 0
    for k, c in enumerate(t):
        depth += (c == "(") - (c == ")")
        if depth == 0 and k < len(t) - 1:
            return False
    return depth == 0


def _node(text: str, members: list[Atom], base: float, size: float, single: Optional[bool] = None) -> Atom:
    return Atom(text, min(a.x0 for a in members), min(a.y0 for a in members), max(a.x1 for a in members),
                max(a.y1 for a in members), base, size, kind="node",
                single=_is_single(text) if single is None else single, glyphs=sum(a.glyphs for a in members))


# ----------------------------------------------------------------------------------------------- reading the page
def _glyphs(page: pymupdf.Page, rect: pymupdf.Rect, areas: Optional[list] = None) -> list[Atom]:
    d = page.get_text("rawdict", clip=rect + (-2, -2, 2, 2), flags=pymupdf.TEXTFLAGS_RAWDICT
                      & ~pymupdf.TEXT_PRESERVE_IMAGES)
    out: list[Atom] = []
    for block in d["blocks"]:
        for line in block.get("lines", []):
            if abs(line["dir"][1]) > 0.01 or line["dir"][0] < 0:
                raise Unsure("rotated text")
            for span in line["spans"]:
                font = span["font"]
                ext = bool(EXT_FONT.match(base_font(font)))
                for c in span["chars"]:
                    ox, oy = c["origin"]
                    if not (rect.x0 - 1 <= ox <= rect.x1 + 1 and rect.y0 - 2 <= oy <= rect.y1 + 2):
                        continue
                    cx = (c["bbox"][0] + c["bbox"][2]) / 2
                    ch, tall = c["c"], ext or c["c"] == "√" or c["c"] == "∫"  # tall glyphs hang from their origin
                    mid = oy - 0.3 * span["size"]
                    if areas and not tall and not any(a[0] - 1 <= cx <= a[2] + 1 and a[1] - 1 <= mid <= a[3] + 1
                                                      for a in areas):
                        continue  # a neighbouring line of text, not part of this formula
                    t = math_char(font, ch) if is_math_font(font) or ext else ch
                    code = ord(ch) if len(ch) == 1 else 0
                    accent = ""
                    if ext and 0x62 <= code <= 0x67:
                        accent = "hat" if code <= 0x64 else "tilde"  # wide accents
                    if not t.strip() and not accent:
                        if ext and ch.strip():
                            raise Unsure("piece of a built-up symbol")
                        continue
                    if t in ACCENTS and not accent:
                        accent = ACCENTS[t]
                    size = span["size"]
                    x0, _y0, x1, _y1 = c["bbox"]
                    if any(o.text == t and abs(o.x0 - x0) < 0.5 and abs(o.base - oy) < 0.5 for o in out):
                        continue  # the same glyph drawn twice (fake bold, stacked text layers)
                    big = ext or t == "√"
                    out.append(Atom(t, x0, oy - 0.70 * size, x1, oy + 0.20 * size, oy, size,
                                    kind="big" if big else "sym",
                                    upright=not is_math_italic(font) and not is_math_font(font), accent=accent))
    return out


def _rules(drawings: list, rect: pymupdf.Rect) -> list[Atom]:
    out = []
    for r in drawings:
        x0, y0, x1, y1 = r
        if y1 - y0 < 1.6 and x1 - x0 > 1.5 and x0 < rect.x1 + 1 and x1 > rect.x0 - 1 \
                and rect.y0 - 2 <= (y0 + y1) / 2 <= rect.y1 + 2:
            y = (y0 + y1) / 2
            out.append(Atom("", x0, y, x1, y, y, 0.0, kind="rule", glyphs=0))
    return out


def _ink_extents(page: pymupdf.Page, rect: pymupdf.Rect, atoms: list[Atom], rules: list[Atom]) -> None:
    """Big symbols (TeX extension font, radicals) report the height of an ordinary letter; measure their real
    height from the rendered ink in their own column (rules blanked out), starting at the glyph's origin."""
    big = [a for a in atoms if a.kind == "big"]
    if not big:
        return
    zoom = 4.0
    clip = rect + (-1, -6, 1, 6)
    pix = page.get_pixmap(clip=clip, matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csGRAY, alpha=False)
    w, h = pix.width, pix.height
    data = bytearray(pix.samples)
    for r in rules:  # blank the rules (fraction bars, radical lines) so they do not join glyphs
        r0, r1 = max(0, int((r.y0 - clip.y0) * zoom) - 2), min(h - 1, int((r.y1 - clip.y0) * zoom) + 2)
        q0, q1 = max(0, int((r.x0 - clip.x0) * zoom) - 1), min(w, int((r.x1 - clip.x0) * zoom) + 2)
        for y in range(r0, r1 + 1):
            data[y * w + q0:y * w + q1] = b"\xff" * (q1 - q0)

    def inked(row: int, c0: int, c1: int) -> bool:
        return min(data[row * w + c0:row * w + c1]) < 140

    for a in big:
        c0 = max(0, int((a.x0 - clip.x0) * zoom) + 1)
        c1 = min(w, int((a.x1 - clip.x0) * zoom) - 1)
        if c1 <= c0:
            continue
        rows = [y for y in range(h) if inked(y, c0, c1)]
        if not rows:
            continue
        start = int((a.base - clip.y0) * zoom)
        runs, cur = [], [rows[0]]
        for y in rows[1:]:
            if y - cur[-1] <= 3:
                cur.append(y)
            else:
                runs.append(cur)
                cur = [y]
        runs.append(cur)
        # the run that holds the origin row (TeX big glyphs hang from it), else the nearest one
        run = min(runs, key=lambda r: 0 if r[0] - 3 <= start <= r[-1] + 3 else min(abs(r[0] - start),
                                                                                   abs(r[-1] - start)))
        a.y0, a.y1 = clip.y0 + run[0] / zoom, clip.y0 + (run[-1] + 1) / zoom


def _axis_bases(atoms: list[Atom], body: float) -> None:
    """Big symbols are centred on the maths axis, a quarter em above the baseline."""
    for a in atoms:
        if a.kind == "big":
            a.top = a.base  # TeX big glyphs hang from their origin (radicals are found by it)
            a.base = a.cy + 0.25 * body


# ----------------------------------------------------------------------------------------------- structure
class _Builder:
    def __init__(self, atoms: list[Atom], rules: list[Atom], body: float):
        self.body = body
        self.atoms = atoms
        self.rules = rules

    # words: upright letters set together (softmax, lim, model)
    def words(self) -> None:
        def letter(a: Atom) -> bool:
            return a.kind == "sym" and a.upright and a.text.isalpha() and not a.accent

        def follows(p: Atom, a: Atom) -> bool:
            return abs(a.base - p.base) < 0.1 * a.size and abs(a.size - p.size) < 0.3 \
                and -0.5 < a.x0 - p.x1 < 0.12 * a.size

        out = [a for a in self.atoms if not letter(a)]
        pending = sorted([a for a in self.atoms if letter(a)], key=lambda a: a.x0)
        while pending:
            run = [pending.pop(0)]
            while True:
                nxt = next((a for a in pending if follows(run[-1], a)), None)
                if nxt is None:
                    break
                pending.remove(nxt)
                run.append(nxt)
            if len(run) == 1:
                out.append(run[0])
                continue
            word = "".join(a.text for a in run)
            out.append(Atom(word, run[0].x0, min(a.y0 for a in run), run[-1].x1, max(a.y1 for a in run),
                            run[0].base, run[0].size, kind="word", upright=True, glyphs=len(run),
                            single=word.lower() in FUNCTION_WORDS))
        # numbers: digits (and a decimal point between digits) set together on one baseline
        def digit(a: Atom) -> bool:
            return a.kind == "sym" and bool(re.fullmatch(r"[\d.]", a.text))

        rest = [a for a in out if not digit(a)]
        pending = sorted([a for a in out if digit(a)], key=lambda a: a.x0)
        while pending:
            run = [pending.pop(0)]
            while True:
                nxt = next((a for a in pending if follows(run[-1], a)), None)
                if nxt is None:
                    break
                pending.remove(nxt)
                run.append(nxt)
            while len(run) > 1 and run[-1].text == ".":  # a full stop after a number is punctuation
                pending.append(run.pop())
                pending.sort(key=lambda a: a.x0)
            if len(run) == 1 or run[0].text == ".":
                rest.extend(run[:1])
                for a in run[1:]:
                    pending.append(a)
                pending.sort(key=lambda a: a.x0)
                continue
            rest.append(Atom("".join(a.text for a in run), run[0].x0, min(a.y0 for a in run), run[-1].x1,
                             max(a.y1 for a in run), run[0].base, run[0].size, kind="num", glyphs=len(run)))
        self.atoms = rest

    def negations(self) -> None:
        """TeX writes ≠ as a slash laid over '=': one symbol."""
        for slash in [a for a in self.atoms if a.text in ("\u0338", "̸", "/") and a.kind == "sym"]:
            rel = [b for b in self.atoms if b.text in NEGATED and abs(b.base - slash.base) < 0.2 * b.size
                   and (min(b.x1, slash.x1) - max(b.x0, slash.x0) > 0.5 * min(b.x1 - b.x0, slash.x1 - slash.x0)
                        if slash.text == "/" else  # TeX's slash has no width: it is drawn over what follows
                        b.x0 - 1 <= slash.cx <= b.x1 + 1 or 0 <= b.x0 - slash.x1 < 0.6 * b.size)]
            if not rel:
                if slash.text != "/":
                    raise Unsure("negation slash without a relation")
                continue
            r = rel[0]
            self.take([slash, r])
            self.atoms.append(Atom(NEGATED[r.text], r.x0, r.y0, max(r.x1, slash.x1), r.y1, r.base,
                                   r.size, glyphs=2))

    def take(self, chosen: list[Atom]) -> None:
        ids = {id(a) for a in chosen}
        self.atoms = [a for a in self.atoms if id(a) not in ids]

    def accents(self) -> None:
        for acc in [a for a in self.atoms if a.accent]:
            under = [b for b in self.atoms if b is not acc and not b.accent and b.kind != "rule"
                     and min(b.x1, acc.x1) - max(b.x0, acc.x0) > 0.4 * min(acc.x1 - acc.x0, b.x1 - b.x0)
                     and b.base >= acc.base - 0.15 * b.size and b.y0 < acc.base + 0.3 * b.size]
            if not under:
                raise Unsure("accent without a symbol")
            under.sort(key=lambda b: b.x0)
            inner = self.row(under) if len(under) > 1 else under[0].text
            self.take(under + [acc])
            main = max(under, key=lambda b: b.size)
            self.atoms.append(_node(f"{acc.accent}({inner})", under, main.base, main.size, single=True))

    def _side(self, rule: Atom, above: bool) -> list[Atom]:
        """Symbols stacked directly above (or below) a rule, not crossing another rule."""
        span = [a for a in self.atoms if a.kind != "rule" and rule.x0 - 1 <= a.cx <= rule.x1 + 1
                and ((a.y1 <= rule.base + 0.8) if above else (a.y0 >= rule.base - 0.8))]
        others = [r for r in self.rules if r is not rule and min(r.x1, rule.x1) - max(r.x0, rule.x0) > 0]
        chosen: list[Atom] = []
        edge = rule.base
        for a in sorted(span, key=lambda a: -a.y1 if above else a.y0):
            gap = (edge - a.y1) if above else (a.y0 - edge)
            if gap > 0.55 * max(a.size, self.body * 0.6):
                break
            if any((a.y1 <= r.base <= rule.base) if above else (rule.base <= r.base <= a.y0) for r in others
                   if r.x0 - 1 <= a.cx <= r.x1 + 1):
                continue
            chosen.append(a)
            edge = min(edge, a.y0) if above else max(edge, a.y1)
        if chosen:
            # one row next to the bar (with its smaller scripts): a symbol as large as that row's but on another
            # baseline belongs to something else (a script of the symbol before the fraction)
            # the first layer: symbols right at the bar; the largest of them is the row next to the bar (not a
            # script of it, and not a line further up that the chain reached)
            def gap(a: Atom) -> float:
                return (rule.base - a.y1) if above else (a.y0 - rule.base)
            first = [a for a in chosen if gap(a) < gap(chosen[0]) + 0.35 * a.size]
            near = max(first, key=lambda a: a.size)
            chosen = [a for a in chosen if a.kind in ("node", "op") or abs(a.base - near.base) < 0.5 * near.size
                      or a.size < 0.9 * near.size]
        return chosen

    def radicals(self) -> None:
        for root in sorted([a for a in self.atoms if a.text == "√"], key=lambda a: a.x1 - a.x0):
            bar = [r for r in self.rules if abs(r.x0 - root.x1) < 2.0
                   and (abs(r.base - root.y0) < 2.5 or abs(r.base - root.top) < 2.5)]
            if not bar:
                continue  # drawn as one glyph: leave the sign as a symbol
            rule = min(bar, key=lambda r: abs(r.x0 - root.x1))
            inside = [a for a in self.atoms if a is not root and rule.x0 - 0.5 <= a.cx <= rule.x1 + 0.5
                      and rule.base - 0.5 <= a.cy <= root.y1 + 0.5]
            index = [a for a in self.atoms if a is not root and a.size < 0.8 * root.size
                     and root.x0 <= a.cx <= root.x0 + 0.6 * (root.x1 - root.x0)  # over the sign's left part
                     and a.y1 <= root.cy and a.y0 >= root.y0 - root.size]
            if not inside:
                raise Unsure("empty radical")
            self.rules.remove(rule)
            body = self.row(inside)
            single = len(inside) == 1 and inside[0].single
            text = "√" + (f"[{self.row(index)}]" if index else "") + _group(body, single)
            members = inside + index + [root]
            self.take(members)
            self.atoms.append(_node(text, members, max(a.base for a in inside if a.kind != "rule"),
                                    max(a.size for a in inside), single=False))

    def fractions(self) -> None:
        for rule in sorted(list(self.rules), key=lambda r: r.x1 - r.x0):
            num, den = self._side(rule, True), self._side(rule, False)
            if not num and not den:
                continue
            if not num or not den:
                if den and ENABLED["accents"]:  # a line over symbols: overline / bar
                    inner = self.row(den)
                    self.rules.remove(rule)
                    self.take(den)
                    main = max(den, key=lambda b: b.size)
                    self.atoms.append(_node(f"bar({inner})", den, main.base, main.size, single=True))
                    continue
                raise Unsure("rule with nothing above or below")
            n, dn = self.row(num), self.row(den)
            ns = len(num) == 1 and num[0].single
            ds = len(den) == 1 and den[0].single
            self.rules.remove(rule)
            self.take(num + den)
            size = max(a.size for a in num + den)
            self.atoms.append(_node(f"{_group(n, ns)}/{_group(dn, ds)}", num + den, rule.base + 0.25 * size, size,
                                    single=False))

    def limits(self) -> None:
        ops = [a for a in self.atoms if (a.text in BIG_OPS and a.kind == "big") or
               (a.kind == "word" and a.text.lower() in LIMIT_WORDS)]
        for op in ops:
            if op not in self.atoms:
                continue
            under, over = self._stack(op, below=True), self._stack(op, below=False)
            if not under and not over:
                continue
            text = op.text
            if under:
                text += "_" + _group(self.row(under, sep=" "), len(under) == 1 and under[0].single)
            if over:
                text += "^" + _group(self.row(over, sep=" "), len(over) == 1 and over[0].single)
            members = [op] + under + over
            self.take(members)
            base = op.base if op.kind == "word" else op.cy + 0.25 * self.body
            self.atoms.append(_node(text, members, base, self.body if op.kind == "big" else op.size, single=False))
            self.atoms[-1].kind = "op"

    def _stack(self, op: Atom, below: bool) -> list[Atom]:
        """Limits set under (over) an operator: smaller symbols starting within its width, plus whatever continues
        them sideways and their own scripts."""
        def placed(a: Atom) -> bool:
            if op.kind == "word":  # a word's box is only nominal: go by baselines
                return a.base - op.base > 0.45 * op.size if below else op.base - a.base > 0.8 * op.size
            return a.y0 >= op.y1 - 0.15 * a.size if below else a.y1 <= op.y0 + 0.15 * a.size

        def near(a: Atom) -> bool:
            if op.kind == "word":
                return abs(a.base - op.base) < 1.6 * op.size
            return (a.y0 - op.y1 if below else op.y0 - a.y1) < 0.6 * self.body

        seeds = [a for a in self.atoms if a is not op and min(a.x1, op.x1) - max(a.x0, op.x0) > 0.2 * (a.x1 - a.x0)
                 and placed(a) and near(a) and a.size <= 0.9 * max(op.size, self.body)]
        others = [o for o in self.atoms if o is not op and ((o.text in BIG_OPS and o.kind == "big") or
                                                          (o.kind == "word" and o.text.lower() in LIMIT_WORDS))]

        def own(a: Atom) -> bool:
            """Not under (over) a neighbouring operator."""
            return not any(o.x0 - 0.5 <= a.cx <= o.x1 + 0.5 for o in others)

        seeds = [a for a in seeds if own(a)]
        chosen = list(seeds)
        grown = True
        while grown:
            grown = False
            for a in self.atoms:
                if a is op or a in chosen or a.size > 0.9 * max(op.size, self.body):
                    continue
                if not placed(a) or not own(a):
                    continue
                if any(min(a.y1, c.y1) - max(a.y0, c.y0) > 0.2 * a.size and
                       -0.6 * c.size < a.x0 - c.x1 < 0.6 * c.size or
                       -0.6 * c.size < c.x0 - a.x1 < 0.6 * c.size and min(a.y1, c.y1) - max(a.y0, c.y0) > 0.2 * a.size
                       for c in chosen):
                    chosen.append(a)
                    grown = True
        return chosen

    def matrices(self) -> None:
        tall = [a for a in self.atoms if a.kind == "big" and (a.text in OPEN or a.text in CLOSE)
                and a.y1 - a.y0 > 1.5 * self.body]
        for left in sorted([a for a in tall if a.text in OPEN], key=lambda a: a.x1 - a.x0):
            if left not in self.atoms:
                continue
            rights = [a for a in tall if a.text in CLOSE and a.x0 > left.x1 and a in self.atoms
                      and min(a.y1, left.y1) - max(a.y0, left.y0) > 0.7 * (left.y1 - left.y0)
                      and a.text == PAIRS.get(left.text)]
            right = min(rights, key=lambda a: a.x0) if rights else None
            if right is None and left.text != "{":
                continue
            x1 = right.x0 if right else max(a.x1 for a in self.atoms)
            inside = [a for a in self.atoms if a is not left and a is not right and left.x1 - 0.5 <= a.cx <= x1 + 0.5
                      and left.y0 - 1 <= a.cy <= left.y1 + 1]
            if not inside:
                raise Unsure("empty brackets")
            rows = self._rows(inside)
            if len(rows) < 2:
                if right is None:
                    continue  # a big brace before one row: an ordinary symbol
                text = f"{left.text}{self.row(inside)}{right.text}"
                members = inside + [left, right]
                self.take(members)
                main = [a for a in inside if a.size >= 0.8 * max(x.size for x in inside)]
                base = sorted(a.base for a in main)[len(main) // 2]  # the row's baseline, not a limit's
                self.atoms.append(_node(text, members, base, max(a.size for a in inside), single=False))
                continue
            cells = [self._cells(r) for r in rows]
            if len({len(c) for c in cells}) != 1:
                raise Unsure("matrix rows of different lengths")
            word = "cases" if right is None else "matrix"
            text = word + "(" + "; ".join(", ".join(self.row(c) for c in row) for row in cells) + ")"
            if left.text not in "([{":  # determinant bars, norms: keep the printed delimiters
                text = left.text + text + (right.text if right else "")
            members = inside + [left] + ([right] if right else [])
            self.take(members)
            self.atoms.append(_node(text, members, left.cy + 0.25 * self.body, self.body, single=True))

    def _rows(self, atoms: list[Atom]) -> list[list[Atom]]:
        """Atoms in rows by their (full-size) baselines; smaller atoms join the nearest row."""
        big = [a for a in atoms if a.size >= 0.85 * max(x.size for x in atoms)]
        bases: list[float] = []
        for a in sorted(big, key=lambda a: a.base):
            if not bases or a.base - bases[-1] > 0.75 * self.body:
                bases.append(a.base)
        rows = [[] for _ in bases]
        for a in atoms:
            k = min(range(len(bases)), key=lambda i: abs(bases[i] - (a.base if a in big else a.cy)))
            rows[k].append(a)
        return rows

    def _cells(self, row: list[Atom]) -> list[list[Atom]]:
        row = sorted(row, key=lambda a: a.x0)
        cells, cur, right = [], [], None
        for a in row:
            if cur and a.x0 - right > 0.6 * self.body:
                cells.append(cur)
                cur = []
            cur.append(a)
            right = a.x1 if right is None or not cur[:-1] else max(right, a.x1)
        cells.append(cur)
        return cells

    # a row: base symbols on one baseline, with their scripts
    def row(self, atoms: list[Atom], sep: str = " ; ") -> str:
        atoms = [a for a in atoms if a.kind != "rule"]
        if not atoms:
            return ""
        # the size of ordinary symbols: the largest size that holds a real share of the ink (fonts mixed on one
        # baseline can differ by 10-20 %, a lone symbol may be larger; big brackets and operators are left out)
        plain = [a for a in atoms if a.kind not in ("big", "op")] or atoms
        by_size: dict[float, float] = {}
        for a in plain:
            by_size[round(a.size, 1)] = by_size.get(round(a.size, 1), 0) + (a.x1 - a.x0)
        total = sum(by_size.values()) or 1.0
        top = max(k for k in by_size if by_size[k] >= 0.1 * total)  # the largest size with a real share
        built = ("node", "op")
        full = [a for a in atoms if a.size >= 0.8 * top or a.kind in built]
        widths: dict[float, float] = {}
        for a in full:
            key = next((k for k in widths if abs(k - a.base) < 0.25 * top), a.base)
            widths[key] = widths.get(key, 0) + (a.x1 - a.x0)
        if ENABLED["rows"] and len(widths) > 1:
            keys = sorted(widths)
            if all(b - a > 1.1 * top for a, b in zip(keys, keys[1:])):
                rows = self._rows(atoms)
                if len(rows) > 1:
                    return sep.join(self.row(r) for r in rows)
        main = max(widths, key=widths.get)
        # the exact baseline comes from ordinary symbols; built pieces and big glyphs only estimate theirs
        exact = [a for a in full if abs(a.base - main) < 0.25 * top and a.kind not in ("big", "op", "node")] \
            or [a for a in full if abs(a.base - main) < 0.25 * top]
        main = sum(a.base * (a.x1 - a.x0) for a in exact) / max(1e-6, sum(a.x1 - a.x0 for a in exact))

        def on_main(a: Atom) -> bool:
            if a.kind == "big" or (a.kind == "op" and a.text[:1] in BIG_OPS):
                return a.y0 - 1 <= main <= a.y1 + 1  # a tall symbol: it spans the baseline
            if a.kind in built:
                return abs(a.base - main) < 0.25 * top
            return abs(a.base - main) < 0.1 * top and a.size >= 0.8 * top
        on_line = [a for a in atoms if on_main(a)]
        scripts = [a for a in atoms if a not in on_line]
        if scripts and not ENABLED["scripts"]:
            on_line, scripts = sorted(atoms, key=lambda a: a.x0), []
        for a in scripts:
            if a.size >= 0.8 * top and a.kind not in built:
                raise Unsure(f"full-size symbol off the baseline: {a.text!r} {a.kind} base {a.base:.1f} "
                             f"main {main:.1f} size {a.size:.1f}/{top:.1f}")
        on_line.sort(key=lambda a: a.x0)
        attach: dict[int, tuple[list[Atom], list[Atom]]] = {id(b): ([], []) for b in on_line}
        for s in scripts:
            before = [b for b in on_line if b.x0 < s.x0 - 0.1]
            if not before:
                raise Unsure("script before any symbol")
            owner = before[-1]
            raised = s.base < main - 0.08 * top
            lowered = s.base > main + 0.04 * top
            if not raised and not lowered:
                raise Unsure("small symbol on the baseline")
            if s.kind in built and s.size >= 0.88 * top:
                raise Unsure("built piece off the baseline")
            attach[id(owner)][0 if lowered else 1].append(s)
        parts, prev = [], None
        for b in on_line:
            subs, sups = attach[id(b)]
            text = b.text
            right = b.x1
            if subs:
                text += "_" + _group(self.row(subs), len(subs) == 1 and subs[0].single)
                right = max(right, max(a.x1 for a in subs))
            if sups:
                text += "^" + _group(self.row(sups), len(sups) == 1 and sups[0].single)
                right = max(right, max(a.x1 for a in sups))
            if prev is not None:
                gap = b.x0 - prev
                parts.append(" " if gap > 0.12 * top or (parts and _joins_badly(parts[-1], text)) else "")
            parts.append(text)
            prev = right
        return "".join(parts)


def _joins_badly(left: str, right: str) -> bool:
    """Two pieces that would read as one token when written together (two numbers, two words)."""
    return (left[-1:].isdigit() and right[:1].isdigit()) or (left[-1:].isalpha() and right[:1].isalpha()
                                                             and (len(left) > 1 or len(right) > 1))


@dataclass
class Formula:
    text: str  # linear text of the formula
    number: str = ""  # its equation number, if it carries one ("3", "12a")
    glyphs: str = ""  # the printed symbols it was built from, left to right

    def labelled(self) -> str:
        """The text with its number kept apart from the formula: 'E = mc^2, equation (3)'."""
        if not self.number:
            return self.text
        # sentence punctuation after the formula ("…(V)." or "…,") is not part of it and would hide the label
        return f"{self.text.rstrip(' ,.;:')}, equation ({self.number})"


def _symbols(text: str) -> dict:
    """The printed symbols of a text, counted (structure marks and words this module adds left out)."""
    t = unicodedata.normalize("NFD", re.sub(r"\b(matrix|cases|hat|bar|tilde|dot|ddot)\(", "(", text))
    for k, v in NEGATED.items():
        t = t.replace(unicodedata.normalize("NFD", v), k + "\u0338")
    return Counter(c for c in t if not c.isspace() and c not in "()^_/;,[]{}" and c not in ACCENTS)


def linear(page: pymupdf.Page, rect, drawings: list, body: float, areas: Optional[list] = None) -> Optional[Formula]:
    """The formula in ``rect`` on ``page`` as linear text, or None when its structure is not certain.
    ``drawings``: rectangles of the page's vector drawings (fraction bars, radical lines); ``areas``: the boxes of
    the text lines that make up the formula (other text inside ``rect`` is left out)."""
    try:
        if page.rotation:
            return None
        rect = pymupdf.Rect(rect)
        atoms = _glyphs(page, rect, areas)
        if not atoms:
            return None
        rules = _rules(drawings, rect)
        if areas:  # a line of a neighbouring formula (its radical bar) is not part of this one
            top_, bottom = min(a[1] for a in areas), max(a[3] for a in areas)
            rules = [r for r in rules if top_ - 1.5 <= r.base <= bottom + 1.5]
        _ink_extents(page, rect, atoms, rules)
        if areas:  # a tall symbol belongs to the formula when its ink lies in the formula's lines
            y0, y1 = min(a[1] for a in areas), max(a[3] for a in areas)
            atoms = [a for a in atoms if a.kind != "big" or y0 - 2 <= a.cy <= y1 + 2]
        _axis_bases(atoms, body)
        printed = "".join(a.text for a in sorted(atoms, key=lambda a: (round(a.base / 3), a.x0)))
        b = _Builder(atoms, rules, body)
        b.words()
        b.negations()
        number = ""
        if ENABLED["number"]:
            number = _number(b)
        if ENABLED["accents"]:
            b.accents()
        if ENABLED["radicals"]:
            b.radicals()
        if ENABLED["fractions"]:
            b.fractions()
        if ENABLED["limits"]:
            b.limits()
        if ENABLED["matrices"]:
            b.matrices()
        if b.rules and ENABLED["fractions"] and ENABLED["radicals"]:
            raise Unsure("a line that is not part of the formula's structure")
        text = b.row(b.atoms)
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"\(\s+", "(", re.sub(r"\s+\)", ")", text))
        if not text:
            return None
        if _symbols(text + number) != _symbols(printed):
            raise Unsure("symbols changed")  # guard: every printed symbol exactly once, nothing added
        return Formula(text, number, printed)
    except Unsure as e:
        LOG.append(str(e))
        del LOG[:-50]
        return None


def _number(b: _Builder) -> str:
    """Take a trailing equation number "(n)" off the formula (it is set well apart at the right)."""
    atoms = sorted(b.atoms, key=lambda a: a.x0)
    for k in range(len(atoms) - 1, max(-1, len(atoms) - 6), -1):
        tail = atoms[k:]
        text = "".join(a.text for a in tail)
        m = NUMBER.match(text)
        if m and k > 0:
            gap = tail[0].x0 - max(a.x1 for a in atoms[:k])
            same_line = max(a.base for a in tail) - min(a.base for a in tail) < 0.2 * b.body
            if gap > 1.5 * b.body and same_line:
                b.take(tail)
                return m.group(1)
    return ""
