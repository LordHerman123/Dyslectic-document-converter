"""Book scans and photocopies: spreads, skew, shadows, borders, rotation, scanner text layers."""
import numpy as np
import pymupdf
import pytest
from PIL import Image, ImageDraw

from conftest import needs_tesseract
from dyslexia_converter import pipeline
from dyslexia_converter.extract.pdf_reader import classify_page, image_coverage
from dyslexia_converter.extract.scan import (binarize, clear_edge_blobs, estimate_skew, find_gutter,
                                             flatten_illumination)
from dyslexia_converter.model import BlockKind


def text_page(w=800, h=1100, lines=30, x0=80, angle=0.0):
    img = Image.new("L", (w, h), 255)
    d = ImageDraw.Draw(img)
    for i in range(lines):
        y = 80 + i * 30
        d.rectangle([x0, y, w - 80, y + 12], fill=0)  # a "line of text"
    return img.rotate(angle, fillcolor=255)


def test_skew_is_estimated():
    for angle in (-2.0, -0.7, 0.0, 1.3):
        ink = binarize(np.asarray(text_page(angle=angle), dtype=np.float32))
        assert estimate_skew(ink) == pytest.approx(angle, abs=0.25)


def test_gutter_found_only_on_spreads():
    left, right = text_page(), text_page()
    spread = Image.new("L", (1600, 1100), 255)
    spread.paste(left, (0, 0))
    spread.paste(right, (800, 0))
    assert 700 < find_gutter(binarize(np.asarray(spread, dtype=np.float32))) < 900
    assert find_gutter(binarize(np.asarray(text_page(), dtype=np.float32))) is None


def test_shadow_flattening_and_border_removal():
    page = np.asarray(text_page(), dtype=np.float32)
    x = np.arange(page.shape[1], dtype=np.float32)
    shaded = page * (1 - 0.6 * np.exp(-((x - 780) / 150) ** 2))[None, :]  # gutter shadow
    shaded[:, :20] = 20  # scanner border
    flat = flatten_illumination(shaded)
    paper = flat[5:60, 700:790]  # blank paper inside the shadow
    assert paper.mean() > 230
    ink = clear_edge_blobs(binarize(flat))
    assert not ink[:, :10].any()


def test_tiled_rotated_scan_is_classified_as_scan(samples):
    page = pymupdf.open(samples / "book_spread.pdf")[0]
    assert page.rotation == 90 and len(page.get_images()) == 2
    assert image_coverage(page) > 0.9
    assert classify_page(page) == "scanned"


@needs_tesseract
@pytest.mark.parametrize("name", ["book_spread.pdf", "book_spread_upside_down.pdf"])
def test_book_spread_is_split_straightened_and_read(samples, name):
    doc = pipeline.load(samples / name).document
    assert [p.side for p in doc.pages] == ["left", "right"]
    assert doc.pages[0].skew == pytest.approx(1.2, abs=0.3)
    texts = [b.text for b in doc.blocks]
    first = next(i for i, t in enumerate(texts) if t.startswith("The early modern European state"))
    later = next(i for i, t in enumerate(texts) if t.startswith("Mathematicians then worked"))
    assert first < later  # left page before right page
    assert any(b.kind == BlockKind.HEADING and b.text == "Measuring the Forest" for b in doc.blocks)
    assert not any(b.kind == BlockKind.IMAGE for b in doc.blocks)  # shadows/borders are not figures
    joined = " ".join(texts)
    assert "counted trees in sample plots." in joined


def test_scanner_text_layer_is_used_without_ocr(samples):
    session = pipeline.load(samples / "scan_with_text_layer.pdf", use_ocr=False)
    doc = session.document
    assert doc.pdf_type == "scanned" and doc.ocr_used
    assert any("text the scanner stored" in w for w in doc.warnings)
    text = " ".join(b.text for b in doc.blocks)
    assert "Reading difficulties affect a substantial proportion" in text


def test_rotated_text_pdf_is_read(paper, tmp_path):
    """Text positions on /Rotate pages must be mapped to the displayed page (they used to be skipped)."""
    rotated = tmp_path / "rotated.pdf"
    d = pymupdf.open(paper)
    for page in d:
        page.set_rotation(90)
    d.save(rotated)
    doc = pipeline.load(rotated).document
    text = " ".join(b.text for b in doc.blocks)
    assert "Reading difficulties affect a substantial proportion" in text
    assert any(b.kind == BlockKind.HEADING and b.text == "2.1 Participants" for b in doc.blocks)


def test_garbled_scanner_text_is_shown_as_picture(samples, tmp_path):
    """A scanner text layer full of nonsense is replaced by a picture of the page, with a warning."""
    src = pymupdf.open(samples / "sample_scanned.pdf")
    out = pymupdf.open()
    out.insert_pdf(src, from_page=0, to_page=0)
    page = out[0]
    junk = "^^Tn wlm^ Zrawtrhi^h fTelel ^^qk7es poTseu^ s AlmT^^ iocalhuge7hTgh"
    for i in range(30):
        page.insert_text((60, 80 + i * 22), junk, fontsize=9, render_mode=3)
    path = tmp_path / "garbled.pdf"
    out.save(path)
    doc = pipeline.load(path, use_ocr=False).document
    assert any(b.kind == BlockKind.IMAGE and b.image.kind == "unreadable-text" for b in doc.blocks)
    assert not any("Zrawtrhi" in b.text for b in doc.blocks)
    assert any("shown as pictures" in w for w in doc.warnings)
