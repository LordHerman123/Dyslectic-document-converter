"""A formula the reader types in LaTeX (to correct one the converter read wrongly), written as the formula text the
converter itself uses: the linear notation of formulas read from a PDF (see :mod:`extract.mathtree`), shown in
the maths font.

* ``x^{2}``, ``x_{i}``, ``\\sum_{i=1}^{n}`` become real superscripts and subscripts where Unicode has them (x²,
  xᵢ, ∑ᵢ₌₁ⁿ); otherwise ``x^(…)``, ``x_(…)`` as in the converter's own formula text;
* ``\\frac{a+b}{2c}`` becomes ``(a+b)/(2c)``, ``\\sqrt{x+1}`` ``√(x+1)``, matrices ``matrix(a, b; c, d)``, cases
  ``cases(…; …)``, accents ``x̂`` or ``hat(…)``;
* Greek letters, operators, relations, arrows and blackboard letters become their symbols.

Nothing typed is lost: a command this module does not know is kept as it was typed (``\\foo``) and reported, so
the reader sees it in the preview. Only commands that change spacing or size and nothing else (``\\,``,
``\\displaystyle``, ``\\left``) leave no trace.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from ..extract.mathtree import NEGATED, _balanced_outer

SUP = dict(zip("0123456789+-=()niTabcdefghjklmoprstuvwxyz",
               "⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾ⁿⁱᵀᵃᵇᶜᵈᵉᶠᵍʰʲᵏˡᵐᵒᵖʳˢᵗᵘᵛʷˣʸᶻ"))
SUB = dict(zip("0123456789+-=()aeoxhklmnpstijruv", "₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎ₐₑₒₓₕₖₗₘₙₚₛₜᵢⱼᵣᵤᵥ"))
SUP.update(zip("ABDEGHIJKLMNOPRUVW", "ᴬᴮᴰᴱᴳᴴᴵᴶᴷᴸᴹᴺᴼᴾᴿᵁⱽᵂ"))
SUP["\u2212"], SUB["\u2212"] = "⁻", "₋"

GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ϵ", "varepsilon": "ε", "zeta": "ζ",
         "eta": "η", "theta": "θ", "vartheta": "ϑ", "iota": "ι", "kappa": "κ", "lambda": "λ", "mu": "μ", "nu": "ν",
         "xi": "ξ", "pi": "π", "varpi": "ϖ", "rho": "ρ", "varrho": "ϱ", "sigma": "σ", "varsigma": "ς", "tau": "τ",
         "upsilon": "υ", "phi": "ϕ", "varphi": "φ", "chi": "χ", "psi": "ψ", "omega": "ω", "Gamma": "Γ",
         "Delta": "Δ", "Theta": "Θ", "Lambda": "Λ", "Xi": "Ξ", "Pi": "Π", "Sigma": "Σ", "Upsilon": "Υ", "Phi": "Φ",
         "Psi": "Ψ", "Omega": "Ω"}
SYMBOLS = {
    # operators
    "cdot": "·", "times": "×", "div": "÷", "pm": "±", "mp": "∓", "ast": "∗", "star": "⋆", "circ": "∘",
    "bullet": "•", "oplus": "⊕", "otimes": "⊗", "odot": "⊙", "cup": "∪", "cap": "∩", "setminus": "∖",
    "wedge": "∧", "land": "∧", "vee": "∨", "lor": "∨", "neg": "¬", "lnot": "¬",
    # relations
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠", "approx": "≈", "sim": "∼",
    "simeq": "≃", "cong": "≅", "equiv": "≡", "propto": "∝", "ll": "≪", "gg": "≫", "subset": "⊂",
    "subseteq": "⊆", "supset": "⊃", "supseteq": "⊇", "in": "∈", "notin": "∉", "ni": "∋", "perp": "⊥",
    "parallel": "∥", "mid": "|", "prec": "≺", "succ": "≻", "models": "⊨", "vdash": "⊢",
    # arrows
    "to": "→", "rightarrow": "→", "leftarrow": "←", "gets": "←", "Rightarrow": "⇒", "Leftarrow": "⇐",
    "Leftrightarrow": "⇔", "iff": "⇔", "leftrightarrow": "↔", "mapsto": "↦", "implies": "⟹", "uparrow": "↑",
    "downarrow": "↓", "longrightarrow": "⟶", "longleftarrow": "⟵",
    # big operators
    "sum": "∑", "prod": "∏", "coprod": "∐", "int": "∫", "iint": "∬", "iiint": "∭", "oint": "∮",
    "bigcup": "⋃", "bigcap": "⋂", "bigoplus": "⨁", "bigotimes": "⨂",
    # others
    "infty": "∞", "partial": "∂", "nabla": "∇", "forall": "∀", "exists": "∃", "nexists": "∄", "emptyset": "∅",
    "varnothing": "∅", "ldots": "…", "dots": "…", "cdots": "⋯", "vdots": "⋮", "ddots": "⋱", "prime": "′",
    "angle": "∠", "degree": "°", "hbar": "ℏ", "ell": "ℓ", "Re": "ℜ", "Im": "ℑ", "aleph": "ℵ", "langle": "⟨",
    "rangle": "⟩", "lfloor": "⌊", "rfloor": "⌋", "lceil": "⌈", "rceil": "⌉", "lVert": "‖", "rVert": "‖",
    "Vert": "‖", "lvert": "|", "rvert": "|", "vert": "|", "top": "⊤", "bot": "⊥", "dagger": "†",
    "therefore": "∴", "because": "∵", "backslash": "\\", "square": "□", "triangle": "△", "checkmark": "✓",
}
FUNCTIONS = {"sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan", "sinh", "cosh", "tanh", "log",
             "ln", "lg", "exp", "lim", "liminf", "limsup", "max", "min", "sup", "inf", "det", "dim", "ker", "deg",
             "gcd", "arg", "Pr", "hom"}
ESCAPED = {"{": "{", "}": "}", "%": "%", "&": "&", "_": "_", "#": "#", "$": "$", "|": "‖"}
SPACES = {",": " ", ";": " ", ":": " ", ">": " ", "!": "", " ": " ", "quad": " ", "qquad": " ", "thinspace": " "}
LAYOUT_ONLY = {"displaystyle", "textstyle", "scriptstyle", "scriptscriptstyle", "limits", "nolimits", "left",
               "right", "big", "Big", "bigg", "Bigg", "bigl", "bigr", "Bigl", "Bigr", "biggl", "biggr", "middle",
               "nonumber", "notag"}
STYLE_ONLY = {"mathrm", "mathit", "mathbf", "mathsf", "mathtt", "boldsymbol", "bm", "textbf", "textit",
              "textrm", "operatorname", "mbox", "text", "textnormal", "mathnormal"}
ACCENTS = {"hat": ("\u0302", "hat"), "widehat": ("\u0302", "hat"), "bar": ("\u0304", "bar"),
           "overline": ("\u0305", "bar"), "tilde": ("\u0303", "tilde"), "widetilde": ("\u0303", "tilde"),
           "dot": ("\u0307", "dot"), "ddot": ("\u0308", "ddot"), "vec": ("\u20d7", "vec")}
DOUBLE_STRUCK = {"C": "ℂ", "H": "ℍ", "N": "ℕ", "P": "ℙ", "Q": "ℚ", "R": "ℝ", "Z": "ℤ"}
SCRIPT = {"B": "ℬ", "E": "ℰ", "F": "ℱ", "H": "ℋ", "I": "ℐ", "L": "ℒ", "M": "ℳ", "R": "ℛ"}
MATRICES = {"matrix": ("", ""), "pmatrix": ("", ""), "bmatrix": ("[", "]"), "Bmatrix": ("{", "}"),
            "vmatrix": ("|", "|"), "Vmatrix": ("‖", "‖"), "smallmatrix": ("", ""), "array": ("", "")}
ROWS = {"align", "align*", "aligned", "gather", "gather*", "gathered", "split", "eqnarray", "eqnarray*",
        "multline", "multline*", "equation", "equation*"}

TOKEN = re.compile(r"\\[A-Za-z]+\*?|\\.|[{}^_&]|\s+|.", re.S)


@dataclass
class Result:
    """The formula text, the commands that were not known (kept as typed), and whether the braces match."""
    text: str
    unknown: list[str] = field(default_factory=list)
    balanced: bool = True


def _single(t: str) -> bool:
    """Whether a piece is written as one token (needs no brackets as a script, numerator or root)."""
    t = t.strip()
    return bool(re.fullmatch(r"[^\W_]|\d+(?:\.\d+)?|[^\w\s()]", t)) or t in FUNCTIONS \
        or bool(re.fullmatch(r"\(.*\)", t) and _balanced_outer(t))


def _group(t: str) -> str:
    t = t.strip()
    return t if _single(t) else f"({t})"


def _script(t: str, table: dict, mark: str) -> str:
    """A superscript or subscript: Unicode script characters when there is one for every character, else the
    converter's ``^(…)`` / ``_(…)``."""
    t = t.strip()
    if t and all(ch in table for ch in t.replace(" ", "")):
        return "".join(table[ch] for ch in t if ch != " ")
    return mark + _group(t)


class _Parser:
    def __init__(self, src: str):
        self.toks = [t for t in TOKEN.findall(src)]
        self.i = 0
        self.unknown: list[str] = []

    def peek(self) -> str:
        return self.toks[self.i] if self.i < len(self.toks) else ""

    def next(self) -> str:
        t = self.peek()
        self.i += 1
        return t

    def skip_space(self) -> None:
        while self.peek().isspace() and self.peek():
            self.i += 1

    def sequence(self, stop: tuple = ("}",)) -> str:
        """Pieces up to (not including) a stop token, with their scripts."""
        out = ""
        while self.i < len(self.toks):
            t = self.peek()
            if t in stop or (t == "\\end" and "\\end" in stop):
                break
            if t.isspace():
                self.i += 1
                out += " "
                continue
            base = self.atom()
            out += base + self.scripts()
        return out

    def scripts(self) -> str:
        """The superscript and subscript after a piece (either order), and primes."""
        sub = sup = None
        while True:
            if self.peek().isspace() and self._script_follows():
                self.skip_space()
            t = self.peek()
            if t == "^" and sup is None:
                self.i += 1
                sup = self.argument()
            elif t == "_" and sub is None:
                self.i += 1
                sub = self.argument()
            elif t == "'":
                self.i += 1
                sup = (sup or "") + "′"
            else:
                break
        out = ""
        if sub is not None:
            out += _script(sub, SUB, "_")
        if sup is not None:
            out += sup if set(sup) <= {"′"} else _script(sup, SUP, "^")
        return out

    def _script_follows(self) -> bool:
        j = self.i
        while j < len(self.toks) and self.toks[j].isspace():
            j += 1
        return j < len(self.toks) and self.toks[j] in ("^", "_")

    def argument(self) -> str:
        """One argument: a {group} or a single token."""
        self.skip_space()
        if self.peek() == "{":
            self.i += 1
            inner = self.sequence(("}",))
            self.next()  # the closing brace
            return inner.strip()
        return self.atom()

    def optional(self) -> str:
        """An optional [argument], or ""."""
        self.skip_space()
        if self.peek() != "[":
            return ""
        self.i += 1
        out = ""
        while self.peek() and self.peek() != "]":
            out += self.atom()
        self.next()
        return out.strip()

    def atom(self) -> str:
        t = self.next()
        if t == "{":
            inner = self.sequence(("}",))
            self.next()
            return inner
        if t in ("&",):
            return ", "
        if t == "\\\\":
            return "; "
        if not t.startswith("\\"):
            return "−" if t == "-" else t
        name = t[1:]
        if len(name) == 1 and not name.isalpha():
            if name in ESCAPED:
                return ESCAPED[name]
            if name in SPACES:
                return SPACES[name]
            return name
        if name in SPACES:
            return SPACES[name]
        if name in GREEK:
            return GREEK[name]
        if name in SYMBOLS:
            return SYMBOLS[name]
        if name in FUNCTIONS:  # "\\sin\\theta" is "sin θ"; "\\lim_{x}", "\\log(x)" stay together
            nxt = self.peek()
            joined = nxt[:1].isalnum() or (nxt.startswith("\\") and nxt[1:] in GREEK)
            return name + " " if joined else name
        if name in LAYOUT_ONLY:
            if name in ("left", "right", "middle") or name.startswith(("big", "Big")):
                d = self.next()
                return "" if d == "." else self.atom_of(d)
            return ""
        if name in ("frac", "dfrac", "tfrac", "cfrac"):
            a, b = self.argument(), self.argument()
            return f"{_group(a)}/{_group(b)}"
        if name == "binom":
            a, b = self.argument(), self.argument()
            return f"C({a.strip()}, {b.strip()})"
        if name == "sqrt":
            n, x = self.optional(), self.argument()
            root = {"": "√", "2": "√", "3": "∛", "4": "∜"}.get(n.strip())
            if root is None:
                root = _script(n, SUP, "^") + "√"
            return root + _group(x)
        if name in ACCENTS:
            x = self.argument().strip()
            mark, word = ACCENTS[name]
            return x + mark if len(x) == 1 else f"{word}({x})"
        if name in STYLE_ONLY:
            return self.text_argument() if name.startswith(("text", "mbox", "operatorname")) else self.argument()
        if name == "mathbb":
            x = self.argument().strip()
            return "".join(DOUBLE_STRUCK.get(ch, chr(0x1D538 + ord(ch) - 65) if "A" <= ch <= "Z" else ch) for ch in x)
        if name == "mathcal" or name == "mathscr":
            x = self.argument().strip()
            return "".join(SCRIPT.get(ch, chr(0x1D49C + ord(ch) - 65) if "A" <= ch <= "Z" else ch) for ch in x)
        if name == "not":
            self.skip_space()
            nxt = self.atom()
            return NEGATED.get(nxt, nxt + "\u0338")
        if name == "begin":
            return self.environment()
        self.unknown.append(t)
        out = t  # kept as typed (with its {arguments}), so nothing is lost
        while self.peek() == "{":
            self.i += 1
            out += "{" + self.sequence(("}",)) + "}"
            self.next()
        return out

    def atom_of(self, tok: str) -> str:
        """A delimiter after \\left, \\right or \\big: written out like any token."""
        self.i -= 1
        return self.atom()

    def text_argument(self) -> str:
        """\\text{...}: the words exactly as typed."""
        self.skip_space()
        if self.peek() != "{":
            return self.atom()
        self.i += 1
        depth, out = 1, ""
        while self.i < len(self.toks):
            t = self.next()
            depth += (t == "{") - (t == "}")
            if depth == 0:
                break
            out += ESCAPED.get(t[1:], t) if t.startswith("\\") and len(t) == 2 else t
        return out

    def environment(self) -> str:
        name = self.argument().strip()
        if name == "array":
            self.argument()  # the column layout ({cc}, {l|r})
        rows: list[list[str]] = [[]]
        cell = ""
        while self.i < len(self.toks):
            t = self.peek()
            if t == "\\end":
                self.i += 1
                self.argument()
                break
            if t == "&":
                self.i += 1
                rows[-1].append(cell.strip())
                cell = ""
            elif t == "\\\\":
                self.i += 1
                self.optional()
                rows[-1].append(cell.strip())
                rows.append([])
                cell = ""
            else:
                cell += self.sequence(("&", "\\\\", "\\end"))
        rows[-1].append(cell.strip())
        rows = [r for r in rows if any(c for c in r)]
        if name in MATRICES:
            left, right = MATRICES[name]
            return f"{left}matrix(" + "; ".join(", ".join(r) for r in rows) + f"){right}"
        if name in ("cases", "dcases"):
            return "cases(" + "; ".join(", ".join(r) for r in rows) + ")"
        if name in ROWS:
            return "; ".join(" ".join(c for c in r) for r in rows)
        self.unknown.append(f"\\begin{{{name}}}")
        return "; ".join(", ".join(r) for r in rows)


def to_formula_text(src: str) -> Result:
    """LaTeX (with or without $…$, \\(…\\) or \\[…\\] around it) as the converter's formula text."""
    s = src.strip()
    for a, b in (("$$", "$$"), ("$", "$"), ("\\[", "\\]"), ("\\(", "\\)")):
        if s.startswith(a) and s.endswith(b) and len(s) >= len(a) + len(b):
            s = s[len(a):len(s) - len(b)]
            break
    p = _Parser(s)
    depth, balanced = 0, True
    for t in p.toks:
        depth += (t == "{") - (t == "}")
        balanced = balanced and depth >= 0
    balanced = balanced and depth == 0
    out = ""
    while p.i < len(p.toks):
        out += p.sequence(("}",))
        if p.peek() == "}":  # a stray closing brace: kept, so nothing typed is lost
            out += p.next()
    text = unicodedata.normalize("NFC", re.sub(r"\s+", " ", out).strip())  # ȳ rather than y + a combining bar
    text = re.sub(r"\s+([,;)\]′])", r"\1", text)
    return Result(text, p.unknown, balanced)
