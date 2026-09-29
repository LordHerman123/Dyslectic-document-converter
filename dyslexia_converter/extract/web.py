"""Opening a web page (an article) as a document.

The page is downloaded once and only its article is kept: menus, headers and footers, adverts, cookie banners,
share buttons and "related" boxes are left out, the same way a browser's reader view does it. Its pictures are
stored inside the page, and the result is saved on this device as an .html file, which the app then opens like a
Word or EPUB file (see :mod:`.structured`). Nothing is sent anywhere: the page is only requested from its site.
"""
from __future__ import annotations

import base64
import hashlib
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin, urlparse

MAX_PAGE = 15 * 1024 * 1024  # bytes of HTML read at most
MAX_IMAGES = 30
MAX_IMAGE = 6 * 1024 * 1024
TIMEOUT = 20.0
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DyslexiaConverter (reader view)"

# parts of a page that are not the article
_DROP_TAGS = ("script", "style", "noscript", "iframe", "form", "nav", "footer", "aside", "button", "input", "select",
              "textarea", "svg", "canvas", "video", "audio", "template", "dialog", "object", "embed")
_DROP_HINTS = re.compile(
    r"(^|[\s_-])(comment|comments|share|sharing|social|related|recommend|promo|newsletter|subscribe|signup|"
    r"cookie|consent|banner|sidebar|menu|breadcrumb|nav|navbar|footer|masthead|advert|ads?|sponsor|popup|modal|"
    r"toolbar|skip-link|paywall|outbrain|taboola|byline-share)([\s_-]|$)", re.I)


class WebPageError(ValueError):
    """The address is not a web page that can be opened (wrong address, not found, no article text)."""


def normalise_url(text: str) -> str:
    """The address as typed, made complete ("example.org/x" becomes "https://example.org/x")."""
    url = text.strip()
    if not url:
        raise WebPageError("Type the address of a web page")
    if not re.match(r"^[a-z][a-z0-9+.-]*://", url, re.I):
        url = "https://" + url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc or "." not in parsed.netloc.split(":")[0] \
            and parsed.netloc.split(":")[0] != "localhost" and not re.match(r"^\d+\.\d+\.\d+\.\d+$",
                                                                            parsed.netloc.split(":")[0]):
        raise WebPageError("This is not the address of a web page")
    return url


def download(url: str, client=None) -> tuple[str, str]:
    """(HTML text, final address after redirects) of a web page."""
    import httpx

    own = client is None
    client = client or httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    try:
        r = client.get(url)
    except httpx.HTTPError as e:
        raise WebPageError("The page could not be downloaded. Check the address and the internet "
                           "connection.") from e
    finally:
        if own:
            client.close()
    if r.status_code >= 400:
        raise WebPageError("The site did not give the page (it may not exist, or it needs a login).")
    kind = r.headers.get("content-type", "")
    if kind and "html" not in kind and "xml" not in kind:
        raise WebPageError("This address is a file, not a web page. Download it and open it with Open file.")
    data = r.content[:MAX_PAGE]
    return data.decode(r.encoding or "utf-8", errors="replace"), str(r.url)


def extract_article(html: str, base_url: str = "") -> tuple[str, str]:
    """(title, article HTML) of a page: the part with the running text, without the page around it."""
    from lxml import etree, html as lh

    try:
        root = lh.fromstring(html)
    except (etree.ParserError, ValueError) as e:
        raise WebPageError("The page could not be read") from e
    if base_url:
        root.make_links_absolute(base_url, resolve_base_href=True)
    title = _title(root)
    for el in root.xpath("//comment()"):
        _drop(el)
    for tag in _DROP_TAGS:
        for el in root.iter(tag):
            _drop(el)
    for el in list(root.iter("header")):  # the page's header goes; a header inside the article (its title) stays
        if not any(a.tag in ("article", "main") for a in el.iterancestors()):
            _drop(el)
    for el in list(root.iter()):
        if not isinstance(el.tag, str):
            continue
        hint = " ".join(filter(None, (el.get("class"), el.get("id"), el.get("role"))))
        if el.get("aria-hidden") == "true" or el.get("hidden") is not None or \
                (hint and _DROP_HINTS.search(hint) and el.tag not in ("html", "body", "article", "main")):
            _drop(el)
    best = _main_part(root)
    if best is None or len(_text(best)) < 200:
        raise WebPageError("No article text was found on this page")
    for el in best.iter("a"):  # links are read as plain text
        el.drop_tag()
    for img in best.iter("img"):  # lazy-loaded pictures keep their real address in data-src
        real = img.get("data-src") or img.get("data-original") or img.get("data-lazy-src")
        if real and (not img.get("src") or img.get("src", "").startswith("data:")):
            img.set("src", urljoin(base_url, real))
    body = etree.tostring(best, encoding="unicode", method="html")
    if not best.xpath(".//h1") and title:
        body = f"<h1>{_escape(title)}</h1>\n" + body
    return title, body


def _drop(el) -> None:
    parent = el.getparent()
    if parent is None:
        return
    tail = el.tail
    prev = el.getprevious()
    parent.remove(el)
    if tail and tail.strip():  # keep text that followed the removed part
        if prev is not None:
            prev.tail = (prev.tail or "") + tail
        else:
            parent.text = (parent.text or "") + tail


def _text(el) -> str:
    return re.sub(r"\s+", " ", el.text_content() or "").strip()


def _title(root) -> str:
    """The article's title: the page's own title for sharing, else its <title> without the site's name
    ("Foxes | Daily News" -> "Foxes" when the article's heading says "Foxes"), else the first heading."""
    heading = re.sub(r"\s+", " ", " ".join(root.xpath("(//h1)[1]//text()"))).strip()
    for xp in ("//meta[@property='og:title']/@content", "//meta[@name='twitter:title']/@content",
               "//title/text()", "//h1//text()"):
        found = [t.strip() for t in root.xpath(xp) if t and t.strip()]
        if found:
            title = re.sub(r"\s+", " ", found[0])
            if xp.startswith("//title") and heading and title.startswith(heading) and title != heading:
                return heading
            return title
    return ""


def _main_part(root):
    """The element holding the article: an <article> or <main> with enough text, else the element whose
    paragraphs hold the most text (the usual reader-view rule)."""
    for tag in ("article", "main"):
        cands = [el for el in root.iter(tag) if len(_text(el)) >= 300]
        if cands:
            return max(cands, key=lambda el: len(_text(el)))
    scores: dict = {}
    for p in root.iter("p"):
        t = _text(p)
        if len(t) < 40:
            continue
        parent = p.getparent()
        if parent is None:
            continue
        scores[parent] = scores.get(parent, 0) + len(t) + 20 * t.count(",")
        grand = parent.getparent()
        if grand is not None:
            scores[grand] = scores.get(grand, 0) + (len(t) + 20 * t.count(",")) / 2
    if not scores:
        body = root.find("body")
        return body if body is not None else root
    return max(scores, key=scores.get)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def embed_images(article: str, client=None) -> str:
    """The article with its pictures stored inside it (data: addresses), so the saved copy is complete on its own;
    pictures that cannot be downloaded are left out."""
    import httpx
    from lxml import etree, html as lh

    root = lh.fragment_fromstring(article, create_parent="div")
    own = client is None
    client = client or httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": USER_AGENT})
    count = 0

    def fetch(src: str) -> str:
        nonlocal count
        if src.startswith("data:image/"):
            return src
        if count >= MAX_IMAGES or not src.startswith(("http://", "https://")):
            return ""
        count += 1
        try:
            r = client.get(src)
        except httpx.HTTPError:
            return ""
        kind = r.headers.get("content-type", "").split(";")[0]
        if r.status_code >= 400 or not kind.startswith("image/") or len(r.content) > MAX_IMAGE:
            return ""
        return f"data:{kind};base64,{base64.b64encode(r.content).decode()}"

    try:
        for img in list(root.iter("img")):
            data = fetch(img.get("src", "").strip())
            if not data:  # a picture that cannot be downloaded is left out
                _drop(img)
                continue
            alt = img.get("alt")
            img.attrib.clear()
            img.set("src", data)
            if alt:
                img.set("alt", alt)
    finally:
        if own:
            client.close()
    return "".join([root.text or ""] + [etree.tostring(el, encoding="unicode", method="html") for el in root])


def web_dir() -> Path:
    """The folder where downloaded web pages are kept (on this device)."""
    from ..settings import app_data_dir

    d = app_data_dir() / "web_pages"
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_article(url: str, client=None, folder: Optional[Path] = None) -> Path:
    """Download the page at ``url``, keep its article (with pictures) and save it as an .html file; returns the
    file, which the app opens like any document. The same address gives the same file (it is refreshed)."""
    url = normalise_url(url)
    html, final = download(url, client)
    title, article = extract_article(html, final)
    article = embed_images(article, client)
    name = re.sub(r"[^\w\s-]", "", title or urlparse(final).netloc).strip()[:60] or "web page"
    name = re.sub(r"\s+", " ", name)
    digest = hashlib.sha1(final.encode()).hexdigest()[:8]
    path = (folder or web_dir()) / f"{name} ({digest}).html"
    page = ("<!DOCTYPE html>\n<html><head><meta charset=\"utf-8\">"
            f"<title>{_escape(title)}</title><meta name=\"source-url\" content=\"{_escape(final)}\">"
            "<style>body{font-family:serif;max-width:40em;margin:2em auto;line-height:1.5}"
            "img{max-width:100%}</style></head>\n"
            f"<body>\n{article}\n</body></html>\n")
    path.write_text(page, encoding="utf-8")
    return path
