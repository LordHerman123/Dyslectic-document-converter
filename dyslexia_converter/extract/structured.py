"""Reading Word (.docx) and EPUB files.

These formats say what every part is (a heading of level 2, a bulleted list, a table), so their structure is read
directly instead of guessed from positions on a page as for a PDF. The result is the same :class:`Document` the PDF
reader and structure detector make, so everything after it (layout, read aloud, focus mode, exports) works the same.

The app shows the original next to the converted version as pages: :func:`original_pdf` lays the file out as a PDF
(with PyMuPDF), and every block is placed on the page of that PDF where its text is, so the two views follow each
other. The source file is only read, never written.
"""
from __future__ import annotations

import io
import posixpath
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree as ET

from ..model import Block, BlockKind, Document, ImageData, PageInfo, StyleRange, TableData

STRUCTURED_TYPES = (".docx", ".epub")


def is_structured(path: str | Path) -> bool:
    """Whether the file is a Word or EPUB file (read by this module) rather than a PDF."""
    return Path(str(path)).suffix.lower() in STRUCTURED_TYPES


def read_structured(path: str | Path) -> tuple[Document, bytes]:
    """The structured document of a Word or EPUB file, and the original laid out as a PDF (for the Original view)."""
    path = str(path)
    doc = _read_docx(path) if path.lower().endswith(".docx") else _read_epub(path)
    pdf = original_pdf(path)
    _place_on_pages(doc, pdf)
    return doc, pdf


def original_pdf(path: str) -> bytes:
    """The Word or EPUB file laid out as pages (PDF), as a reader would see it."""
    import pymupdf

    pymupdf.TOOLS.mupdf_display_errors(False)  # books often have CSS MuPDF does not know; it is skipped quietly
    try:
        with pymupdf.open(path) as src:
            return src.convert_to_pdf()
    finally:
        pymupdf.TOOLS.mupdf_display_errors(True)


# ----------------------------------------------------------------------------- building blocks
class _Builder:
    """Collects blocks with running ids (b1, b2, ...), the same as the structure detector."""

    def __init__(self):
        self.blocks: list[Block] = []

    def add(self, kind: BlockKind, text: str = "", level: int = 0, styles: Optional[list] = None, **kw) -> None:
        text, styles = _tidy(text, styles or [])
        if not text and kind not in (BlockKind.IMAGE, BlockKind.TABLE):
            return
        self.blocks.append(Block(id=f"b{len(self.blocks) + 1}", kind=kind, text=text, level=level,
                                 styles=styles, **kw))


def _tidy(text: str, styles: list[StyleRange]) -> tuple[str, list[StyleRange]]:
    """Text with runs of white space made one space and the ends trimmed, the style ranges moved along."""
    out, keep = [], []  # keep[i]: position in the new text of old character i
    prev_space = True
    for ch in text.replace("­", ""):
        space = ch.isspace() and ch != " "
        if space and prev_space:
            keep.append(len(out))
            continue
        keep.append(len(out))
        out.append(" " if space else ch)
        prev_space = space
    keep.append(len(out))
    new = "".join(out)
    trail = len(new) - len(new.rstrip())
    new = new.rstrip()
    moved = []
    for s in styles:
        a, b = keep[min(s.start, len(keep) - 1)], keep[min(s.end, len(keep) - 1)]
        b = min(b, len(new))
        if b > a:
            moved.append(s.moved(0, a, b))
    del trail
    return new, moved


def _picture(data: bytes, name: str) -> Optional[ImageData]:
    """A picture from the file as PNG or JPEG (other formats are turned into PNG); None when it cannot be read."""
    from PIL import Image

    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        return None
    if im.width < 8 or im.height < 8:  # spacers and tracking pixels
        return None
    if im.format == "JPEG":
        return ImageData(data, "jpeg", im.width, im.height)
    if im.format != "PNG":
        out = io.BytesIO()
        im.convert("RGBA" if "A" in im.getbands() else "RGB").save(out, "PNG")
        data = out.getvalue()
    return ImageData(data, "png", im.width, im.height)


# ----------------------------------------------------------------------------- Word
_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _read_docx(path: str) -> Document:
    from docx import Document as Docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    d = Docx(path)
    b = _Builder()
    formats = _numbering_formats(d)
    counters: dict[tuple, int] = {}
    body = d.element.body
    for el in body.iterchildren():
        if el.tag == _W + "p":
            _docx_paragraph(Paragraph(el, d), d, b, formats, counters)
        elif el.tag == _W + "tbl":
            rows = [[cell.text.strip() for cell in row.cells] for row in Table(el, d).rows]
            rows = [r for r in rows if any(r)]
            if rows:
                b.add(BlockKind.TABLE, "", table=TableData(rows=rows))
    props = d.core_properties
    return Document(source_path=path, blocks=b.blocks, title=(props.title or "").strip(),
                    author=(props.author or "").strip(), language=(props.language or "")[:2].lower() or "en")


def _numbering_formats(d) -> dict[tuple[str, int], str]:
    """For every list (numId) and depth, how it is numbered: "bullet", "decimal", "lowerLetter", ..."""
    out: dict[tuple[str, int], str] = {}
    try:
        numbering = d.part.numbering_part.element
    except Exception:
        return out
    abstract = {}
    for a in numbering.findall(_W + "abstractNum"):
        levels = {}
        for lvl in a.findall(_W + "lvl"):
            fmt = lvl.find(_W + "numFmt")
            levels[int(lvl.get(_W + "ilvl", "0"))] = fmt.get(_W + "val") if fmt is not None else "decimal"
        abstract[a.get(_W + "abstractNumId")] = levels
    for num in numbering.findall(_W + "num"):
        ref = num.find(_W + "abstractNumId")
        if ref is not None:
            for ilvl, fmt in abstract.get(ref.get(_W + "val"), {}).items():
                out[(num.get(_W + "numId"), ilvl)] = fmt
    return out


def _docx_paragraph(p, d, b: _Builder, formats: dict, counters: dict) -> None:
    style = (p.style.name if p.style is not None else "") or ""
    text, styles = "", []
    for run in p.runs:
        t = run.text
        if t:
            f = run.font
            if run.bold or run.italic or f.superscript or f.subscript:
                styles.append(StyleRange(len(text), len(text) + len(t), bold=bool(run.bold),
                                         italic=bool(run.italic), superscript=bool(f.superscript),
                                         subscript=bool(f.subscript)))
            text += t
    for pic in _docx_pictures(p, d):
        b.add(BlockKind.IMAGE, "", image=pic)
    low = style.lower()
    heading = re.match(r"heading (\d)", low)
    if low == "title":
        b.add(BlockKind.TITLE, text, styles=styles)
    elif heading:
        b.add(BlockKind.HEADING, text, level=int(heading.group(1)), styles=styles)
    elif low == "subtitle":
        b.add(BlockKind.HEADING, text, level=2, styles=styles)
    elif "quote" in low:
        b.add(BlockKind.QUOTE, text, styles=styles)
    elif low == "caption":
        b.add(BlockKind.CAPTION, text, styles=styles)
    else:
        num = p._p.pPr.numPr if p._p.pPr is not None else None
        if num is None and p.style is not None:  # list styles ("List Number") carry the numbering themselves
            ppr = p.style.element.pPr
            num = ppr.numPr if ppr is not None else None
        if num is not None and num.numId is not None and text.strip():
            num_id = str(num.numId.val)
            ilvl = int(num.ilvl.val) if num.ilvl is not None else 0
            fmt = formats.get((num_id, ilvl), "bullet" if "bullet" in low else "decimal")
            marker = _list_marker(fmt, num_id, ilvl, counters)
            shift = len(marker)
            b.add(BlockKind.LIST_ITEM, marker + text, level=ilvl,
                  styles=[s.moved(shift) for s in styles])
        elif "list" in low and text.strip():  # a list style without numbering definitions
            marker = _list_marker("decimal" if "number" in low else "bullet", style, 0, counters)
            b.add(BlockKind.LIST_ITEM, marker + text, level=0, styles=[s.moved(len(marker)) for s in styles])
        else:
            b.add(BlockKind.PARAGRAPH, text, styles=styles)


def _list_marker(fmt: str, num_id: str, ilvl: int, counters: dict) -> str:
    """The marker in front of a list item ("• ", "3. ", "c) "), counting per list and depth."""
    for key in [k for k in counters if k[0] == num_id and k[1] > ilvl]:
        del counters[key]  # a deeper list starts again after its parent item
    if fmt in ("bullet", "none"):
        return "• "
    n = counters.get((num_id, ilvl), 0) + 1
    counters[(num_id, ilvl)] = n
    if fmt == "lowerLetter":
        return f"{chr(96 + (n - 1) % 26 + 1)}) "
    if fmt == "upperLetter":
        return f"{chr(64 + (n - 1) % 26 + 1)}. "
    if fmt in ("lowerRoman", "upperRoman"):
        r = _roman(n)
        return f"{r if fmt == 'upperRoman' else r.lower()}. "
    return f"{n}. "


def _roman(n: int) -> str:
    out = ""
    for v, s in ((1000, "M"), (900, "CM"), (500, "D"), (400, "CD"), (100, "C"), (90, "XC"), (50, "L"),
                 (40, "XL"), (10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I")):
        while n >= v:
            out, n = out + s, n - v
    return out


def _docx_pictures(p, d) -> list[ImageData]:
    """The pictures placed in a paragraph."""
    out = []
    for blip in p._p.iter("{http://schemas.openxmlformats.org/drawingml/2006/main}blip"):
        rid = blip.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
        part = d.part.related_parts.get(rid) if rid else None
        pic = _picture(part.blob, str(part.partname)) if part is not None else None
        if pic:
            out.append(pic)
    return out


# ----------------------------------------------------------------------------- EPUB
_BLOCK_TAGS = {"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "figcaption", "caption", "dt",
               "dd", "pre", "td", "th", "aside", "section", "article", "header", "footer", "table", "tr", "ul", "ol",
               "figure", "br", "hr", "body", "nav"}
_SKIP_TAGS = {"script", "style", "head", "title", "svg", "math", "noscript"}


def _read_epub(path: str) -> Document:
    z = zipfile.ZipFile(path)
    opf_path = _opf_path(z)
    opf = ET.fromstring(z.read(opf_path))
    ns = {"opf": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/"}
    base = posixpath.dirname(opf_path)
    items = {}
    for it in opf.iterfind(".//opf:manifest/opf:item", ns):
        items[it.get("id")] = (posixpath.normpath(posixpath.join(base, it.get("href", ""))),
                               it.get("media-type", ""), it.get("properties", "") or "")
    b = _Builder()
    for ref in opf.iterfind(".//opf:spine/opf:itemref", ns):
        href, media, props = items.get(ref.get("idref"), ("", "", ""))
        if not href or "nav" in props.split() or "html" not in media:
            continue
        try:
            html = z.read(href).decode("utf-8", errors="replace")
        except KeyError:
            continue
        _EpubPage(z, href, b).feed(html)
    title = opf.findtext(".//dc:title", "", ns).strip()
    author = opf.findtext(".//dc:creator", "", ns).strip()
    lang = (opf.findtext(".//dc:language", "", ns) or "en")[:2].lower()
    return Document(source_path=path, blocks=b.blocks, title=title, author=author, language=lang)


def _opf_path(z: zipfile.ZipFile) -> str:
    """Where the package file (the list of the book's parts, in reading order) is."""
    root = ET.fromstring(z.read("META-INF/container.xml"))
    for el in root.iter():
        if el.tag.endswith("rootfile") and el.get("full-path"):
            return el.get("full-path")
    raise ValueError("This EPUB has no package file")


class _EpubPage(HTMLParser):
    """Turns one XHTML part of a book into blocks: headings, paragraphs, list items, quotes, tables, pictures."""

    def __init__(self, z: zipfile.ZipFile, href: str, b: _Builder):
        super().__init__(convert_charrefs=True)
        self.z, self.dir, self.b = z, posixpath.dirname(href), b
        self.text, self.styles = "", []
        self.kind, self.level = BlockKind.PARAGRAPH, 0
        self.inline: list[dict] = []  # open inline styles with where they started
        self.skip = 0  # inside <script>, <style>, page-break markers...
        self.lists: list[list] = []  # open lists: [ordered, counter]
        self.quote = 0
        self.note = 0
        self.table: Optional[list] = None
        self.row: Optional[list] = None
        self.cell: Optional[str] = None
        self.hidden: list[str] = []  # tags whose content is skipped (their names, to find the end)

    # the block being collected ----------------------------------------------------------------
    def _flush(self) -> None:
        if self.table is not None and self.cell is not None:
            return  # table cells are collected into the table
        text, styles = self.text, self.styles
        self.text, self.styles = "", []
        if not text.strip():
            return
        kind = self.kind
        if kind == BlockKind.PARAGRAPH and self.note:
            kind = BlockKind.FOOTNOTE
        elif kind == BlockKind.PARAGRAPH and self.quote:
            kind = BlockKind.QUOTE
        self.b.add(kind, text, level=self.level, styles=styles)
        self.kind, self.level = BlockKind.PARAGRAPH, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        kind_attr = (a.get("epub:type", "") + " " + a.get("role", "")).lower()
        if self.skip or tag in _SKIP_TAGS or "pagebreak" in kind_attr:
            if tag not in ("br", "img", "hr"):  # an empty tag has no end tag to wait for
                self.skip += 1
                self.hidden.append(tag)
            return
        if tag in _BLOCK_TAGS:
            self._flush()
        if re.fullmatch(r"h[1-6]", tag):
            self.kind, self.level = BlockKind.HEADING, int(tag[1])
        elif tag in ("ul", "ol"):
            self.lists.append([tag == "ol", int(a.get("start", "1") or 1) - 1])
        elif tag == "li":
            self.kind, self.level = BlockKind.LIST_ITEM, max(0, len(self.lists) - 1)
            if self.lists and self.lists[-1][0]:
                self.lists[-1][1] += 1
                self.text = f"{self.lists[-1][1]}. "
            else:
                self.text = "• "
        elif tag == "blockquote":
            self.quote += 1
        elif tag in ("aside",) and ("footnote" in kind_attr or "endnote" in kind_attr or "note" in kind_attr):
            self.note += 1
        elif tag in ("figcaption", "caption"):
            self.kind = BlockKind.CAPTION
        elif tag == "table":
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = ""
        elif tag == "img":
            self._image(a.get("src", ""))
        elif tag in ("b", "strong", "i", "em", "sup", "sub"):
            self.inline.append({"tag": tag, "start": len(self.text)})

    def handle_endtag(self, tag):
        if self.skip:
            if self.hidden and self.hidden[-1] == tag:
                self.hidden.pop()
                self.skip -= 1
            return
        if tag in ("b", "strong", "i", "em", "sup", "sub"):
            for k in range(len(self.inline) - 1, -1, -1):
                if self.inline[k]["tag"] == tag:
                    start = self.inline.pop(k)["start"]
                    if len(self.text) > start:
                        self.styles.append(StyleRange(start, len(self.text), bold=tag in ("b", "strong"),
                                                      italic=tag in ("i", "em"), superscript=tag == "sup",
                                                      subscript=tag == "sub"))
                    break
            return
        if tag in ("td", "th") and self.row is not None and self.cell is not None:
            self.row.append(re.sub(r"\s+", " ", self.cell).strip())
            self.cell = None
            return
        if tag == "tr" and self.table is not None and self.row is not None:
            if any(self.row):
                self.table.append(self.row)
            self.row = None
            return
        if tag == "table" and self.table is not None:
            rows, self.table = self.table, None
            if rows:
                width = max(len(r) for r in rows)
                self.b.add(BlockKind.TABLE, "", table=TableData(rows=[r + [""] * (width - len(r)) for r in rows]))
            return
        if tag in _BLOCK_TAGS:
            self._flush()
        if tag in ("ul", "ol") and self.lists:
            self.lists.pop()
        elif tag == "blockquote" and self.quote:
            self.quote -= 1
        elif tag == "aside" and self.note:
            self.note -= 1

    def handle_data(self, data):
        if self.skip:
            return
        if self.cell is not None:
            self.cell += data
        else:
            self.text += data

    def _image(self, src: str) -> None:
        if not src or src.startswith(("http:", "https:", "data:")):
            return
        self._flush()
        name = posixpath.normpath(posixpath.join(self.dir, src.split("#")[0]))
        try:
            pic = _picture(self.z.read(name), name)
        except KeyError:
            return
        if pic:
            self.b.add(BlockKind.IMAGE, "", image=pic)


# ----------------------------------------------------------------------------- pages of the original
def _norm(text: str) -> str:
    return re.sub(r"[^\w]+", "", text.lower())


def _place_on_pages(doc: Document, pdf: bytes) -> None:
    """Give every block the page of the laid-out original where its text starts, so the Original and the
    converted view follow each other (blocks without text, like pictures, take the page of the block before)."""
    import pymupdf

    with pymupdf.open("pdf", pdf) as od:
        doc.pages = [PageInfo(number=i, width=p.rect.width, height=p.rect.height, kind="text", source_page=i,
                              text_source="pdf") for i, p in enumerate(od)]
        texts = [_norm(p.get_text()) for p in od]
    page, pos = 0, 0  # where the text before was found: the next block is looked for after it
    for b in doc.blocks:
        probe = _norm(b.text)[:40] if b.text else ""
        if b.kind == BlockKind.TABLE and b.table and b.table.rows:
            probe = _norm(" ".join(b.table.rows[0]))[:40]
        if len(probe) >= 6 and texts:
            at = texts[page].find(probe, pos)
            if at >= 0:
                pos = at + len(probe)
            else:
                for k in list(range(page + 1, min(len(texts), page + 4))) + list(range(page + 4, len(texts))):
                    at = texts[k].find(probe)
                    if at >= 0:
                        page, pos = k, at + len(probe)
                        break
        b.page = page
        if doc.pages:
            p = doc.pages[min(page, len(doc.pages) - 1)]
            b.bbox = (0.0, 0.0, p.width, p.height)
