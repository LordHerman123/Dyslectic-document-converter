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
from urllib.parse import quote, unquote, urljoin, urlparse

from .. import __version__

MAX_PAGE = 15 * 1024 * 1024  # bytes of HTML read at most
MAX_IMAGES = 30
MAX_IMAGE = 6 * 1024 * 1024
TIMEOUT = 20.0
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) DyslexiaConverter (reader view)"
# Wikipedia and its picture server ask programs to name themselves and where to find them, and refuse others
WIKI_USER_AGENT = (f"DyslexiaConverter/{__version__} (https://github.com/LordHerman123/Dyslectic-document-converter;"
                   " reader view for dyslexic readers)")
_WIKI_PAGE = re.compile(r"^(?:https?://)?([a-z][a-z0-9-]*)\.(?:m\.)?wikipedia\.org/wiki/([^?#]+)", re.I)

# parts of a page that are not the article
_DROP_TAGS = ("script", "style", "noscript", "iframe", "form", "nav", "footer", "aside", "button", "input", "select",
              "textarea", "svg", "canvas", "video", "audio", "template", "dialog", "object", "embed")
_DROP_HINTS = re.compile(
    r"(^|[\s_-])(comment|comments|share|sharing|social|related|recommend|promo|newsletter|subscribe|signup|"
    r"cookie|consent|banner|sidebar|menu|breadcrumb|nav|navbar|footer|masthead|advert|ads?|sponsor|popup|modal|"
    r"toolbar|skip-link|paywall|outbrain|taboola|byline-share|"
    # Wikipedia and other wikis: [edit] links, navigation boxes, "for other uses" notes, hidden short description
    r"navbox|navigation|editsection|noprint|metadata|shortdescription|hatnote|catlinks|printfooter|"
    r"jump-link|cite-backlink|empty-elt|sistersitebox|portalbox|portlet|dropdown|"
    r"reference)([\s_-]|$)", re.I)  # footnote marks like [1] in the text (the list of references stays)
_HIDDEN_STYLE = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden", re.I)


class WebPageError(ValueError):
    """The address is not a web page that can be opened (wrong address, not found, no article text).
    The message is for the reader (and can be translated); ``detail`` is technical (an error code), shown after it."""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.detail = detail


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


def _headers(url: str) -> dict:
    """Request headers for ``url``: Wikimedia's sites get the program's own name (they refuse unnamed programs)."""
    host = urlparse(url).netloc.lower()
    if host.endswith(("wikipedia.org", "wikimedia.org")):
        return {"User-Agent": WIKI_USER_AGENT, "Api-User-Agent": WIKI_USER_AGENT}
    return {}


def _client():
    import httpx

    return httpx.Client(timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": USER_AGENT})


def download(url: str, client=None) -> tuple[str, str]:
    """(HTML text, final address after redirects) of a web page."""
    import httpx

    own = client is None
    client = client or _client()
    try:
        r = client.get(url, headers=_headers(url))
    except httpx.HTTPError as e:
        raise WebPageError("The page could not be downloaded. Check the address and the internet "
                           "connection.", type(e).__name__) from e
    finally:
        if own:
            client.close()
    if r.status_code >= 400:
        raise WebPageError("The site did not give the page (it may not exist, or it needs a login).",
                           f"error {r.status_code}")
    kind = r.headers.get("content-type", "")
    if kind and "html" not in kind and "xml" not in kind:
        raise WebPageError("This address is a file, not a web page. Download it and open it with Open file.")
    data = r.content[:MAX_PAGE]
    return data.decode(r.encoding or "utf-8", errors="replace"), str(r.url)


def extract_article(html: str, base_url: str = "") -> tuple[str, str, str]:
    """(title, article HTML, language code or "") of a page: the part with the running text, without the page
    around it."""
    from lxml import etree, html as lh

    try:
        root = lh.fromstring(html)
    except (etree.ParserError, ValueError) as e:
        raise WebPageError("The page could not be read") from e
    if base_url:
        root.make_links_absolute(base_url, resolve_base_href=True)
    title = _title(root)
    for img in list(root.iter("img")):  # a wiki's formula pictures (SVG) are written as their text
        if "mwe-math-fallback" in (img.get("class") or ""):
            _replace_with_text(img, _formula_text(img.get("alt", "")))
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
                _HIDDEN_STYLE.search(el.get("style", "")) or \
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
    lang = next((el.get("lang") for el in (root, root.find("body"), best) if el is not None and el.get("lang")), "")
    body = etree.tostring(best, encoding="unicode", method="html")
    if not best.xpath(".//h1") and title:
        body = f"<h1>{_escape(title)}</h1>\n" + body
    return title, body, lang


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


def _formula_text(alt: str) -> str:
    """A formula's text from its description: "{\\displaystyle x^{2}}" -> "x^2"."""
    alt = re.sub(r"^\{\\(?:display|text)style\s*(.*)\}$", r"\1", alt.strip(), flags=re.S)
    for _ in range(3):  # \frac{a}{b} -> (a)/(b), inside out
        alt = re.sub(r"\\frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}",
                     lambda m: f"{_paren(m.group(1))}/{_paren(m.group(2))}", alt)
    alt = re.sub(r"\\(" + "|".join(_SYMBOLS) + r")(?![A-Za-z])", lambda m: _SYMBOLS[m.group(1)], alt)
    alt = alt.replace("\\{", "\x00").replace("\\}", "\x01").replace("{", "").replace("}", "")  # groups only
    return re.sub(r"\s+", " ", alt.replace("\x00", "{").replace("\x01", "}")).strip()


def _paren(part: str) -> str:
    part = part.strip()
    return part if re.fullmatch(r"[\w.]+", part) else f"({part})"


_SYMBOLS = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "theta": "θ", "lambda": "λ",
            "mu": "μ", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "phi": "φ", "omega": "ω", "Delta": "Δ",
            "Sigma": "Σ", "Omega": "Ω", "times": "×", "cdot": "·", "pm": "±", "leq": "≤", "geq": "≥", "neq": "≠",
            "approx": "≈", "infty": "∞", "sqrt": "√", "to": "→", "in": "∈", "sum": "Σ", "int": "∫", "ldots": "…",
            "circ": "°", "partial": "∂"}


def _replace_with_text(el, text: str) -> None:
    """Put ``text`` where ``el`` was (keeping the text that followed it)."""
    parent = el.getparent()
    if parent is None:
        return
    prev = el.getprevious()
    joined = text + (el.tail or "")
    parent.remove(el)
    if prev is not None:
        prev.tail = (prev.tail or "") + joined
    else:
        parent.text = (parent.text or "") + joined


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
            if heading and title.startswith(heading) and title != heading:  # "Red fox - Wikipedia"
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
    best = max(scores, key=scores.get)
    # an article split into <section>s (Wikipedia, many blogs): the whole article, not its longest section
    while best.tag == "section" and best.getparent() is not None and \
            len([c for c in best.getparent() if c.tag == "section"]) > 1:
        best = best.getparent()
    return best


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def embed_images(article: str, client=None) -> str:
    """The article with its pictures stored inside it (data: addresses), so the saved copy is complete on its own;
    pictures that cannot be downloaded are left out."""
    import httpx
    from lxml import etree, html as lh

    root = lh.fragment_fromstring(article, create_parent="div")
    own = client is None
    client = client or _client()
    count = 0

    def fetch(src: str) -> str:
        nonlocal count
        if src.startswith("data:image/"):
            return src
        if count >= MAX_IMAGES or not src.startswith(("http://", "https://")):
            return ""
        count += 1
        try:
            r = client.get(src, headers=_headers(src))
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


def _download_article(url: str, client) -> tuple[str, str, str]:
    """(HTML, address, title or "") of the page. A Wikipedia article is asked from Wikipedia's own interface for
    programs, which gives the article alone (without the site around it); if that fails, the page itself."""
    m = _WIKI_PAGE.match(url)
    if m:
        lang, page = m.group(1).lower(), unquote(m.group(2))
        api = f"https://{lang}.wikipedia.org/w/rest.php/v1/page/{quote(page.replace(' ', '_'), safe='')}/html"
        try:
            html, _ = download(api, client)
            title = page.replace("_", " ")
            return html, f"https://{lang}.wikipedia.org/wiki/{quote(page.replace(' ', '_'), safe='')}", title
        except WebPageError:
            pass
    html, final = download(url, client)
    return html, final, ""


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
    own = client is None
    client = client or _client()
    try:
        html, final, title = _download_article(url, client)
        found, article, lang = extract_article(html, final)
        title = title or found
        article = embed_images(article, client)
    finally:
        if own:
            client.close()
    name = re.sub(r"[^\w\s-]", "", title or urlparse(final).netloc).strip()[:60] or "web page"
    name = re.sub(r"\s+", " ", name)
    digest = hashlib.sha1(final.encode()).hexdigest()[:8]
    path = (folder or web_dir()) / f"{name} ({digest}).html"
    lang_attr = f' lang="{_escape(lang)}"' if re.fullmatch(r"[A-Za-z]{2,3}(-[A-Za-z0-9]+)*", lang or "") else ""
    page = (f"<!DOCTYPE html>\n<html{lang_attr}><head><meta charset=\"utf-8\">"
            f"<title>{_escape(title)}</title><meta name=\"source-url\" content=\"{_escape(final)}\">"
            "<style>body{font-family:serif;max-width:40em;margin:2em auto;line-height:1.5}"
            "img{max-width:100%}</style></head>\n"
            f"<body>\n{article}\n</body></html>\n")
    path.write_text(page, encoding="utf-8")
    return path
