"""Formulas said in words, for reading aloud: ``∑_(i=1)^n x_i^2`` becomes "the sum from i equals 1 to n of x sub i
squared" (or the same in Dutch, German, French, Spanish or Italian).

The input is the linear text the converter writes for a formula (see :mod:`extract.mathtree`): scripts with ``^`` and
``_``, fractions with ``/``, ``√``, accents as ``hat(x)``, ``matrix(a; b)``, and a trailing ``, equation (3)``.
Brackets that only group a script, a numerator or a denominator are not said; printed brackets are, except after a
function or a letter, where ``f(x)`` is "f of x". Every symbol is said: nothing is left out or made up.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Optional

# ---------------------------------------------------------------------------------------------------- words

GREEK = "αβγδεζηθικλμνξοπρστυφχψω"
GREEK_NAMES = {
    "en": "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau upsilon "
          "phi chi psi omega",
    "nl": "alfa bèta gamma delta epsilon zèta èta thèta jota kappa lambda mu nu ksi omikron pi rho sigma tau upsilon "
          "phi chi psi omega",
    "de": "Alpha Beta Gamma Delta Epsilon Zeta Eta Theta Iota Kappa Lambda My Ny Xi Omikron Pi Rho Sigma Tau Ypsilon "
          "Phi Chi Psi Omega",
    "fr": "alpha bêta gamma delta epsilon zêta êta thêta iota kappa lambda mu nu xi omicron pi rhô sigma tau upsilon "
          "phi khi psi oméga",
    "es": "alfa beta gamma delta épsilon zeta eta theta iota kappa lambda mu nu xi ómicron pi rho sigma tau ípsilon "
          "fi ji psi omega",
    "it": "alfa beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau ipsilon "
          "fi chi psi omega",
}
GREEK_VARIANTS = {"ϵ": "ε", "ϑ": "θ", "ϕ": "φ", "ϱ": "ρ", "ς": "σ", "ϖ": "π", "µ": "μ"}

# "{x}" is where the spoken part goes
WORDS: dict[str, dict[str, str]] = {
    "en": {
        "placeholder": "dot", "capital": "capital {x}", "sub": "sub", "power": "to the power", "squared": "squared", "cubed": "cubed",
        "over": "over", "frac": "the fraction", "frac_end": "end fraction", "sqrt": "the square root of",
        "root": "the root with index {x} of", "root_end": "end root", "of": "of", "sum": "the sum",
        "prod": "the product", "int": "the integral", "iint": "the double integral", "oint": "the contour integral",
        "from": "from", "to": "to", "lim": "the limit as {x} of", "max": "the maximum over {x} of",
        "min": "the minimum over {x} of", "argmax": "the arg max over {x} of", "argmin": "the arg min over {x} of",
        "sup": "the supremum over {x} of", "inf": "the infimum over {x} of", "open": "open bracket",
        "close": "close bracket", "abs": "the absolute value of", "abs_end": "end absolute value",
        "norm": "the norm of", "norm_end": "end norm", "given": "given", "hat": "{x} hat", "bar": "{x} bar",
        "tilde": "{x} tilde", "dot": "{x} dot", "ddot": "{x} double dot", "vec": "vector {x}",
        "matrix": "the matrix", "cases": "cases", "row": "row", "end_matrix": "end matrix", "equation": "equation",
        "transpose": "transpose", "prime": "prime", "dprime": "double prime", "star": "star",
        "=": "equals", "≠": "is not equal to", "<": "is less than", ">": "is greater than",
        "≤": "is less than or equal to", "≥": "is greater than or equal to", "≈": "is approximately equal to",
        "≡": "is identical to", "∝": "is proportional to", "∼": "tilde", "≃": "is asymptotically equal to",
        "≪": "is much less than", "≫": "is much greater than", "∈": "is in", "∉": "is not in", "⊂": "is a subset of",
        "⊆": "is a subset of or equal to", "∪": "union", "∩": "intersection", "→": "goes to", "←": "comes from",
        "↦": "maps to", "⇒": "implies", "⇔": "if and only if", "∀": "for all", "∃": "there exists", "¬": "not",
        "∧": "and", "∨": "or", "+": "plus", "−": "minus", "-": "minus", "±": "plus or minus", "∓": "minus or plus",
        "·": "times", "×": "times", "⋅": "times", "∗": "star", "*": "star", "⊙": "element-wise times",
        "⊗": "tensor product", "⊕": "direct sum", "∘": "composed with", "/": "divided by", "∂": "partial",
        "∇": "nabla", "∞": "infinity", "∅": "the empty set", "…": "and so on", "⋯": "and so on", "!": "factorial",
        "%": "percent", "°": "degrees", "∥": "parallel", "|": "given", ":": "colon", "∫": "the integral",
        "ℝ": "the real numbers", "ℕ": "the natural numbers", "ℤ": "the integers", "ℂ": "the complex numbers",
        "log": "log", "ln": "natural log", "exp": "exp", "sin": "sine", "cos": "cosine", "tan": "tangent",
        "det": "determinant", "tr": "trace", "Pr": "probability",
    },
    "nl": {
        "placeholder": "punt", "capital": "hoofdletter {x}", "sub": "index", "power": "tot de macht", "squared": "kwadraat",
        "cubed": "tot de derde", "over": "gedeeld door", "frac": "de breuk", "frac_end": "einde breuk",
        "sqrt": "de wortel van", "root": "de wortel met index {x} van", "root_end": "einde wortel", "of": "van",
        "sum": "de som", "prod": "het product", "int": "de integraal", "iint": "de dubbele integraal",
        "oint": "de kringintegraal", "from": "van", "to": "tot", "lim": "de limiet voor {x} van",
        "max": "het maximum over {x} van", "min": "het minimum over {x} van", "argmax": "de arg max over {x} van",
        "argmin": "de arg min over {x} van", "sup": "het supremum over {x} van", "inf": "het infimum over {x} van",
        "open": "haakje openen", "close": "haakje sluiten", "abs": "de absolute waarde van",
        "abs_end": "einde absolute waarde", "norm": "de norm van", "norm_end": "einde norm", "given": "gegeven",
        "hat": "{x} dakje", "bar": "{x} streep", "tilde": "{x} tilde", "dot": "{x} punt", "ddot": "{x} dubbel punt",
        "vec": "vector {x}", "matrix": "de matrix", "cases": "gevallen", "row": "rij", "end_matrix": "einde matrix",
        "equation": "vergelijking", "transpose": "getransponeerd", "prime": "accent", "dprime": "dubbel accent",
        "star": "ster", "=": "is gelijk aan", "≠": "is niet gelijk aan", "<": "is kleiner dan",
        ">": "is groter dan", "≤": "is kleiner dan of gelijk aan", "≥": "is groter dan of gelijk aan",
        "≈": "is ongeveer gelijk aan", "≡": "is identiek aan", "∝": "is evenredig met", "∼": "tilde",
        "≃": "is asymptotisch gelijk aan", "≪": "is veel kleiner dan", "≫": "is veel groter dan",
        "∈": "is element van", "∉": "is geen element van", "⊂": "is een deelverzameling van",
        "⊆": "is een deelverzameling van of gelijk aan", "∪": "vereniging", "∩": "doorsnede", "→": "gaat naar",
        "←": "komt van", "↦": "wordt afgebeeld op", "⇒": "impliceert", "⇔": "dan en slechts dan als",
        "∀": "voor alle", "∃": "er bestaat", "¬": "niet", "∧": "en", "∨": "of", "+": "plus", "−": "min", "-": "min",
        "±": "plus of min", "∓": "min of plus", "·": "maal", "×": "maal", "⋅": "maal", "∗": "ster", "*": "ster",
        "⊙": "elementsgewijs maal", "⊗": "tensorproduct", "⊕": "directe som", "∘": "na", "/": "gedeeld door",
        "∂": "partieel", "∇": "nabla", "∞": "oneindig", "∅": "de lege verzameling", "…": "enzovoort",
        "⋯": "enzovoort", "!": "faculteit", "%": "procent", "°": "graden", "∥": "parallel", "|": "gegeven",
        ":": "dubbele punt", "∫": "de integraal", "ℝ": "de reële getallen", "ℕ": "de natuurlijke getallen",
        "ℤ": "de gehele getallen", "ℂ": "de complexe getallen", "log": "log", "ln": "natuurlijke logaritme",
        "exp": "exp", "sin": "sinus", "cos": "cosinus", "tan": "tangens", "det": "determinant", "tr": "spoor",
        "Pr": "kans",
    },
    "de": {
        "placeholder": "Punkt", "capital": "großes {x}", "sub": "Index", "power": "hoch", "squared": "Quadrat", "cubed": "hoch drei",
        "over": "durch", "frac": "Bruch", "frac_end": "Ende des Bruchs", "sqrt": "Wurzel aus",
        "root": "{x}-te Wurzel aus", "root_end": "Ende der Wurzel", "of": "von", "sum": "Summe",
        "prod": "Produkt", "int": "Integral", "iint": "Doppelintegral", "oint": "Kurvenintegral",
        "from": "von", "to": "bis", "lim": "Limes für {x} von", "max": "Maximum über {x} von",
        "min": "Minimum über {x} von", "argmax": "Arg-Max über {x} von", "argmin": "Arg-Min über {x} von",
        "sup": "Supremum über {x} von", "inf": "Infimum über {x} von", "open": "Klammer auf",
        "close": "Klammer zu", "abs": "Betrag von", "abs_end": "Ende des Betrags", "norm": "Norm von",
        "norm_end": "Ende der Norm", "given": "gegeben", "hat": "{x} Dach", "bar": "{x} quer",
        "tilde": "{x} Tilde", "dot": "{x} Punkt", "ddot": "{x} zwei Punkte", "vec": "Vektor {x}",
        "matrix": "Matrix", "cases": "Fallunterscheidung", "row": "Zeile", "end_matrix": "Ende der Matrix",
        "equation": "Gleichung", "transpose": "transponiert", "prime": "Strich", "dprime": "zwei Strich",
        "star": "Stern", "=": "gleich", "≠": "ungleich", "<": "kleiner als", ">": "größer als",
        "≤": "kleiner oder gleich", "≥": "größer oder gleich", "≈": "ungefähr gleich", "≡": "identisch mit",
        "∝": "proportional zu", "∼": "Tilde", "≃": "asymptotisch gleich", "≪": "sehr viel kleiner als",
        "≫": "sehr viel größer als", "∈": "Element von", "∉": "nicht Element von", "⊂": "Teilmenge von",
        "⊆": "Teilmenge oder gleich", "∪": "vereinigt mit", "∩": "geschnitten mit", "→": "gegen",
        "←": "kommt von", "↦": "wird abgebildet auf", "⇒": "daraus folgt", "⇔": "genau dann, wenn",
        "∀": "für alle", "∃": "es gibt", "¬": "nicht", "∧": "und", "∨": "oder", "+": "plus", "−": "minus",
        "-": "minus", "±": "plus minus", "∓": "minus plus", "·": "mal", "×": "mal", "⋅": "mal", "∗": "Stern",
        "*": "Stern", "⊙": "elementweise mal", "⊗": "Tensorprodukt", "⊕": "direkte Summe", "∘": "verkettet mit",
        "/": "geteilt durch", "∂": "partiell", "∇": "Nabla", "∞": "unendlich", "∅": "leere Menge",
        "…": "und so weiter", "⋯": "und so weiter", "!": "Fakultät", "%": "Prozent", "°": "Grad",
        "∥": "parallel", "|": "gegeben", ":": "Doppelpunkt", "∫": "Integral", "ℝ": "R", "ℕ": "N", "ℤ": "Z", "ℂ": "C", "log": "log",
        "ln": "natürlicher Logarithmus", "exp": "exp", "sin": "Sinus", "cos": "Kosinus", "tan": "Tangens",
        "det": "Determinante", "tr": "Spur", "Pr": "Wahrscheinlichkeit",
    },
    "fr": {
        "placeholder": "point", "capital": "{x} majuscule", "sub": "indice", "power": "puissance", "squared": "au carré",
        "cubed": "au cube", "over": "sur", "frac": "la fraction", "frac_end": "fin de la fraction",
        "sqrt": "la racine carrée de", "root": "la racine {x}-ième de", "root_end": "fin de la racine", "of": "de",
        "sum": "la somme", "prod": "le produit", "int": "l'intégrale", "iint": "l'intégrale double",
        "oint": "l'intégrale curviligne", "from": "de", "to": "à", "lim": "la limite quand {x} de",
        "max": "le maximum sur {x} de", "min": "le minimum sur {x} de", "argmax": "l'arg max sur {x} de",
        "argmin": "l'arg min sur {x} de", "sup": "le supremum sur {x} de", "inf": "l'infimum sur {x} de",
        "open": "ouvrir la parenthèse", "close": "fermer la parenthèse", "abs": "la valeur absolue de",
        "abs_end": "fin de la valeur absolue", "norm": "la norme de", "norm_end": "fin de la norme",
        "given": "sachant", "hat": "{x} chapeau", "bar": "{x} barre", "tilde": "{x} tilde", "dot": "{x} point",
        "ddot": "{x} deux points", "vec": "vecteur {x}", "matrix": "la matrice", "cases": "les cas",
        "row": "ligne", "end_matrix": "fin de la matrice", "equation": "équation", "transpose": "transposée",
        "prime": "prime", "dprime": "seconde", "star": "étoile", "=": "égale", "≠": "est différent de",
        "<": "est inférieur à", ">": "est supérieur à", "≤": "est inférieur ou égal à",
        "≥": "est supérieur ou égal à", "≈": "est environ égal à", "≡": "est identique à",
        "∝": "est proportionnel à", "∼": "tilde", "≃": "est asymptotiquement égal à",
        "≪": "est très inférieur à", "≫": "est très supérieur à", "∈": "appartient à", "∉": "n'appartient pas à",
        "⊂": "est inclus dans", "⊆": "est inclus ou égal à", "∪": "union", "∩": "inter", "→": "tend vers",
        "←": "vient de", "↦": "a pour image", "⇒": "implique", "⇔": "si et seulement si", "∀": "pour tout",
        "∃": "il existe", "¬": "non", "∧": "et", "∨": "ou", "+": "plus", "−": "moins", "-": "moins",
        "±": "plus ou moins", "∓": "moins ou plus", "·": "fois", "×": "fois", "⋅": "fois", "∗": "étoile",
        "*": "étoile", "⊙": "fois terme à terme", "⊗": "produit tensoriel", "⊕": "somme directe", "∘": "rond",
        "/": "divisé par", "∂": "d rond", "∇": "nabla", "∞": "l'infini", "∅": "l'ensemble vide",
        "…": "et ainsi de suite", "⋯": "et ainsi de suite", "!": "factorielle", "%": "pour cent",
        "°": "degrés", "∥": "parallèle à", "|": "sachant", ":": "deux points", "∫": "l'intégrale",
        "ℝ": "l'ensemble des réels", "ℕ": "l'ensemble des entiers naturels", "ℤ": "l'ensemble des entiers",
        "ℂ": "l'ensemble des complexes", "log": "log", "ln": "logarithme népérien", "exp": "exp", "sin": "sinus",
        "cos": "cosinus", "tan": "tangente", "det": "déterminant", "tr": "trace", "Pr": "probabilité",
    },
    "es": {
        "placeholder": "punto", "capital": "{x} mayúscula", "sub": "subíndice", "power": "elevado a", "squared": "al cuadrado",
        "cubed": "al cubo", "over": "entre", "frac": "la fracción", "frac_end": "fin de la fracción",
        "sqrt": "la raíz cuadrada de", "root": "la raíz {x}-ésima de", "root_end": "fin de la raíz", "of": "de",
        "sum": "la suma", "prod": "el producto", "int": "la integral", "iint": "la integral doble",
        "oint": "la integral de contorno", "from": "desde", "to": "hasta", "lim": "el límite cuando {x} de",
        "max": "el máximo sobre {x} de", "min": "el mínimo sobre {x} de", "argmax": "el arg max sobre {x} de",
        "argmin": "el arg min sobre {x} de", "sup": "el supremo sobre {x} de", "inf": "el ínfimo sobre {x} de",
        "open": "abre paréntesis", "close": "cierra paréntesis", "abs": "el valor absoluto de",
        "abs_end": "fin del valor absoluto", "norm": "la norma de", "norm_end": "fin de la norma",
        "given": "dado", "hat": "{x} sombrero", "bar": "{x} barra", "tilde": "{x} tilde", "dot": "{x} punto",
        "ddot": "{x} dos puntos", "vec": "vector {x}", "matrix": "la matriz", "cases": "casos", "row": "fila",
        "end_matrix": "fin de la matriz", "equation": "ecuación", "transpose": "traspuesta", "prime": "prima",
        "dprime": "segunda", "star": "estrella", "=": "igual a", "≠": "distinto de", "<": "menor que",
        ">": "mayor que", "≤": "menor o igual que", "≥": "mayor o igual que", "≈": "aproximadamente igual a",
        "≡": "idéntico a", "∝": "proporcional a", "∼": "tilde", "≃": "asintóticamente igual a",
        "≪": "mucho menor que", "≫": "mucho mayor que", "∈": "pertenece a", "∉": "no pertenece a",
        "⊂": "es subconjunto de", "⊆": "es subconjunto o igual a", "∪": "unión", "∩": "intersección",
        "→": "tiende a", "←": "viene de", "↦": "se aplica en", "⇒": "implica", "⇔": "si y solo si",
        "∀": "para todo", "∃": "existe", "¬": "no", "∧": "y", "∨": "o", "+": "más", "−": "menos", "-": "menos",
        "±": "más o menos", "∓": "menos o más", "·": "por", "×": "por", "⋅": "por", "∗": "estrella",
        "*": "estrella", "⊙": "por elemento a elemento", "⊗": "producto tensorial", "⊕": "suma directa",
        "∘": "compuesto con", "/": "dividido entre", "∂": "parcial", "∇": "nabla", "∞": "infinito",
        "∅": "el conjunto vacío", "…": "etcétera", "⋯": "etcétera", "!": "factorial", "%": "por ciento",
        "°": "grados", "∥": "paralelo a", "|": "dado", ":": "dos puntos", "∫": "la integral",
        "ℝ": "los números reales", "ℕ": "los números naturales", "ℤ": "los números enteros",
        "ℂ": "los números complejos", "log": "log", "ln": "logaritmo natural", "exp": "exp", "sin": "seno",
        "cos": "coseno", "tan": "tangente", "det": "determinante", "tr": "traza", "Pr": "probabilidad",
    },
    "it": {
        "placeholder": "punto", "capital": "{x} maiuscola", "sub": "pedice", "power": "elevato a", "squared": "al quadrato",
        "cubed": "al cubo", "over": "fratto", "frac": "la frazione", "frac_end": "fine della frazione",
        "sqrt": "la radice quadrata di", "root": "la radice {x}-esima di", "root_end": "fine della radice",
        "of": "di", "sum": "la somma", "prod": "il prodotto", "int": "l'integrale", "iint": "l'integrale doppio",
        "oint": "l'integrale di linea", "from": "da", "to": "a", "lim": "il limite per {x} di",
        "max": "il massimo su {x} di", "min": "il minimo su {x} di", "argmax": "l'arg max su {x} di",
        "argmin": "l'arg min su {x} di", "sup": "l'estremo superiore su {x} di",
        "inf": "l'estremo inferiore su {x} di", "open": "aperta parentesi", "close": "chiusa parentesi",
        "abs": "il valore assoluto di", "abs_end": "fine del valore assoluto", "norm": "la norma di",
        "norm_end": "fine della norma", "given": "dato", "hat": "{x} cappello", "bar": "{x} barra",
        "tilde": "{x} tilde", "dot": "{x} punto", "ddot": "{x} due punti", "vec": "vettore {x}",
        "matrix": "la matrice", "cases": "casi", "row": "riga", "end_matrix": "fine della matrice",
        "equation": "equazione", "transpose": "trasposta", "prime": "primo", "dprime": "secondo",
        "star": "stella", "=": "uguale a", "≠": "diverso da", "<": "minore di", ">": "maggiore di",
        "≤": "minore o uguale a", "≥": "maggiore o uguale a", "≈": "circa uguale a", "≡": "identico a",
        "∝": "proporzionale a", "∼": "tilde", "≃": "asintoticamente uguale a", "≪": "molto minore di",
        "≫": "molto maggiore di", "∈": "appartiene a", "∉": "non appartiene a", "⊂": "è sottoinsieme di",
        "⊆": "è sottoinsieme o uguale a", "∪": "unione", "∩": "intersezione", "→": "tende a",
        "←": "viene da", "↦": "va in", "⇒": "implica", "⇔": "se e solo se", "∀": "per ogni", "∃": "esiste",
        "¬": "non", "∧": "e", "∨": "o", "+": "più", "−": "meno", "-": "meno", "±": "più o meno",
        "∓": "meno o più", "·": "per", "×": "per", "⋅": "per", "∗": "stella", "*": "stella",
        "⊙": "per elemento per elemento", "⊗": "prodotto tensoriale", "⊕": "somma diretta", "∘": "composto",
        "/": "diviso", "∂": "parziale", "∇": "nabla", "∞": "infinito", "∅": "l'insieme vuoto",
        "…": "eccetera", "⋯": "eccetera", "!": "fattoriale", "%": "per cento", "°": "gradi",
        "∥": "parallelo a", "|": "dato", ":": "due punti", "∫": "l'integrale", "ℝ": "l'insieme dei numeri reali",
        "ℕ": "l'insieme dei numeri naturali", "ℤ": "l'insieme dei numeri interi",
        "ℂ": "l'insieme dei numeri complessi", "log": "log",
        "ln": "logaritmo naturale", "exp": "exp", "sin": "seno", "cos": "coseno", "tan": "tangente",
        "det": "determinante", "tr": "traccia", "Pr": "probabilità",
    },
}

# the words that describe the structure (looked up as "@sub", ...), apart from the symbols and function names
STRUCTURE = ("capital", "sub", "power", "squared", "cubed", "over", "frac", "frac_end", "sqrt", "root", "root_end",
             "of", "sum", "prod", "int", "iint", "oint", "from", "to", "lim", "max", "min", "argmax", "argmin", "sup",
             "inf", "open", "close", "abs", "abs_end", "norm", "norm_end", "given", "hat", "bar", "tilde", "dot",
             "ddot", "vec", "matrix", "cases", "row", "end_matrix", "equation", "transpose", "prime", "dprime", "star",
             "super", "placeholder")
SUPER = {"en": "superscript", "nl": "superscript", "de": "hochgestellt", "fr": "exposant", "es": "superíndice",
         "it": "apice"}
for _lang, _words in WORDS.items():
    _words["super"] = SUPER[_lang]
    for _k in STRUCTURE:
        _words["@" + _k] = _words.pop(_k)

BIG = {"∑": "sum", "∏": "prod", "∫": "int", "∬": "iint", "∮": "oint"}
LIMITS = {"lim", "max", "min", "argmax", "argmin", "sup", "inf"}
ACCENT_WORDS = {"hat", "bar", "tilde", "dot", "ddot", "vec"}
SHORT_WORDS = {"if", "or", "is", "in", "on", "at", "to", "of", "as", "by", "ln", "tr", "Pr", "lg"}
FUNCTIONS = {"log", "ln", "exp", "sin", "cos", "tan", "tanh", "sinh", "cosh", "det", "tr", "Pr", "softmax", "sigmoid",
             "relu", "diag", "rank", "max", "min", "sup", "inf", "lim", "argmax", "argmin", "Cov", "Var", "E"}
CONTRACTIONS = {
    "fr": [("de le", "du"), ("à le", "au"), ("de les", "des"), ("à les", "aux")],
    "es": [("a el", "al"), ("de el", "del")],
    "it": [(f"{p} {a}", f"{c}{e}") for p, c in (("a", "a"), ("di", "de"), ("da", "da"), ("su", "su"))
           for a, e in (("il", "l"), ("la", "lla"), ("lo", "llo"))]  # (not "i": it is mostly a variable)
          + [(f"{p} l'", f"{c}ll'") for p, c in (("a", "a"), ("di", "de"), ("da", "da"), ("su", "su"))],
}
OPERATIONS = set("=≠<>≤≥≈≡∝∼≃≪≫∈∉⊂⊆∪∩→←↦⇒⇔+−-±∓·×⋅⊙⊗⊕∘/,;:|")
# accents set as combining marks over a letter (ā), as they come from text: said like hat(x), bar(x), ...
COMBINING = {"\u0302": "hat", "\u0303": "tilde", "\u0304": "bar", "\u0305": "bar", "\u0307": "dot", "\u0308": "ddot",
             "\u20d7": "vec"}
ORDINALS = {"th", "st", "nd", "rd"}  # l^th: the l-th, not a power
LABEL = re.compile(r",\s*equation \((\w{1,4})\)\s*$")
TOKEN = re.compile(r"\s+|\d+(?:\.\d+)?|[A-Za-zÀ-ÖØ-öø-ɏ]+|.", re.S)  # (Latin letters, accented too)


@dataclass
class _Tok:
    text: str
    spaced: bool = False  # whitespace before it


@dataclass
class _Node:
    kind: str  # sym / seq / group / script / frac / root / accent / matrix / apply / big / bars
    text: str = ""
    parts: list = field(default_factory=list)


def _tokens(text: str) -> list[_Tok]:
    out: list[_Tok] = []
    space = False
    for m in TOKEN.finditer(text):
        t = m.group()
        if t.isspace():
            space = True
            continue
        if t.isalpha() and t.isascii() and len(t) == 2 and t not in SHORT_WORDS and t not in FUNCTIONS:
            for k, c in enumerate(t):  # "Wx", "dt": letters side by side
                out.append(_Tok(c, space and k == 0))
        else:
            out.append(_Tok(t, space))
        space = False
    return out


class _Parser:
    def __init__(self, toks: list[_Tok]):
        self.t = toks
        self.i = 0

    def peek(self, k: int = 0) -> Optional[_Tok]:
        return self.t[self.i + k] if self.i + k < len(self.t) else None

    def take(self) -> _Tok:
        tok = self.t[self.i]
        self.i += 1
        return tok

    def seq(self, stop: str = "") -> _Node:
        """Items up to the closing bracket ``stop`` (not taken)."""
        items: list[_Node] = []
        while self.peek() is not None and self.peek().text not in (stop or "\x00"):
            if not stop and self.peek().text in ")]}":
                items.append(_Node("sym", self.take().text))  # a bracket without its partner: said as it is
                continue
            item = self.item()
            if item is not None:
                items.append(item)
        return _Node("seq", parts=items)

    def bracketed(self) -> _Node:
        """A bracket and what it holds, up to its partner (``text``: the pair, then "s" when a space came before)."""
        tok = self.take()
        o = tok.text
        c = {"(": ")", "[": "]", "{": "}"}[o]
        inner = self.seq(c)
        if self.peek() is not None:
            self.take()
        return _Node("group", o + c + ("s" if tok.spaced else ""), [inner])

    def atom(self) -> Optional[_Node]:
        tok = self.peek()
        if tok is None:
            return None
        t = tok.text
        if t in "([{":
            return self.bracketed()
        self.take()
        if t == "√":
            index = None
            if self.peek() is not None and self.peek().text == "[":
                index = self.bracketed().parts[0]
            body = self.argument()
            return _Node("root", parts=[index, body])
        if t in ACCENT_WORDS | {"matrix", "cases"} and self.peek() is not None and self.peek().text == "(" \
                and not self.peek().spaced:
            inner = self.bracketed().parts[0]
            if t in ("matrix", "cases"):
                rows, cur = [], []
                for it in inner.parts:
                    if it.kind == "sym" and it.text == ";":
                        rows.append(_Node("seq", parts=cur))
                        cur = []
                    else:
                        cur.append(it)
                rows.append(_Node("seq", parts=cur))
                return _Node("matrix", t, rows)
            return _Node("accent", t, [inner])
        return _Node("sym", t)

    def argument(self) -> Optional[_Node]:
        """What a script, a fraction part or a root holds: a bracketed group (its brackets only group) or one
        symbol."""
        tok = self.peek()
        if tok is None:
            return None
        if tok.text in "({":
            return self.bracketed().parts[0]
        return self.atom()

    def scripts(self, base: _Node) -> _Node:
        sub = sup = None
        primes = ""
        while self.peek() is not None:
            t = self.peek().text
            if t in "′″‴'" and not self.peek().spaced:
                primes += self.take().text
            elif t in "_^" and (sub is None if t == "_" else sup is None):
                self.take()
                arg = self.argument()
                if t == "_":
                    sub = arg
                else:
                    sup = arg
            else:
                break
        if sub is None and sup is None and not primes:
            return base
        return _Node("script", primes, [base, sub, sup])

    def item(self) -> Optional[_Node]:
        tok = self.peek()
        if tok.text in "_^":  # a script with nothing before it (a fraction set as ¹/K): said as one
            self.take()
            return _Node("script", "", [_Node("seq"), self.argument(), None] if tok.text == "_"
                         else [_Node("seq"), None, self.argument()])
        a = self.atom()
        if a is None:
            return None
        a = self.scripts(a)
        if self.peek() is not None and self.peek().text == "/" and not (a.kind == "sym" and a.text in OPERATIONS):
            self.take()
            num = a.parts[0] if a.kind == "group" and a.text.startswith("()") else a
            den = self.argument()
            den = self.scripts(den) if den is not None else _Node("seq")
            return _Node("frac", parts=[num, den])
        return a


# ---------------------------------------------------------------------------------------------------- saying

class _Say:
    def __init__(self, lang: str):
        self.w = WORDS.get(lang, WORDS["en"])
        self.lang = lang if lang in WORDS else "en"
        self.greek = dict(zip(GREEK, GREEK_NAMES[self.lang].split()))

    def word(self, key: str, x: str = "") -> str:
        return self.w["@" + key].replace("{x}", x)

    def sym(self, t: str) -> str:
        t = GREEK_VARIANTS.get(t, t)
        if t in self.greek:
            return self.greek[t]
        if t.lower() in self.greek and len(t) == 1 and t.isupper():
            return self.word("capital", self.greek[t.lower()])
        if t == "\x00dot":
            return self.word("placeholder")
        if t in BIG:  # an operator without its limits ("√∑ x")
            return self.word(BIG[t])
        return self.w.get(t, t)

    @staticmethod
    def short(n: Optional[_Node]) -> bool:
        """Two or three symbols, none of them an operation ("∂z", "dt", "x_i"): clear without marking its end."""
        if n is None or _Say.simple(n):
            return True
        parts = n.parts if n.kind == "seq" else [n]
        return len(parts) <= 3 and all(
            (p.kind == "sym" and p.text not in OPERATIONS) or
            (p.kind == "script" and _Say.simple(p.parts[0]) and _Say.simple(p.parts[1]) and _Say.simple(p.parts[2]))
            for p in parts)

    @staticmethod
    def simple(n: Optional[_Node]) -> bool:
        """One symbol (said without marking where it ends)."""
        if n is None:
            return True
        if n.kind == "seq":
            return len(n.parts) == 1 and _Say.simple(n.parts[0])
        return n.kind == "sym"

    def say(self, n: Optional[_Node]) -> str:
        if n is None:
            return ""
        k = n.kind
        if k == "sym":
            return self.sym(n.text)
        if k == "seq":
            return self.seq(n.parts)
        if k == "group":
            inner = self.say(n.parts[0])
            if n.text.startswith("{}"):
                return inner
            return f"{self.word('open')} {inner} {self.word('close')}"
        if k == "script":
            return self.script(n)
        if k == "frac":
            num, den = n.parts
            if self.short(num) and self.short(den):
                return f"{self.say(num)} {self.word('over')} {self.say(den)}"
            return f"{self.word('frac')} {self.say(num)}, {self.word('over')} {self.say(den)}, {self.word('frac_end')},"
        if k == "root":
            index, body = n.parts
            start = self.word("sqrt") if index is None else self.word("root", self.say(index))
            if self.simple(body):
                return f"{start} {self.say(body)}"
            return f"{start} {self.say(body)}, {self.word('root_end')},"
        if k == "accent":
            return self.word(n.text, self.say(n.parts[0]))
        if k == "matrix":
            rows = [self.say(r) for r in n.parts]
            if n.text == "cases":
                return f"{self.word('cases')}: " + "; ".join(rows) + ";"
            return f"{self.word('matrix')}, " + "; ".join(f"{self.word('row')} {i + 1}: {r}"
                                                      for i, r in enumerate(rows)) + f", {self.word('end_matrix')},"
        return ""

    def script(self, n: _Node) -> str:
        base, sub, sup = n.parts
        out = self.say(base)
        if not out and sup is not None:
            return f"{self.word('super')} {self.say(sup)}"
        if sub is not None:
            out += f" {self.word('sub')} {self.say(sub)}" + ("" if self.simple(sub) else ",")
        for p in n.text:
            out += " " + self.word("dprime" if p == "″" else "prime")
        if sup is not None:
            out += " " + self.power(sup)
        return out

    def power(self, sup: _Node) -> str:
        flat = "".join(n.text for n in (sup.parts if sup.kind == "seq" else [sup]) if n.kind == "sym")
        if flat in ORDINALS and (sup.kind != "seq" or all(n.kind == "sym" for n in sup.parts)):
            return flat  # "l th"
        s = sup.parts[0] if sup.kind == "seq" and len(sup.parts) == 1 else sup
        if s.kind == "sym":
            if s.text == "2":
                return self.word("squared")
            if s.text == "3":
                return self.word("cubed")
            if s.text == "⊤":
                return self.word("transpose")
            if s.text in ("*", "∗"):
                return self.word("star")
            if s.text in "′″":
                return self.word("prime")
            if s.text in OPERATIONS:
                return f"{self.word('super')} {self.say(s)}"
        # a number is a power; a letter or expression may as well be an index (layer l, time t): "superscript"
        numeric = all(n.kind == "sym" and (re.fullmatch(r"\d+(?:\.\d+)?", n.text) or n.text in "−-") for n in
                      (sup.parts if sup.kind == "seq" else [sup])) and any(c.isdigit() for c in flat)
        word = self.word("power" if numeric else "super")
        return f"{word} {self.say(sup)}" + ("" if self.simple(sup) else ",")

    def big(self, op: str, node: _Node) -> str:
        """A sum, product or integral with its limits: "the sum from i equals 1 to n of"."""
        base, sub, sup = node.parts if node.kind == "script" else (node, None, None)
        out = self.word(BIG[op])
        if sub is not None:
            out += f" {self.word('from')} {self.say(sub)}"
        if sup is not None:
            out += f" {self.word('to')} {self.say(sup)}"
        return out + f" {self.word('of')}"

    def seq(self, items: list[_Node]) -> str:
        if len(items) == 1 and items[0].kind == "sym" and items[0].text in "·∙⋅":
            return self.word("placeholder")  # f(·): any argument
        for k, it in enumerate(items):  # [·,·]: dots standing for arguments, between commas or brackets
            if it.kind == "sym" and it.text in "·∙⋅" and all(
                    n is None or (n.kind == "sym" and n.text in ",;")
                    for n in (items[k - 1] if k else None, items[k + 1] if k + 1 < len(items) else None)):
                items = items[:k] + [_Node("sym", "\x00dot")] + items[k + 1:]
        words: list[str] = []
        bars = [k for k, it in enumerate(items) if it.kind == "sym" and it.text in "|‖∥"]
        pairs = {}
        for kind in ("|", "‖∥"):
            ks = [k for k in bars if items[k].text in kind]
            if len(ks) >= 2 and len(ks) % 2 == 0:
                for a, b in zip(ks[::2], ks[1::2]):
                    pairs[a], pairs[b] = "abs" if kind == "|" else "norm", "end"
        k = 0
        while k < len(items):
            it = items[k]
            nxt = items[k + 1] if k + 1 < len(items) else None
            head = it.parts[0] if it.kind == "script" else it
            if head.kind == "sym" and head.text in BIG:
                words.append(self.big(head.text, it))
            elif head.kind == "sym" and head.text in LIMITS and it.kind == "script" and it.parts[1] is not None \
                    and it.parts[2] is None and not it.text:
                words.append(self.word(head.text, self.say(it.parts[1])))
            elif k in pairs:
                if pairs[k] == "end":
                    words.append(self.word("abs_end" if items[k].text == "|" else "norm_end") + ",")
                else:
                    words.append(self.word(pairs[k]))
            elif nxt is not None and nxt.kind == "group" and nxt.text.startswith("()") and self.applies(it, nxt):
                arg = self.say(nxt.parts[0])
                words.append(f"{self.say(it)} {self.word('of')} {arg}" + ("" if self.simple(nxt.parts[0]) else ","))
                k += 1
            else:
                words.append(self.say(it))
            k += 1
        text = " ".join(w for w in words if w)
        text = re.sub(r"\s+([,;:])", r"\1", text)
        return re.sub(r",(\s*,)+", ",", text)

    @staticmethod
    def applies(it: _Node, group: _Node) -> bool:
        """``f(x)``, ``p_i(z)``, ``log(x)``: a function applied to what the brackets hold."""
        head = it.parts[0] if it.kind == "script" else it
        if head.kind == "accent":
            head = head.parts[0].parts[0] if head.parts[0].parts else head
        if head.kind != "sym":
            return False
        t = head.text
        # "f(x)" and "log (x)"; a letter and a bracket set apart ("F (θ)") may be a product
        return t in FUNCTIONS or (len(t) == 1 and (t.isalpha() or t in GREEK_VARIANTS) and not group.text.endswith("s"))


def speak(text: str, lang: str = "en") -> str:
    """A formula's linear text said in words, in the document's language (English when it is not one of en, nl, de,
    fr, es, it); "" when it cannot be said (the caller then names it a formula)."""
    try:
        return _speak(text, lang)
    except Exception:  # (the reading goes on whatever a formula's text holds)
        return ""


def _speak(text: str, lang: str) -> str:
    text = text.strip()
    if not text:
        return ""
    sayer = _Say(lang)
    number = ""
    m = LABEL.search(text)
    if m:
        number, text = m.group(1), text[:m.start()]
    text = re.sub(r"\.\s*\.\s*\.", "…", re.sub(r"·\s*·\s*·", "⋯", text))  # ". . ." is one ellipsis
    text = unicodedata.normalize("NFC", re.sub(
        "(\\S)([" + "".join(COMBINING) + "])", lambda m: f"{COMBINING[m.group(2)]}({m.group(1)})",
        unicodedata.normalize("NFD", text)))
    rows = [r for r in re.split(r"\s;\s", text) if r.strip()]  # the rows of a derivation
    said = "; ".join(sayer.say(_Parser(_tokens(r)).seq()) for r in rows)
    said = re.sub(r"\s+", " ", said).strip().rstrip(",")
    for a, b in CONTRACTIONS.get(sayer.lang, ()):  # "a il valore" is "al valore", "de le produit" "du produit"
        said = re.sub(rf"(?<!\S){re.escape(a)}" + ("" if a.endswith("'") else r"(?!\S)"), b, said)
    if number:
        said += f", {sayer.word('equation')} {number}"
    return said


def formulas_in_runs(runs: list) -> list[tuple[int, int, str]]:
    """The formulas set as text in a paragraph's runs (maths runs with their indices, over spaces), as (start, end,
    text in the converter's notation) with positions in the runs' joined text: ``x`` + index ``i`` + power ``2`` is
    ``x_i^2``. Note markers (∗, †) are not maths."""
    out: list[tuple[int, int, str]] = []
    parts: list[tuple[str, str]] = []
    start = pos = end = 0

    def close() -> None:
        nonlocal parts
        text = ""
        for kind, t in parts:
            if kind in ("sup", "sub"):
                t = t.strip()
                text += ("^" if kind == "sup" else "_") + (t if len(t) == 1 else f"({t})")
            else:
                text += t
        text = text.strip().strip(",;").strip()
        if text.strip("∗*†‡§¶ "):
            out.append((start, end, text))
        parts = []

    for r in runs:
        script = r.superscript or r.subscript
        if r.math or (script and parts):
            if not parts:
                start = pos + len(r.text) - len(r.text.lstrip())
            kind = "sup" if r.superscript else "sub" if r.subscript else "base"
            if parts and parts[-1][0] == kind:
                parts[-1] = (kind, parts[-1][1] + r.text)
            else:
                parts.append((kind, r.text))
            end = pos + len(r.text.rstrip())
        elif parts and not r.text.strip():
            parts.append(("base", r.text))  # a space between two parts of one formula
        else:
            if parts:
                close()
        pos += len(r.text)
    if parts:
        close()
    return out
