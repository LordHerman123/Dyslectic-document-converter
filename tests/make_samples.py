"""Generate sample PDFs used by the tests (and handy for manual trying-out).

    python tests/make_samples.py [output_dir]

Creates:
  sample_paper.pdf    two-column academic paper with title, authors, numbered
                      headings, citations, footnotes, a figure, a table, references
  sample_scanned.pdf  the same paper rasterised (image-only) to exercise OCR
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import pymupdf
from reportlab.graphics.shapes import Drawing, Line, Rect, String
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (BaseDocTemplate, Flowable, Frame, FrameBreak, NextPageTemplate, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

BODY = ParagraphStyle("body", fontName="Times-Roman", fontSize=9.5, leading=11.5, alignment=4,
                      firstLineIndent=10)
BODY0 = ParagraphStyle("body0", parent=BODY, firstLineIndent=0)
H1 = ParagraphStyle("h1", fontName="Times-Bold", fontSize=11.5, leading=14, spaceBefore=8, spaceAfter=4)
H2 = ParagraphStyle("h2", fontName="Times-Bold", fontSize=10, leading=12, spaceBefore=6, spaceAfter=3)
TITLE = ParagraphStyle("title", fontName="Times-Bold", fontSize=18, leading=22, alignment=1, spaceAfter=8)
AUTH = ParagraphStyle("auth", fontName="Times-Roman", fontSize=11, leading=14, alignment=1, spaceAfter=14)
CAP = ParagraphStyle("cap", fontName="Times-Roman", fontSize=8.5, leading=10, spaceBefore=4, spaceAfter=8)
REF = ParagraphStyle("ref", fontName="Times-Roman", fontSize=8.5, leading=10, leftIndent=10,
                     firstLineIndent=-10, spaceAfter=3)
FOOT = ParagraphStyle("foot", fontName="Times-Roman", fontSize=7.5, leading=9)

INTRO = ("Reading difficulties affect a substantial proportion of students in higher education. "
         "Previous studies have demonstrated that typographic adjustments can change reading speed "
         "(Smith, 2020; Jones & Brown, 2021). However, the evidence remains mixed and effects appear to "
         "depend strongly on the individual reader<super>1</super>. In this paper we examine how line spacing, "
         "letter spacing and reading width interact when students read academic texts on paper.")
INTRO2 = ("A second motivation concerns the accessibility of scientific literature itself. Journal layouts "
          "are optimised for compactness rather than readability, which often results in long lines, small "
          "type and dense two-column pages (Garcia et al., 2019). Converting such documents into a more "
          "spacious layout is therefore an attractive idea that has been explored before [3].")
PART = ("Forty-two undergraduate students participated in the study. All participants gave informed "
        "consent and received course credit for their participation. Participants were recruited through "
        "the university research pool and had normal or corrected-to-normal vision<super>2</super>.")
PROC = ("Each participant read eight passages in four typographic conditions. Passages were matched for "
        "length and difficulty using a standard readability index. Reading time and comprehension accuracy "
        "were recorded for every passage, and the order of conditions was counterbalanced across participants "
        "(see Miller, 2018, for the procedure).")
RES = ("Reading times were shorter in the spacious condition than in the standard condition. The effect was "
       "most pronounced for participants who reported reading difficulties. Comprehension accuracy did not "
       "differ between conditions, suggesting that the faster reading did not come at the cost of understanding. "
       "Table 1 summarises the main results and Figure 1 shows the distribution of reading times.")
DISC = ("The present findings suggest that simple typographic changes can make academic texts easier to read "
        "for some students. Importantly, the benefits varied considerably between individuals, which argues "
        "against a single recommended format. Tools that let readers choose their own settings may therefore "
        "be more useful than fixed guidelines [1, 2].")


class Chart(Flowable):
    def __init__(self, width, height):
        super().__init__()
        self.width, self.height = width, height

    def draw(self):
        d = Drawing(self.width, self.height)
        d.add(Rect(0, 0, self.width, self.height, strokeColor=colors.black, fillColor=None))
        vals = [30, 55, 80, 45, 65]
        bw = self.width / (len(vals) * 2 + 1)
        for i, v in enumerate(vals):
            d.add(Rect(bw * (2 * i + 1), 8, bw, v * (self.height - 20) / 80,
                       fillColor=colors.HexColor("#4a7ab5"), strokeColor=None))
        d.add(Line(4, 8, self.width - 4, 8))
        d.add(String(self.width / 2 - 20, self.height - 10, "Time (s)", fontSize=6))
        d.drawOn(self.canv, 0, 0)


def paper_story():
    s = []
    s.append(Paragraph("Typography and Reading Speed in Academic Texts", TITLE))
    s.append(Paragraph("Anna de Vries<super>a</super>, Tom Jansen<super>b</super> and Lisa Peters<super>a</super>",
                       AUTH))
    s.append(FrameBreak())
    s.append(Paragraph("Abstract", H1))
    s.append(Paragraph("We studied whether adjustable typography helps students read academic papers. "
                       "Spacing adjustments improved reading speed for some readers.", BODY0))
    s.append(Paragraph("1 Introduction", H1))
    s.append(Paragraph(INTRO, BODY0))
    s.append(Paragraph(INTRO2, BODY))
    s.append(Paragraph("2 Methods", H1))
    s.append(Paragraph("2.1 Participants", H2))
    s.append(Paragraph(PART, BODY0))
    s.append(Paragraph("2.2 Procedure", H2))
    s.append(Paragraph(PROC, BODY0))
    s.append(Paragraph(PROC.replace("Each participant", "In addition, each participant"), BODY))
    s.append(Paragraph("3 Results", H1))
    s.append(Paragraph(RES, BODY0))
    s.append(Chart(7 * cm, 3.2 * cm))
    s.append(Paragraph("Figure 1. Mean reading time per condition.", CAP))
    s.append(Paragraph("Table 1. Reading time and accuracy by condition.", CAP))
    t = Table([["Condition", "Time (s)", "Accuracy"], ["Standard", "61.2", "0.84"], ["Spacious", "55.9", "0.85"],
               ["Wide", "58.4", "0.83"]], colWidths=[2.6 * cm, 2 * cm, 2 * cm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                           ("FONT", (0, 0), (-1, -1), "Times-Roman", 8.5)]))
    s.append(t)
    s.append(Spacer(1, 6))
    s.append(Paragraph("4 Discussion", H1))
    s.append(Paragraph(DISC, BODY0))
    s.append(Paragraph(DISC.replace("The present findings", "Taken together, the findings"), BODY))
    s.append(Paragraph("References", H1))
    for r in ["[1] Garcia, M., Lopez, R., & Chen, L. (2019). Journal layouts and readability. "
              "Reading Research, 12(3), 45-67.",
              "[2] Jones, P., & Brown, K. (2021). Letter spacing and reading. Journal of Typography, 8, 10-19.",
              "[3] Miller, D. (2018). Methods for reading research. Academic Press.",
              "[4] Smith, J. (2020). Dyslexia and typography: a review. Dyslexia Review, 4, 1-22."]:
        s.append(Paragraph(r, REF))
    return s


def make_paper(path: Path) -> None:
    footnotes = {1: "1 Individual differences are discussed in Section 4.",
                 2: "2 Vision was checked with a standard eye chart."}

    def on_page(canv, doc):
        canv.saveState()
        canv.setFont("Times-Italic", 8)
        canv.drawString(2 * cm, A4[1] - 1.2 * cm, "Journal of Reading Studies - Vol. 3")
        canv.drawCentredString(A4[0] / 2, 1.2 * cm, str(doc.page))
        if doc.page == 1:
            y = 2.3 * cm
            canv.line(2 * cm, y + 0.9 * cm, 6 * cm, y + 0.9 * cm)
            for n in (2, 1):
                Paragraph(footnotes[n], FOOT).wrapOn(canv, 8 * cm, 2 * cm)
                p = Paragraph(footnotes[n], FOOT)
                p.wrapOn(canv, 8 * cm, 2 * cm)
                p.drawOn(canv, 2 * cm, y)
                y += 0.4 * cm
        canv.restoreState()

    W, H = A4
    m = 2 * cm
    gutter = 0.8 * cm
    colw = (W - 2 * m - gutter) / 2
    title_h = 3.2 * cm
    first = PageTemplate("first", [Frame(m, H - m - title_h, W - 2 * m, title_h, id="title"),
                                   Frame(m, 3.6 * cm, colw, H - m - title_h - 3.6 * cm, id="c1"),
                                   Frame(m + colw + gutter, 3.6 * cm, colw, H - m - title_h - 3.6 * cm, id="c2")],
                         onPage=on_page)
    later = PageTemplate("later", [Frame(m, m, colw, H - 2 * m - 0.4 * cm, id="l1"),
                                   Frame(m + colw + gutter, m, colw, H - 2 * m - 0.4 * cm, id="l2")],
                         onPage=on_page)
    doc = BaseDocTemplate(str(path), pagesize=A4, pageTemplates=[first, later], title="Typography and Reading",
                          author="A. de Vries")
    story = [NextPageTemplate("later")] + paper_story()
    doc.build(story)


def make_scanned(src: Path, dst: Path, dpi: int = 200) -> None:
    doc = pymupdf.open(src)
    out = pymupdf.open()
    for page in doc:
        pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
        np = out.new_page(width=page.rect.width, height=page.rect.height)
        np.insert_image(np.rect, stream=pix.tobytes("png"))
    out.save(dst)


def main(out_dir: str = "tests/fixtures") -> None:
    d = Path(out_dir)
    d.mkdir(parents=True, exist_ok=True)
    make_paper(d / "sample_paper.pdf")
    make_scanned(d / "sample_paper.pdf", d / "sample_scanned.pdf")
    make_book_spread(d / "sample_book_spread.pdf")
    print(f"Wrote samples to {d}")



# --------------------------------------------------------------------------- book scans

BOOK_TEXT = [
    ("12 THE STATE AND THE FOREST", None),
    (None, "The early modern European state viewed its forests primarily through the fiscal lens of "
           "revenue needs. Other concerns were not entirely absent from official management, but they "
           "rarely shaped the decisions that mattered."),
    (None, "The best way to appreciate how narrow this vision was is to notice what fell outside its field "
           "of vision. Missing were all those trees, bushes, and plants holding little or no potential for "
           "state revenue, and all the uses that local people made of them."),
    ("heading", "Measuring the Forest"),
    (None, "Careful exploitation of the forests was all the more important because the forests were a "
           "source of income that could be planned and taxed. The first attempts at precise measurement "
           "were made by officials who counted trees in sample plots."),
]
BOOK_TEXT_2 = [
    ("The State and the Forest 13", None),
    (None, "Mathematicians then worked from the shape of an ideal tree to tables that predicted the volume "
           "of wood a stand would yield. The result was a forest that could be read like a ledger."),
    (None, "Foresters soon began to replant the forest itself so that it matched the tables. Rows of trees "
           "of one species and one age made counting, harvesting and planning much easier."),
    (None, "This simplified forest was easier to manage for a while, but the losses of the old diversity "
           "became visible only after a generation, when the second rotation of trees began to fail."),
]


def _book_page_image(blocks, dpi=200):
    """Render one book page (14 x 21 cm, single column, indented paragraphs) to a PIL image."""
    from PIL import Image

    buf = io.BytesIO()
    body = ParagraphStyle("b", fontName="Times-Roman", fontSize=11, leading=14.5, firstLineIndent=14,
                          alignment=4)
    head = ParagraphStyle("h", fontName="Times-Italic", fontSize=12, leading=16, spaceBefore=10, spaceAfter=6)
    run = ParagraphStyle("r", fontName="Times-Roman", fontSize=8.5, leading=10, spaceAfter=14)
    story = []
    for kind, text in blocks:
        if text is None:
            story.append(Paragraph(kind, run))
        elif kind == "heading":
            story.append(Paragraph(text, head))
        else:
            story.append(Paragraph(text, body))
    from reportlab.platypus import SimpleDocTemplate

    SimpleDocTemplate(buf, pagesize=(14 * cm, 21 * cm), leftMargin=1.8 * cm, rightMargin=1.8 * cm,
                      topMargin=1.5 * cm, bottomMargin=2 * cm).build(story)
    page = pymupdf.open(stream=buf.getvalue(), filetype="pdf")[0]
    pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")


def make_book_spread(dst: Path, dpi: int = 200, skew: float = 1.2, rotation: int = 90) -> None:
    """A photocopied book spread: two pages side by side, tilted, with gutter shadow and dark edges,
    stored as two image tiles on a PDF page that is rotated by 90 degrees."""
    import numpy as np
    from PIL import Image

    left = _book_page_image(BOOK_TEXT, dpi).rotate(skew, fillcolor=255, expand=False)
    right = _book_page_image(BOOK_TEXT_2, dpi).rotate(-skew * 0.7, fillcolor=255, expand=False)
    w, h = left.width + right.width, max(left.height, right.height)
    spread = Image.new("L", (w, h), 255)
    spread.paste(left, (0, 0))
    spread.paste(right, (left.width, 0))
    a = np.asarray(spread, dtype=np.float32)
    x = np.arange(w, dtype=np.float32)
    gutter = 1 - 0.55 * np.exp(-((x - left.width) / (w * 0.03)) ** 2)  # shadow in the fold
    paper = 0.9 - 0.08 * (x / w)  # greyish, unevenly lit paper
    a = a * paper[None, :] * gutter[None, :]
    a[:, : int(w * 0.012)] = 25  # dark scanner edges
    a[:, -int(w * 0.012):] = 25
    a[: int(h * 0.01), :] = 30
    spread = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    # store rotated 90 degrees (as copiers often do) in two tiles
    stored = spread.rotate(90, expand=True)
    out = pymupdf.open()
    pw, ph = stored.width * 72 / dpi, stored.height * 72 / dpi
    page = out.new_page(width=pw, height=ph)
    half = stored.height // 2
    for i, box in enumerate(((0, 0, stored.width, half), (0, half, stored.width, stored.height))):
        tile = stored.crop(box)
        b = io.BytesIO()
        tile.save(b, format="PNG")
        rect = pymupdf.Rect(0, box[1] * 72 / dpi, pw, box[3] * 72 / dpi)
        page.insert_image(rect, stream=b.getvalue())
    page.set_rotation(rotation)  # 90 shows it upright; 270 shows it upside down
    out.save(dst)


def make_scan_with_text_layer(src_scan: Path, dst: Path, text_pdf: Path) -> None:
    """Add an invisible text layer (like a copier's OCR) to a scanned PDF."""
    scan = pymupdf.open(src_scan)
    text = pymupdf.open(text_pdf)
    for sp, tp in zip(scan, text):
        for x0, y0, x1, y1, t, *_ in tp.get_text("words"):
            unit = pymupdf.get_text_length(t, fontname="helv", fontsize=1) or 1
            size = max(3, min((y1 - y0) * 0.8, (x1 - x0) / unit * 0.95))  # fit the word's box
            sp.insert_text((x0, y1 - 2), t, fontsize=size, render_mode=3)
    scan.save(dst)


if __name__ == "__main__":
    main(*sys.argv[1:])
