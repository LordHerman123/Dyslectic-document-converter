"""OCR lines that run across a column gutter are split, so the columns are read one after the other."""
from dataclasses import dataclass

from dyslexia_converter.extract.pdf_reader import _split_wide_gaps


@dataclass
class W:
    text: str
    bbox: tuple


def _line(y, *parts):
    """Words of one OCR line: ``parts`` are (x, text) where the text starts; words are 50 wide, 10 apart."""
    words = []
    for x, text in parts:
        for t in text.split():
            words.append(W(t, (x, y, x + 50, y + 20)))
            x += 60
    return words


def _texts(groups):
    return sorted(" ".join(w.text for w in ws) for ws in groups.values())


def test_a_narrow_column_read_across_into_the_abstract_is_split():
    # "article info" box on the left, the abstract on the right, read by OCR as one line each
    groups = {
        (7, 1, 1): _line(100, (0, "Received 12 February 2023"), (900, "We compute the Poisson cohomology of algebras")),
        (7, 1, 2): _line(130, (0, "Accepted 8 May 2023"), (900, "together with existing results this gives all")),
    }
    out = _split_wide_gaps(groups)
    assert _texts(out) == sorted(["Received 12 February 2023", "Accepted 8 May 2023",
                                  "We compute the Poisson cohomology of algebras",
                                  "together with existing results this gives all"])
    left = {k for k, ws in out.items() if ws[0].text in ("Received", "Accepted")}
    right = set(out) - left
    assert {k[0] for k in left} != {k[0] for k in right}  # each column a block of its own


def test_a_single_wide_gap_and_table_rows_are_left_alone():
    # a title and its page number: one line with a wide gap, no neighbour with a gap there
    single = {(1, 1, 1): _line(100, (0, "Results and discussion"), (1500, "3"))}
    assert _split_wide_gaps(single) == {k: sorted(v, key=lambda w: w.bbox[0]) for k, v in single.items()}
    # rows of a table: wide gaps at the same place, but short cells on both sides keep the row together
    table = {(2, 1, 1): _line(100, (0, "Control group"), (900, "12 patients")),
             (2, 1, 2): _line(130, (0, "Treated group"), (900, "15 patients"))}
    assert _texts(_split_wide_gaps(table)) == ["Control group 12 patients", "Treated group 15 patients"]


def test_ordinary_lines_are_unchanged():
    groups = {(3, 1, n): _line(100 + 30 * n, (0, "an ordinary line of prose with normal spaces")) for n in range(3)}
    assert _texts(_split_wide_gaps(groups)) == _texts(groups)
