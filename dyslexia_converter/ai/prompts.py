"""Prompts for the AI tasks: short instructions plus worked examples (few-shot), and compact answers.

Every request has two parts:

* ``system``: the instructions and the worked examples. They are the same for every request of a task, so
  providers that cache a repeated prompt start (Anthropic, Gemini) charge only a fraction for them after the
  first request.
* ``prompt``: the numbered items of this request, each a few words of the document around a marked item.

Answers only list the exceptions (the ids that are citations, the words that are OCR errors), which keeps the
output short. Each task also has a JSON schema for providers that enforce one.
"""
from __future__ import annotations

from dataclasses import dataclass

from .privacy import MARK_CLOSE, MARK_OPEN

M0, M1 = MARK_OPEN, MARK_CLOSE


@dataclass(frozen=True)
class Task:
    """An AI task: its fixed instructions with examples (few-shot), the JSON schema of the answer, the answer format
    for providers that cannot enforce a schema, and the answer size per snippet.
    """
    name: str
    system: str
    schema: dict
    answer_hint: str  # the answer format, for providers without enforced schemas
    tokens_per_item: int  # to size max_tokens


CITATIONS = Task(
    name="citations",
    system=(
        "You help a tool that makes academic documents easier to read for people with dyslexia. "
        "You answer one narrow question and never rewrite text.\n\n"
        f"Each numbered line holds a short piece of a document with one part marked {M0}like this{M1}. "
        "Decide for each whether the marked part is an in-text citation of a source (author or organisation "
        "with a year, page or 'et al.'), as opposed to other text in brackets: an explanation, abbreviation, "
        "statistic, cross-reference or date.\n"
        'Answer with JSON: {"c": [ids of the lines that ARE citations]}. Leave out every other line.\n\n'
        "Examples\n"
        f"0: …as argued earlier {M0}(Kitchin, 2014){M1} big data changes…\n"
        f"1: …the sample {M0}(n = 42){M1} was too small to…\n"
        f"2: …results are shown below {M0}(see Table 2){M1} and discussed…\n"
        f"3: …has been widely studied {M0}(boyd and Crawford 2012; Laney, 2001){M1} in several fields…\n"
        f"4: …many soldiers died during the war {M0}(1914–1918){M1} in the…\n"
        f"5: …een bekende theorie {M0}(Van Dijk, 2006, p. 12){M1} stelt dat…\n"
        f"6: …the World Health Organization {M0}(WHO){M1} reported that…\n"
        f"7: …as the report notes {M0}(WHO, 2020){M1}, vaccination…\n"
        f"8: …this effect was large {M0}(Smith et al.){M1} and it…\n"
        f"9: …temperature rose sharply {M0}(from 12 to 19 °C){M1} within…\n"
        'Answer: {"c": [0, 3, 5, 7, 8]}'
    ),
    schema={"type": "object", "additionalProperties": False, "required": ["c"],
            "properties": {"c": {"type": "array", "items": {"type": "integer"}}}},
    answer_hint='Answer with JSON only: {"c": [ids]}',
    tokens_per_item=3,
)

OCR = Task(
    name="ocr",
    system=(
        "You help a tool that makes scanned documents easier to read for people with dyslexia. "
        "You answer one narrow question and never rewrite text.\n\n"
        f"Each numbered line holds a word read by OCR, marked {M0}like this{M1}, with a few words around it, "
        "after 'suggested:' a spelling correction the tool is unsure about. Decide for each whether the "
        "marked word is an OCR reading error. If it is, give the intended word: one word, same language, "
        "same meaning, no rephrasing. The suggestion may be wrong. Names, technical terms, abbreviations and "
        "words from another language are usually correct.\n"
        'Answer with JSON: {"f": [{"i": id, "w": "intended word"}]} for the errors only. Leave out every '
        "word that is correct.\n\n"
        "Examples\n"
        f"0: suggested: the | …the sample was found in {M0}tbe{M1} upper layer of…\n"
        f"1: suggested: Maynard | …National University of Ireland {M0}Maynooth{M1}, County Kildare…\n"
        f"2: suggested: model | …we trained a new {M0}rnodel{M1} on the data…\n"
        f"3: suggested: lass | …objects of each {M0}c1ass{M1} are counted…\n"
        f"4: suggested: CRISP | …edited with {M0}CRISPR{M1} in the second…\n"
        f"5: suggested: het | …de resultaten van {M0}hct{M1} onderzoek laten…\n"
        f"6: suggested: modern | …changes in the {M0}modem{M1} era of mass…\n"
        f"7: suggested: dataset | …stored in the {M0}datasct{M1} described above…\n"
        'Answer: {"f": [{"i": 0, "w": "the"}, {"i": 2, "w": "model"}, {"i": 3, "w": "class"}, '
        '{"i": 5, "w": "het"}, {"i": 6, "w": "modern"}, {"i": 7, "w": "dataset"}]}'
    ),
    schema={"type": "object", "additionalProperties": False, "required": ["f"],
            "properties": {"f": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["i", "w"],
                "properties": {"i": {"type": "integer"}, "w": {"type": "string"}}}}}},
    answer_hint='Answer with JSON only: {"f": [{"i": id, "w": "word"}]}',
    tokens_per_item=10,
)


SPLITS = Task(
    name="splits",
    system=(
        "You help a tool that makes documents easier to read for people with dyslexia. "
        "You answer one narrow question and never rewrite text.\n\n"
        f"Each numbered line holds a few words of a document with two pieces marked {M0}like this{M1}. Scanning "
        "and copying text out of PDFs sometimes puts a space inside a word. Decide for each whether the marked "
        "pieces are one word wrongly split by a space. Letters used as symbols or names (a variable, an "
        "initial, a unit) and two real words are not split words.\n"
        'Answer with JSON: {"j": [ids of the lines whose pieces are ONE word]}. Leave out every other line.\n\n'
        "Examples\n"
        f"0: …papers {M0}subm itted{M1} to the journal were…\n"
        f"1: …for every integer of {M0}degree n{M1} we find that…\n"
        f"2: …the Journal {M0}o f{M1} Natural Pharmaceuticals…\n"
        f"3: …signed by {M0}A T{M1} Smith and…\n"
        f"4: …it was a {M0}lit tle{M1} too late to…\n"
        f"5: …costs grow {M0}since r{M1} is larger than…\n"
        f"6: …{M0}W hen{M1} the editors replied…\n"
        'Answer: {"j": [0, 2, 4, 6]}'
    ),
    schema={"type": "object", "additionalProperties": False, "required": ["j"],
            "properties": {"j": {"type": "array", "items": {"type": "integer"}}}},
    answer_hint='Answer with JSON only: {"j": [ids]}',
    tokens_per_item=3,
)


def citation_prompt(snippets: list[str]) -> str:
    """The snippets of one request, numbered from 0, one per line."""
    return "\n".join(f"{i}: {s}" for i, s in enumerate(snippets))


def ocr_prompt(items: list[tuple[str, str]]) -> str:
    """items: (suggested word, snippet with the OCR word marked)."""
    return "\n".join(f"{i}: suggested: {sug} | {snip}" for i, (sug, snip) in enumerate(items))


SUMMARY = Task(
    name="summary",
    system=(
        "You help people with dyslexia read academic documents. You summarise a part of a document that the "
        "reader chose, so they can see the main points before or after reading it. The summary is shown next "
        "to the original text, never instead of it.\n\n"
        "Rules:\n"
        "- Use only what the text says. Do not add facts, opinions or advice.\n"
        "- Write in the language given on the first line (the document's language).\n"
        "- 'Length: short' means 3 to 5 points; 'Length: detailed' means 6 to 10 points.\n"
        "- 'Style: plain' means short sentences (at most 15 words) and everyday words; explain a needed term "
        "in a few words. 'Style: normal' keeps the terms of the text.\n"
        "- Keep who says what: 'Anderson argues...', not as if it were a fact.\n"
        "- Give a short title for the part summarised.\n"
        'Answer with JSON: {"t": "title", "b": ["point", "point", ...]}.\n\n'
        "Example\n"
        "Language: en\nLength: short (3 to 5 points, no more)\nStyle: plain\nText:\n"
        "Photosynthesis is the process by which green plants convert light energy into chemical energy. Using "
        "chlorophyll, they absorb sunlight and combine carbon dioxide and water into glucose, releasing oxygen "
        "as a by-product. Smith (2019) notes that the rate depends on light intensity and temperature.\n"
        'Answer: {"t": "How plants make food", "b": ["Plants use light to make their own food (sugar).", '
        '"The green substance chlorophyll takes in the sunlight.", "They use carbon dioxide and water, and give '
        'off oxygen.", "Smith (2019) says light and temperature change how fast this goes."]}'
    ),
    schema={"type": "object", "additionalProperties": False, "required": ["t", "b"],
            "properties": {"t": {"type": "string"}, "b": {"type": "array", "items": {"type": "string"}}}},
    answer_hint='Answer with JSON only: {"t": "title", "b": ["point", ...]}',
    tokens_per_item=700,
)


EXPLAIN = Task(
    name="explain",
    system=(
        "You help people with dyslexia understand academic texts. The reader chose a short part they find hard "
        "to follow. You explain what it means, so they can go back to the text and understand it. The "
        "explanation is shown next to the original text, never instead of it.\n\n"
        "Rules:\n"
        "- Explain only what the text says and means. Do not add facts, opinions or advice, and do not judge it.\n"
        "- Write in the language given on the first line (the document's language).\n"
        "- Use short sentences (at most 15 words) and everyday words.\n"
        "- First 2 to 5 points that say what the text means, in order. Then, for up to 4 difficult words or "
        "terms from the text, one point each: 'term: what it means here'.\n"
        "- Keep who says what: 'The author argues...', not as if it were a fact.\n"
        "- Give a short title that says what the part is about.\n"
        'Answer with JSON: {"t": "title", "b": ["point", "point", ...]}.\n\n'
        "Example\n"
        "Language: en\nText:\n"
        "Heteronormative assumptions in curricula marginalise students whose identities fall outside them, "
        "Jones (2018) contends, thereby reproducing structural inequities.\n"
        'Answer: {"t": "How school lessons can leave students out", "b": ["Jones (2018) looks at what lessons '
        'take for granted.", "Lessons often assume everyone is straight.", "Jones says this pushes other '
        'students to the side.", "In this way, unfair patterns in society keep going.", "heteronormative: '
        'taking for granted that everyone is straight", "curricula: what is taught at school", "structural '
        'inequities: unfairness built into how society works"]}'
    ),
    schema={"type": "object", "additionalProperties": False, "required": ["t", "b"],
            "properties": {"t": {"type": "string"}, "b": {"type": "array", "items": {"type": "string"}}}},
    answer_hint='Answer with JSON only: {"t": "title", "b": ["point", ...]}',
    tokens_per_item=700,
)


LANGUAGE_NAMES = {"en": "English", "nl": "Dutch", "fr": "French", "de": "German", "es": "Spanish",
                  "it": "Italian"}  # named in full at the end of a summary request: a bare code is easily missed


LAYOUT = Task(
    name="layout",
    system=(
        "You help a tool that makes documents easier to read for people with dyslexia. You never rewrite text: "
        "you only put the pieces of one page in reading order.\n\n"
        "Each numbered line is one piece of the page: where it is (x from its left to its right edge and y from "
        "its top to its bottom, in % of the page), its font size, and its first and last words (… marks words "
        "left out). [figure] is a picture.\n"
        "Put all pieces in reading order. The title and headings go where they belong. Running text is read "
        "column by column: the left column from top to bottom, then the next column. A piece whose last words "
        "run on into the first words of another piece is followed by that piece. Pull quotes (large text that "
        "repeats a sentence of the article), side boxes, adverts, photo credits and page labels go after the "
        "running text, in the order they appear. Never leave a piece out.\n"
        'Answer with JSON: {"o": [piece numbers in reading order]}.\n\n'
        "Example\n"
        "0 | x 5-95 y 8-12 | 24pt | THE HIDDEN COST OF SLEEP\n"
        "1 | x 5-48 y 20-45 | 9pt | Most people think that a good night's rest … the brain clears waste while we\n"
        "2 | x 52-95 y 20-45 | 9pt | adults who slept less than six hours … were more likely to\n"
        "3 | x 30-70 y 46-52 | 16pt | “THE BRAIN CLEARS WASTE WHILE WE SLEEP.”\n"
        "4 | x 5-28 y 53-80 | 9pt | sleep, researchers now say. The study followed … and found that\n"
        "5 | x 72-95 y 53-80 | 9pt | forget words. Not everyone agrees … most people sleep less.\n"
        "6 | x 5-48 y 82-92 | 8pt | SUBSCRIBE TODAY … and save 30%\n"
        "7 | x 97-99 y 30-60 | 6pt | PHOTO: J. DOE\n"
        "8 | x 52-95 y 82-92 | [figure]\n"
        'Answer: {"o": [0, 1, 4, 2, 5, 8, 3, 6, 7]}'
    ),
    schema={"type": "object", "additionalProperties": False, "required": ["o"],
            "properties": {"o": {"type": "array", "items": {"type": "integer"}}}},
    answer_hint='Answer with JSON only: {"o": [piece numbers in reading order]}',
    tokens_per_item=4,
)


def layout_prompt(pieces: list[tuple[float, float, float, float, float, str | None]]) -> str:
    """One page for the layout task: per piece its place (in % of the page: x0, y0, x1, y1), font size and the
    first and last words of its text (None for a picture)."""
    rows = []
    for n, (x0, y0, x1, y1, size, text) in enumerate(pieces):
        place = f"x {round(x0)}-{round(x1)} y {round(y0)}-{round(y1)}"
        if text is None:
            rows.append(f"{n} | {place} | [figure]")
            continue
        words = text.split()
        shown = " ".join(words) if len(words) <= 18 else " ".join(words[:10]) + " … " + " ".join(words[-6:])
        rows.append(f"{n} | {place} | {size:g}pt | {shown}")
    return "\n".join(rows)


def summary_prompt(text: str, language: str, detailed: bool, plain: bool) -> str:
    """The request for one summary: the options, then the text."""
    # the number of points is spelled out here too, and again after the text: some models skip the rule
    points = "6 to 10 points" if detailed else "3 to 5 points, no more"
    return (f"Language: {language}\nLength: {'detailed' if detailed else 'short'} ({points})\n"
            f"Style: {'plain' if plain else 'normal'}\nText:\n{text}\n\n"
            f"Cover the whole text in {points}. Write the title and points in "
            f"{LANGUAGE_NAMES.get(language, language)}.")


def explain_prompt(text: str, language: str) -> str:
    """The request to explain one part of the document."""
    return (f"Language: {language}\nText:\n{text}\n\n"
            f"Write the title and points in {LANGUAGE_NAMES.get(language, language)}.")


CHECK = Task(
    name="check",
    system=(
        "You help a tool that converts PDF documents into an easier-to-read version for people with dyslexia. "
        "Converting a PDF can go wrong. You read the converted text and point out where the CONVERSION went "
        "wrong. You never rewrite text, and you never judge the author's writing: spelling mistakes, grammar, "
        "style or odd wording that were already in the original are not conversion errors.\n\n"
        "The first line names the document's language. Each numbered line after it is one block of the converted "
        "document: its number | its kind (T title, H1-H3 "
        "heading, P paragraph, L list item, Q quote, C caption, N footnote; 'scan' means the text was read from "
        "a scan by text recognition) | the page of the original | its text.\n\n"
        "Report only these conversion errors:\n"
        "- word: a word broken in two ('num ber'), two words run together ('forthe'), or a hyphen from a line "
        "break left in or lost ('non- disclosure', 'self- report'). Give the corrected words in 'w'. A hyphen "
        "before 'and', 'or' or the same in another language is correct ('pre- and post-review', 'zorg- en "
        "welzijnswerk').\n"
        "- scan: only in 'scan' blocks, a word misread by text recognition ('tbe', 'rnodel'). Give the intended "
        "word in 'w'.\n"
        "- furniture: a running header or footer, page number, journal name or volume line, copyright or "
        "download notice inside the text. Quote all of it.\n"
        "- heading: a heading run into the start of a paragraph ('2. Methods We asked…'). Quote only the "
        "heading.\n"
        "- not_heading: a block marked as a heading (H1-H3) that is not a heading of this document, such as "
        "part of a sentence or a figure label.\n"
        "- order: text that breaks off and continues with something that does not belong there (a line from "
        "another column, a box or a caption spliced in). Quote the first words of the text that does not "
        "belong.\n"
        "In 'q' copy the text exactly as it is in the block, as short as possible (at most 12 words). Add a "
        "reason of at most 10 words in 'r'. When you are not sure, leave it out. Most blocks have no errors.\n"
        'Answer with JSON: {"f": [{"b": block number, "t": type, "q": "exact text", "w": "correction", '
        '"r": "reason"}]}, or {"f": []} when you find nothing.\n\n'
        "Example\n"
        "Language: English\n"
        "0 | T | p1 | THE PRICE OF KNOWLEDGE\n"
        "1 | P | p1 | Publishers say that their costs are high. The num ber of journals has grown fast, and some "
        "now charge less than 100 euro per paper. 1 2 | S C I E N C E | V O L 7 Yet prices still vary.\n"
        "2 | P | p2 | 2. Methods We asked forty publishers about their costs and recieved twelve answers.\n"
        "3 | P | p2 | Prices that libraries pay are hidden by the non- Germany; and the Wellcome Trust in London, "
        "have joined the plan. disclosure agreements that they sign.\n"
        "4 | H2 | p3 | Figure 2\n"
        "5 | P scan | p3 | Most of them said that the new rnodel was cheaper forthe small journals.\n"
        'Answer: {"f": [{"b": 1, "t": "word", "q": "num ber", "w": "number", "r": "word broken in two"}, '
        '{"b": 1, "t": "furniture", "q": "1 2 | S C I E N C E | V O L 7", "r": "page footer in the text"}, '
        '{"b": 2, "t": "heading", "q": "2. Methods", "r": "heading run into the paragraph"}, '
        '{"b": 3, "t": "order", "q": "Germany; and the Wellcome Trust in London, have joined the plan.", '
        '"r": "a line from another column breaks the sentence"}, '
        '{"b": 4, "t": "not_heading", "q": "Figure 2", "r": "a figure label, not a heading"}, '
        '{"b": 5, "t": "scan", "q": "rnodel", "w": "model", "r": "misread letters"}, '
        '{"b": 5, "t": "word", "q": "forthe", "w": "for the", "r": "two words run together"}]}\n'
        "('recieved' in block 2 is the author's own spelling, so it is not reported.)"
    ),
    schema={"type": "object", "additionalProperties": False, "required": ["f"],
            "properties": {"f": {"type": "array", "items": {
                "type": "object", "additionalProperties": False, "required": ["b", "t", "q", "w", "r"],
                "properties": {"b": {"type": "integer"}, "t": {"type": "string"}, "q": {"type": "string"},
                               "w": {"type": "string"}, "r": {"type": "string"}}}}}},
    answer_hint='Answer with JSON only: {"f": [{"b": block, "t": "type", "q": "exact text", "w": "correction", '
                '"r": "reason"}]}',
    tokens_per_item=25,
)


def check_prompt(blocks: list[tuple[int, str, int, str]], language: str = "en") -> str:
    """One part of the document for the check: its language, then per block its number, kind code, original page
    and text."""
    return f"Language: {LANGUAGE_NAMES.get(language, language)}\n" + \
        "\n".join(f"{n} | {kind} | p{page} | {text}" for n, kind, page, text in blocks)
