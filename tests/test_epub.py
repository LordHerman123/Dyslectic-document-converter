"""EPUB export: a valid, reflowable book with the whole text, working links, described images."""
import io
import re
import zipfile
import xml.etree.ElementTree as ET

import pymupdf
import pytest

from dyslexia_converter import pipeline
from dyslexia_converter.model import Block, BlockKind, Document, ImageData, TableData
from dyslexia_converter.render import epub_writer
from dyslexia_converter.render.compose import compose
from dyslexia_converter.settings import PRESETS, FormatSettings

OPF = "{http://www.idpf.org/2007/opf}"


def check_package(data: bytes) -> zipfile.ZipFile:
    """What e-readers rely on: the mimetype entry, the container, a manifest that lists every file,
    well-formed pages, links and images that exist, and a description on every image."""
    z = zipfile.ZipFile(io.BytesIO(data))
    first = z.infolist()[0]
    assert first.filename == "mimetype" and first.compress_type == zipfile.ZIP_STORED
    assert z.read("mimetype") == b"application/epub+zip"
    assert b'full-path="OEBPS/content.opf"' in z.read("META-INF/container.xml")
    opf = ET.fromstring(z.read("OEBPS/content.opf"))
    listed = {"OEBPS/" + i.get("href") for i in opf.iter(f"{OPF}item")}
    files = {n for n in z.namelist() if n.startswith("OEBPS/") and not n.endswith("content.opf")}
    assert listed == files
    ids: dict[str, set] = {}
    pages = [n for n in files if n.endswith(".xhtml")]
    for n in pages + ["OEBPS/toc.ncx"]:
        ET.fromstring(z.read(n))  # well-formed XML
    for n in pages:
        text = z.read(n).decode("utf-8")
        ids[n.split("/")[-1]] = set(re.findall(r' id="([^"]+)"', text))
    for n in pages:
        text = z.read(n).decode("utf-8")
        for href in re.findall(r'<a [^>]*href="([^"]+)"', text):
            target, _, anchor = href.partition("#")
            page = target.split("/")[-1] or n.split("/")[-1]
            assert page in ids, href
            assert not anchor or anchor in ids[page], href
        for tag in re.findall(r"<img [^>]*>", text):
            src = re.search(r'src="([^"]+)"', tag).group(1)
            assert "OEBPS/" + src.replace("../", "") in files, src
            alt = re.search(r'alt="([^"]*)"', tag)
            assert alt and alt.group(1).strip(), tag  # every picture is described
    return z


@pytest.mark.parametrize("preset", ["Standard", "Spacious"])
def test_epub_is_valid_and_keeps_every_word(paper, preset):
    session = pipeline.load(paper)
    s = PRESETS[preset].copy(bold_word_start=False, move_footnotes=False, move_citations=False)
    data = session.export("epub", s)
    check_package(data)
    book = " ".join(epub_writer.chapter_texts(data))
    norm = lambda t: re.sub(r"\s+", " ", t.replace("­", "")).strip()  # noqa: E731
    for b in session.document.blocks:
        if b.kind in (BlockKind.PARAGRAPH, BlockKind.HEADING):
            assert norm(b.text) in norm(book), b.text[:60]


def test_epub_links_notes_and_citations(paper):
    session = pipeline.load(paper)
    data = session.export("epub", FormatSettings(move_citations=True, move_footnotes=True, bold_word_start=True))
    z = check_package(data)
    body = "".join(z.read(n).decode() for n in z.namelist() if n.startswith("OEBPS/text/"))
    assert 'epub:type="noteref"' in body and "<b>" in body
    nav = z.read("OEBPS/nav.xhtml").decode()
    assert 'epub:type="toc"' in nav and nav.count("<li>") >= 3


def test_only_freely_licensed_fonts_are_embedded(paper, monkeypatch, tmp_path):
    from dyslexia_converter import fonts
    from dyslexia_converter.render import epub_writer as ew

    session = pipeline.load(paper)
    data = session.export("epub", FormatSettings(font="OpenDyslexic"))
    assert any(n.endswith("OpenDyslexic-Regular.ttf") for n in zipfile.ZipFile(io.BytesIO(data)).namelist())
    # a font found on the computer (like Verdana from Windows) is named in the style, never copied
    system_font = tmp_path / "verdana.ttf"
    system_font.write_bytes(b"not really a font")
    fam = fonts.FontFamily("Verdana", str(system_font), str(system_font), str(system_font), str(system_font))
    monkeypatch.setattr(ew, "get_family", lambda name: fam)
    data = session.export("epub", FormatSettings(font="Verdana"))
    z = check_package(data)
    assert not any("fonts/" in n for n in z.namelist())
    assert "Verdana" in z.read("OEBPS/style.css").decode()


def test_epub_odd_documents():
    s = FormatSettings()
    # nothing at all
    empty = epub_writer.build_epub(compose(Document(blocks=[], pages=[], source_path="x.pdf"), s), s)
    check_package(empty)
    # control characters, markup-like text, a formula, a table and a table that is only a picture
    png = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 40, 16), False)
    png.clear_with(255)
    eq = ImageData(png.tobytes("png"), "png", 40, 16, kind="equation", alt="", text_size=10)
    pic = ImageData(png.tobytes("png"), "png", 40, 16)
    blocks = [
        Block("h", BlockKind.HEADING, "Results & <discussion>", 0, (0, 0, 100, 10), level=1),
        Block("p", BlockKind.PARAGRAPH, "Odd \x0b text with \"quotes\" & <tags> \x00 inside.", 0, (0, 20, 100, 30)),
        Block("e", BlockKind.IMAGE, "", 0, (0, 40, 40, 56), image=eq),
        Block("t", BlockKind.TABLE, "", 0, (0, 60, 100, 90), table=TableData([["a", "b"], ["1", "2", "3"]])),
        Block("u", BlockKind.TABLE, "", 0, (0, 60, 100, 90), table=TableData([], fallback_image=pic, reliable=False)),
    ]
    data = epub_writer.build_epub(compose(Document(blocks=blocks, pages=[], source_path="x.pdf"), s), s, "T & T")
    z = check_package(data)
    text = " ".join(epub_writer.chapter_texts(data))
    assert "Results & <discussion>" in text and "\x0b" not in text and "\x00" not in text
    assert "<th>a</th>" in "".join(z.read(n).decode() for n in z.namelist() if n.endswith(".xhtml"))


@pytest.mark.parametrize("levels,expect", [
    ([1, 2, 2, 1, 3], "<ol><li>0<ol><li>1</li><li>2</li></ol></li><li>3<ol><li>4</li></ol></li></ol>"),
    ([3, 1, 2, 3, 2], "<ol><li>0</li><li>1<ol><li>2<ol><li>3</li></ol></li><li>4</li></ol></li></ol>"),
    ([1, 4, 4, 2, 1], "<ol><li>0<ol><li>1</li><li>2</li><li>3</li></ol></li><li>4</li></ol>"),
    ([], ""),
])
def test_table_of_contents_nesting(levels, expect):
    html = epub_writer._nested_list([(lv, str(i)) for i, lv in enumerate(levels)])
    assert html == expect
    if html:
        ET.fromstring(f"<r>{html}</r>")


def test_cli_writes_epub(paper, tmp_path):
    from dyslexia_converter import cli

    out = tmp_path / "book.epub"
    assert cli.main([str(paper), "-o", str(out), "-f", "epub"]) == 0
    check_package(out.read_bytes())
