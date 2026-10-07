"""'Sources at the end': the reference list and notes set small, or small in two columns, to save paper. The
sources are always all kept, with their numbers, and never run off the page."""
import copy
import io
import re

import pymupdf
import pytest

from dyslexia_converter import pipeline
from dyslexia_converter.render import compose
from dyslexia_converter.settings import FormatSettings


def _words(pdf: bytes) -> list[str]:
    with pymupdf.open(stream=pdf) as d:
        return sorted(w for p in d for w in p.get_text().replace("-", "").split() if not w.isdigit())


@pytest.fixture(scope="module")
def long_list(paper):
    """The sample paper with a long reference list (as many real papers have), citations as numbers."""
    session = pipeline.load(paper)
    doc = session.document
    refs = [b for b in doc.blocks if b.kind.name == "REFERENCE"]
    assert refs, "the sample paper has a reference list"
    extra = []
    for n in range(80):  # many more entries, of varied length, in the style of the existing ones
        b = refs[n % len(refs)]
        c = copy.copy(b)
        c.id = f"x{n}"
        c.text = (f"Author{n}, A. ({1990 + n % 30}). " + "A study of something rather particular " * (1 + n % 4)
                  + f"Journal {n}, {n}-{n + 9}.")
        extra.append(c)
    doc.blocks[doc.blocks.index(refs[-1]) + 1:doc.blocks.index(refs[-1]) + 1] = extra
    return session


@pytest.mark.parametrize("numbers", [False, True])
def test_small_and_two_columns_keep_every_source_and_save_pages(long_list, numbers):
    pdfs = {mode: long_list.export("pdf", FormatSettings(sources_layout=mode, move_citations=numbers))
            for mode in ("normal", "small", "columns")}
    pages = {}
    for mode, pdf in pdfs.items():
        with pymupdf.open(stream=pdf) as d:
            pages[mode] = d.page_count
            bottom = d[0].rect.height - FormatSettings().margin_bottom * 72 / 2.54
            for p in d:  # nothing runs past the bottom margin (the page number sits below it)
                for b in p.get_text("dict")["blocks"]:
                    for line in b.get("lines", []):
                        text = "".join(s["text"] for s in line["spans"]).strip()
                        if text and not text.isdigit():
                            assert line["bbox"][3] <= bottom + 1, f"{mode}: text below the margin on page {p.number + 1}"
    assert _words(pdfs["small"]) == _words(pdfs["normal"]) == _words(pdfs["columns"])  # every source kept
    assert pages["small"] < pages["normal"] and pages["columns"] <= pages["small"]
    if numbers:  # with citations as numbers, every source at the end shows its number, in every layout
        for pdf in pdfs.values():
            with pymupdf.open(stream=pdf) as d:
                text = "\n".join(p.get_text() for p in d)
            last = text[text.rfind("References"):] if "References" in text else text
            numbers_shown = {int(m) for m in re.findall(r"^\[?(\d+)[\].] ", last, re.M)}
            assert {1, 2, 80} <= numbers_shown  # the first sources and those far down the list


def test_word_export_puts_the_sources_in_two_columns(long_list):
    import docx

    d = docx.Document(io.BytesIO(long_list.export("docx", FormatSettings(sources_layout="columns"))))
    ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    cols = [(s._sectPr.find(f"{ns}cols").get(f"{ns}num") if s._sectPr.find(f"{ns}cols") is not None else "1")
            for s in d.sections]
    assert "2" in cols and cols[-1] == "1"  # the list in two columns; what follows it in one again


def test_normal_is_the_default_and_unchanged():
    assert FormatSettings().sources_layout == "normal"
    assert FormatSettings.from_dict({"sources_layout": "columns"}).sources_layout == "columns"
