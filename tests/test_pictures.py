"""A picture as large as the reader makes it: kept per picture, used by every export, and noted where it is drawn so
focus mode can pick it."""
import io
import zipfile

from PIL import Image as PILImage, ImageDraw

from dyslexia_converter import pipeline
from dyslexia_converter.model import Block, BlockKind, Document, ImageData, PageInfo, TableData
from dyslexia_converter.render.compose import compose
from dyslexia_converter.settings import FormatSettings
from dyslexia_converter.transform.spelling import CustomWords

TEXT = "The early state viewed its forests through the fiscal lens of revenue needs. " * 3


def picture(w: int, h: int, colour: str = "steelblue") -> ImageData:
    """A small chart-like picture."""
    im = PILImage.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    d.rectangle((w // 8, h // 3, w // 3, h - 10), fill=colour)
    d.rectangle((w // 2, h // 5, w * 3 // 4, h - 10), fill=colour)
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return ImageData(buf.getvalue(), "png", w, h, kind="figure")


def session_with(blocks: list[Block], tmp_path) -> pipeline.Session:
    doc = Document("x.pdf", pages=[PageInfo(0, 595, 842, "text")], blocks=blocks)
    return pipeline.Session(doc, CustomWords(tmp_path / "words.txt"))


def figure_doc(tmp_path, img: ImageData, width_pt: float = 120) -> pipeline.Session:
    return session_with([Block("p1", BlockKind.PARAGRAPH, TEXT, page=0),
                         Block("f1", BlockKind.IMAGE, page=0, bbox=(100, 300, 100 + width_pt, 400), image=img),
                         Block("c1", BlockKind.CAPTION, "Figure 1. Trees counted per plot.", page=0),
                         Block("p2", BlockKind.PARAGRAPH, TEXT, page=0)], tmp_path)


def test_a_picture_is_named_by_what_it_shows():
    a, b = picture(400, 300), picture(400, 300)
    assert a.key == b.key and len(a.key) == 16
    assert picture(400, 300, "darkred").key != a.key


def test_the_reader_makes_a_picture_larger_and_back_to_automatic(tmp_path):
    img = picture(400, 300)
    session = figure_doc(tmp_path, img)
    settings = FormatSettings()
    session.export("pdf", settings)
    [(page, x0, y0, x1, y1, key, share)] = session.picture_marks
    assert key == img.key and 0.55 < share < 0.65  # automatic: 60 % of the column for a small figure
    automatic = x1 - x0
    assert abs((y1 - y0) - automatic * 300 / 400) < 0.5  # drawn without stretching

    session.set_picture_size(img.key, 1.0)
    session.export("pdf", settings)
    [(_, a0, b0, a1, b1, _, share)] = session.picture_marks
    assert share == 1.0 and abs((a1 - a0) - automatic / 0.6) < 1.0
    assert abs((b1 - b0) - (a1 - a0) * 300 / 400) < 0.5

    session.set_picture_size(img.key, 0.05)  # never smaller than a fifth of the column
    session.export("pdf", settings)
    assert session.picture_sizes[img.key] == 0.2 and session.picture_marks[0][6] == 0.2

    session.set_picture_size(img.key, 0)  # back to the size the converter chose
    session.export("pdf", settings)
    assert session.picture_sizes == {} and abs((session.picture_marks[0][3] - session.picture_marks[0][1])
                                                - automatic) < 0.01


def test_a_tall_picture_grows_only_as_far_as_a_page_allows(tmp_path):
    img = picture(300, 1200)
    session = figure_doc(tmp_path, img)
    settings = FormatSettings()
    session.export("pdf", settings)
    [(_, _, y0, _, y1, _, _)] = session.picture_marks
    session.set_picture_size(img.key, 1.0)
    session.export("pdf", settings)
    [(_, _, b0, _, b1, _, share)] = session.picture_marks
    assert b1 - b0 > y1 - y0  # larger than the automatic size (at most 70 % of the page) ...
    assert share < 1.0 and b1 - b0 < 842 * 0.9  # ... but never higher than the page's text area


def test_a_table_shown_as_its_picture_can_be_resized(tmp_path):
    img = picture(500, 200, "grey")
    table = TableData(rows=[["a", "b"], ["1", "2"]], fallback_image=img, reliable=False)
    session = session_with([Block("p1", BlockKind.PARAGRAPH, TEXT, page=0),
                            Block("t1", BlockKind.TABLE, page=0, bbox=(100, 300, 250, 360), table=table)], tmp_path)
    session.set_picture_size(img.key, 0.9)
    session.export("pdf", FormatSettings())
    [(_, _, _, _, _, key, share)] = session.picture_marks
    assert key == img.key and share == 0.9


def test_word_and_epub_use_the_size_the_reader_chose(tmp_path):
    img = picture(400, 300)
    session = figure_doc(tmp_path, img)
    settings = FormatSettings()
    from docx import Document as Docx

    def docx_width() -> int:
        return Docx(io.BytesIO(session.export("docx", settings))).inline_shapes[0].width

    def epub_img() -> str:
        with zipfile.ZipFile(io.BytesIO(session.export("epub", settings))) as z:
            page = next(z.read(n).decode() for n in z.namelist() if n.endswith(".xhtml") and b"<figure" in z.read(n))
        return page[page.index("<img"):page.index("/>", page.index("<img"))]

    before = docx_width()
    assert "style=" not in epub_img()
    session.set_picture_size(img.key, 1.0)
    assert docx_width() > before
    assert 'style="width:100%"' in epub_img()


def test_only_pictures_the_reader_sized_change(tmp_path):
    """Without a chosen size the composed document is exactly as before."""
    img = picture(400, 300)
    session = figure_doc(tmp_path, img)
    settings = FormatSettings()
    items = compose(session.view(), settings).items
    assert [it.size for it in items if it.kind == "image"] == [0.0]
    sized = compose(session.view(), settings, picture_sizes={img.key: 0.8}).items
    assert [it.size for it in sized if it.kind == "image"] == [0.8]
