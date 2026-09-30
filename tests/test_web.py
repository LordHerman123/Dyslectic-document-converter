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


# Wikipedia: the article interface gives the article in <section>s, with reference marks and navigation boxes;
# the normal page has the site around it (menus, tools, [edit] links, language list).
WIKI_API = """<!DOCTYPE html>
<html prefix="dc: http://purl.org/dc/terms/"><head><meta charset="utf-8"><title>Red fox</title>
<link rel="stylesheet" href="/w/load.php?modules=mediawiki.skinning.content.parsoid"></head>
<body lang="en" class="mw-content-ltr sitedir-ltr ltr mw-body-content parsoid-body mediawiki mw-parser-output">
<section data-mw-section-id="0"><div class="shortdescription nomobile noexcerpt noprint searchaux"
 style="display:none">Species of carnivore</div>
<div role="note" class="hatnote navigation-not-searchable">For other uses, see Red fox (disambiguation).</div>
<p>The <b>red fox</b> (<i>Vulpes vulpes</i>) is the largest of the true foxes and one of the most widely distributed
members of the order Carnivora, being present across the entire Northern Hemisphere.<sup class="mw-ref reference">
<a href="./Red_fox#cite_note-1"><span class="mw-reflink-text">[1]</span></a></sup> It is listed as least concern.</p>
<figure typeof="mw:File/Thumb"><a href="./File:Fox.png"><img src="//upload.wikimedia.org/fox.png" width="120"
 height="80"></a><figcaption>A red fox in a garden</figcaption></figure></section>
<section data-mw-section-id="1"><h2 id="Taxonomy">Taxonomy</h2>
<p>Carl Linnaeus named the species in 1758, in the tenth edition of his Systema Naturae, and many subspecies have
been described since then, although several of them are now thought to be the same animal.</p></section>
<section data-mw-section-id="2"><h2 id="Behaviour">Behaviour</h2>
<p>Red foxes are usually together in pairs or small groups consisting of families, such as a mated pair and their
young, or a male with several females having kinship ties.</p></section>
<section data-mw-section-id="3"><h2 id="References">References</h2><div class="mw-references-wrap">
<ol class="mw-references references"><li id="cite_note-1"><span class="mw-cite-backlink"><a href="#cite_ref-1">↑</a>
</span><span class="reference-text">Hoffmann, M. (2016). Vulpes vulpes. IUCN Red List of Threatened Species.</span>
</li></ol></div></section>
<div role="navigation" class="navbox" aria-labelledby="Carnivora">Carnivora: Felidae · Canidae · Ursidae</div>
</body></html>"""

WIKI_PAGE = """<!DOCTYPE html><html class="client-nojs vector-feature-main-menu-pinned-disabled" lang="en"><head>
<title>Red fox - Wikipedia</title><meta property="og:title" content="Red fox - Wikipedia"></head>
<body class="skin-vector mediawiki ltr ns-0 page-Red_fox skin-vector-2022">
<a class="mw-jump-link" href="#bodyContent">Jump to content</a>
<div class="vector-header-container"><header class="vector-header mw-header">
<div class="vector-main-menu-container">Main page Contents Current events Random article</div>
<div id="p-search" role="search">Search Wikipedia</div></header></div>
<div class="mw-page-container"><div class="mw-page-container-inner">
<div class="vector-column-start"><nav class="vector-toc">Contents (Top) 1 Taxonomy 2 Behaviour</nav></div>
<div class="mw-content-container"><main id="content" class="mw-body">
<header class="mw-body-header vector-page-titlebar"><h1 id="firstHeading" class="firstHeading mw-first-heading">
<span class="mw-page-title-main">Red fox</span></h1>
<div id="p-lang-btn" class="vector-dropdown mw-portlet mw-portlet-lang"><input type="checkbox"
 class="vector-dropdown-checkbox"><label class="vector-dropdown-label"><span>150 languages</span></label>
<div class="vector-dropdown-content"><div class="vector-menu-content"><ul class="vector-menu-content-list">
<li>Afrikaans</li><li>العربية</li><li>Deutsch</li></ul></div></div></div></header>
<div class="vector-page-toolbar">Article Talk Read Edit View history Tools</div>
<div id="bodyContent" class="vector-body"><div id="siteSub" class="noprint">From Wikipedia, the free encyclopedia</div>
<div id="mw-content-text" class="mw-body-content"><div class="mw-content-ltr mw-parser-output" lang="en" dir="ltr">
""" + WIKI_API.split("<body", 1)[1].split(">", 1)[1].replace("</body></html>", "").replace(
    '<h2 id="Taxonomy">Taxonomy</h2>',
    '<div class="mw-heading mw-heading2"><h2 id="Taxonomy">Taxonomy</h2><span class="mw-editsection">'
    '<span class="mw-editsection-bracket">[</span><a href="/w/index.php?action=edit">edit</a>'
    '<span class="mw-editsection-bracket">]</span></span></div>') + """
</div></div><div id="catlinks" class="catlinks">Categories: Vulpes</div></div></main>
<footer id="footer" class="mw-footer">This page was last edited on 1 May 2026. Privacy policy</footer>
</div></div></div></body></html>"""


def _wiki_site(api_status=200):
    """A pretend Wikipedia: the article interface, the page itself and the picture server, which (like the real
    ones) only answer programs that name themselves."""
    seen = []

    def answer(request):
        seen.append(str(request.url))
        if not request.headers.get("user-agent", "").startswith("DyslexiaConverter/"):
            return httpx.Response(403, text="Please set a user-agent and respect our robot policy")
        path = request.url.path
        if path == "/w/rest.php/v1/page/Red_fox/html":
            return httpx.Response(api_status, headers={"content-type": "text/html; charset=utf-8"}, text=WIKI_API)
        if path == "/wiki/Red_fox":
            return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, text=WIKI_PAGE)
        if request.url.host == "upload.wikimedia.org":
            return httpx.Response(200, headers={"content-type": "image/png"}, content=_png())
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(answer), follow_redirects=True), seen


@pytest.mark.parametrize("api_status", [200, 500])
def test_wikipedia_article(tmp_path, api_status):
    """A Wikipedia article (through its article interface, or the page itself when that fails): the article with
    its sections, picture and caption; not the menus, [edit] links, languages, contents, hidden short description,
    "for other uses" note, navigation box, categories or footer."""
    client, seen = _wiki_site(api_status)
    path = web.save_article("https://en.m.wikipedia.org/wiki/Red_fox#Behaviour", client=client, folder=tmp_path)
    assert seen[0] == "https://en.wikipedia.org/w/rest.php/v1/page/Red_fox/html"
    saved = path.read_text(encoding="utf-8")
    assert path.name.startswith("Red fox (") and '<html lang="en">' in saved
    for kept in ("largest of the true foxes", "Taxonomy", "Linnaeus", "Behaviour", "kinship ties",
                 "Hoffmann, M. (2016). Vulpes vulpes",  # the reference list stays (only the marks [1] go)
                 "A red fox in a garden", "data:image/png;base64,"):
        assert kept in saved, kept
    for clutter in ("Jump to content", "Main page", "Search Wikipedia", "150 languages", "Afrikaans", "(Top)",
                    "View history", "free encyclopedia", "action=edit", "[", "Species of carnivore", "For other uses",
                    "Felidae", "Categories", "last edited", "- Wikipedia"):
        assert clutter not in saved, clutter

    doc = pipeline.load(str(path), FormatSettings()).document
    assert doc.title == "Red fox" and doc.language == "en"
    heads = [b.text for b in doc.blocks if b.kind == BlockKind.HEADING]
    assert heads == ["Red fox", "Taxonomy", "Behaviour", "References"]


def test_error_code_is_shown(tmp_path):
    client, _ = _wiki_site()
    client.headers["User-Agent"] = "x"  # a site that refuses the request
    with pytest.raises(web.WebPageError) as e:
        web.save_article("https://example.org/page", client=client, folder=tmp_path)
    assert e.value.detail == "error 403"


def test_wiki_formulas_are_written_as_text():
    """A wiki's formula pictures (SVG, which the app cannot show) become their text, so sentences stay whole."""
    assert web._formula_text(r"{\displaystyle \pi r^{2}}") == "π r^2"
    assert web._formula_text(r"{\displaystyle {\frac {a+b}{2}}}") == "(a+b)/2"
    html = ("<html><body><article><p>" + PARA * 3 + 'The area is <span class="mwe-math-element"><span '
            'style="display: none;"><math>x</math></span><img class="mwe-math-fallback-image-inline" src="a.svg" '
            'alt="{\\displaystyle \\pi r^{2}}"></span> for a circle.</p></article></body></html>')
    _, article, _ = web.extract_article(html, "https://en.wikipedia.org/wiki/Circle")
    assert "The area is <span" in article and "π r^2</span> for a circle." in article and "<math" not in article


def test_pages_are_downloaded_without_httpx(site, tmp_path):
    """The app downloads with Python's own urllib: some sites (Wikipedia) refuse connections made by httpx."""
    assert isinstance(web._client(), web._Fetcher)
    path = web.save_article(site + "/article.html", folder=tmp_path)
    saved = path.read_text(encoding="utf-8")
    assert "Where they live" in saved and saved.count("data:image/png;base64,") == 1


def test_menus_next_to_each_other_all_go():
    """Removing parts of a page while going through it must not skip the next one (two menus in a row)."""
    html = ("<html><body><main><nav>First menu</nav><nav>Second menu</nav><nav>Third menu</nav>"
            f"<p>{PARA * 3}</p></main></body></html>")
    _, article, _ = web.extract_article(html, "https://example.org/a")
    assert "menu" not in article
