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
        "Language: en\nLength: short\nStyle: plain\nText:\n"
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


def summary_prompt(text: str, language: str, detailed: bool, plain: bool) -> str:
    """The request for one summary: the options, then the text."""
    return (f"Language: {language}\nLength: {'detailed' if detailed else 'short'}\n"
            f"Style: {'plain' if plain else 'normal'}\nText:\n{text}")
