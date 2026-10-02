"""Tapping a citation or note marker shows what it points to."""
from dyslexia_converter.model import Block, BlockKind, Document
from dyslexia_converter.render.compose import compose
from dyslexia_converter.render.popups import Popups
from dyslexia_converter.settings import FormatSettings


def test_markers_find_their_references_and_notes():
    p = Popups()
    p.add_reference(3, "[3] Smith J (2019) A paper.")
    p.add_reference(4, "4. Lee K (2020) Another.")
    p.notes["[Note 2]"] = "A note."
    p.citations["(Kim, 2018)"] = ["Kim (2018) A book."]
    text = "as shown [3-4] and (Kim,\n2018) in [3, 9] here [Note 2]."
    at = lambda w: p.at(text, text.index(w) + 1)
    assert at("[3-4]").entries == ["[3] Smith J (2019) A paper.", "[4] Lee K (2020) Another."]
    assert at("Kim").label == "(Kim, 2018)" and at("2018)").entries == ["Kim (2018) A book."]
    assert at("[3, 9]").entries == ["[3] Smith J (2019) A paper."]  # 9 is not in the list
    assert at("[Note").kind == "note" and at("[Note").entries == ["A note."]
    assert at("here") is None and at("shown") is None
    assert not Popups() and p


def _doc(blocks):
    doc = Document(source_path="x.pdf", blocks=blocks)
    doc.language = "en"
    return doc


def test_composing_collects_references_citations_and_notes():
    refs = [Block(id="r1", kind=BlockKind.REFERENCE, text="Kitchin R (2014) Big data. Big Data & Society.", page=1),
            Block(id="r2", kind=BlockKind.REFERENCE, text="Laney D (2001) 3D data management.", page=1)]
    para = Block(id="p1", kind=BlockKind.PARAGRAPH, text="Big data changes research (Kitchin, 2014; Laney, 2001).",
                 page=0)
    pop = compose(_doc([para] + refs), FormatSettings(move_citations=False)).popups
    assert pop.references == {1: refs[0].text, 2: refs[1].text}
    assert pop.citations == {"(Kitchin, 2014; Laney, 2001)": [refs[0].text, refs[1].text]}

    moved = compose(_doc([para] + refs), FormatSettings(move_citations=True)).popups
    text = "Big data changes research [1][2]."
    assert moved.at(text, text.index("[2]") + 1).entries == ["[2] " + refs[1].text]
    assert not moved.citations  # moved citations are numbers now

    numbered = [Block(id="n1", kind=BlockKind.REFERENCE, text="[7] Brown T (2020) Models.", page=1)]
    pop = compose(_doc([Block(id="p", kind=BlockKind.PARAGRAPH, text="As in [7].", page=0)] + numbered),
                  FormatSettings()).popups
    assert pop.references == {7: "Brown T (2020) Models."}  # its own number, without the number in the text
