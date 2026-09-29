"""Opening a web page: only the article is kept (with its pictures), saved on this device and read like a book.

The pages are served from this computer (a small local web server), so the tests do not use the internet.
"""
import functools
import http.server
import io
import threading

import httpx
import pytest
from PIL import Image

from dyslexia_converter import pipeline
from dyslexia_converter.extract import web
from dyslexia_converter.model import BlockKind
from dyslexia_converter.settings import FormatSettings

PARA = ("Foxes have learned to live in cities, where they find food in gardens, parks and bins, and where they "
        "have fewer enemies than in the countryside. ")


def _png() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (120, 80), (200, 60, 60)).save(out, "PNG")
    return out.getvalue()


ARTICLE = f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>Foxes in the city | Daily News</title>
<meta property="og:title" content="Foxes in the city"><script>var tracking = 1;</script>
<style>body {{ color: red }}</style></head><body>
<header class="site-header"><a href="/">Daily News</a><nav><a href="/">Home</a> <a href="/news">News</a></nav></header>
<div class="cookie-banner">We use cookies. Accept all?</div>
<div id="content"><article><h1>Foxes in the city</h1>
<p>{PARA * 3}</p>
<figure><img data-src="fox.png" src="data:image/gif;base64,R0lGODlhAQABAAAAACw="><figcaption>A fox in a garden</figcaption></figure>
<h2>Where they live</h2><p>{PARA * 2} Read <a href="/more">more about foxes</a> in our guide.</p>
<ul><li>Gardens</li><li>Parks</li></ul>
<img src="missing.png">
<div class="share-buttons">Share on social media</div></article>
<aside class="related">Related: Cats in the city</aside></div>
<footer>Copyright Daily News</footer></body></html>"""

NO_ARTICLE = "<html><head><title>Login</title></head><body><form>Log in <input name=u></form></body></html>"


@pytest.fixture
def site(tmp_path):
    """A small web site on this computer: /article.html, /login.html, /fox.png, /file.pdf."""
    root = tmp_path / "site"
    root.mkdir()
    (root / "article.html").write_text(ARTICLE, encoding="utf-8")
    (root / "login.html").write_text(NO_ARTICLE, encoding="utf-8")
    (root / "fox.png").write_bytes(_png())
    (root / "file.pdf").write_bytes(b"%PDF-1.4\n")
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    handler.log_message = lambda *a: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture
def client():
    with httpx.Client(trust_env=False, follow_redirects=True) as c:  # straight to the local site, no proxy
        yield c


def test_normalise_url():
    assert web.normalise_url(" example.org/news ") == "https://example.org/news"
    assert web.normalise_url("http://localhost:8000/a") == "http://localhost:8000/a"
    for bad in ("", "ftp://example.org/x", "just words"):
        with pytest.raises(web.WebPageError):
            web.normalise_url(bad)


def test_article_is_kept_and_the_rest_left_out(site, client, tmp_path):
    path = web.save_article(site + "/article.html", client=client, folder=tmp_path)
    saved = path.read_text(encoding="utf-8")
    assert path.suffix == ".html" and path.name.startswith("Foxes in the city")
    assert "Where they live" in saved and "more about foxes" in saved  # the link's words stay, as text
    for clutter in ("cookies", "Share on", "Related:", "Copyright", "Home", "tracking", "<a "):
        assert clutter not in saved, clutter
    assert saved.count("data:image/png;base64,") == 1  # the lazy-loaded picture is stored; the missing one left out
    assert f'content="{site}/article.html"' in saved  # where it came from

    doc = pipeline.load(str(path), FormatSettings()).document
    kinds = [b.kind for b in doc.blocks]
    assert doc.title == "Foxes in the city"
    assert kinds[:2] == [BlockKind.HEADING, BlockKind.PARAGRAPH]
    assert BlockKind.IMAGE in kinds and BlockKind.CAPTION in kinds
    assert [b.text for b in doc.blocks if b.kind == BlockKind.LIST_ITEM] == ["• Gardens", "• Parks"]
    assert web.save_article(site + "/article.html", client=client, folder=tmp_path) == path  # same page, same file


def test_pages_that_cannot_be_opened(site, client, tmp_path):
    for address in (site + "/login.html", site + "/nothing-here.html", site + "/file.pdf"):
        with pytest.raises(web.WebPageError):
            web.save_article(address, client=client, folder=tmp_path)
    assert not list(tmp_path.glob("*.html"))


def test_saved_page_converts(site, client, tmp_path):
    path = web.save_article(site + "/article.html", client=client, folder=tmp_path)
    session = pipeline.load(str(path), FormatSettings())
    assert session.original_pdf and session.export("pdf", FormatSettings())[:4] == b"%PDF"
