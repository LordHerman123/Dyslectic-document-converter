"""EPUB 3 export: a reflowable book for e-readers, tablets and phones.

Unlike a PDF, an EPUB lets the reader's own app change the font, size, spacing and colours, and it fits
any screen. The book keeps the converted document's structure: headings (with a table of contents),
paragraphs with bold/italic and bold word starts, lists, boxed sections, figures and formulas as
pictures with their text as description, real tables, and notes and citations as links that can be
tapped. The chosen font is embedded when its licence allows (the fonts that come with the app); the
reading settings become the book's default style, which the reader can still change. Text and
background colours are left to the reading app, so its night mode keeps working.
"""
from __future__ import annotations

import datetime as _dt
import io
import re
import uuid
import zipfile
from pathlib import Path
from typing import Optional
from xml.sax.saxutils import escape, unescape

from ..fonts import get_family
from ..settings import FormatSettings
from .compose import ComposeResult, RItem, Run
from .labels import label as doc_label

_BAD_XML = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f￾￿]")
_FONT_DIR = (Path(__file__).resolve().parents[1] / "assets" / "fonts").resolve()


def _x(text: str) -> str:
    return escape(_BAD_XML.sub("", text), {'"': "&quot;"})


class _Book:
    def __init__(self, result: ComposeResult, s: FormatSettings):
        self.result = result
        self.s = s
        self.images: list[tuple[str, bytes, str]] = []  # (file name, data, media type)
        self._image_names: dict[int, str] = {}
        self.anchors: dict[str, str] = {}  # marker text ("[Note 3]", "[12]") -> "chapter.xhtml#id"
        self.chapter = ""

    # ------------------------------------------------------------------ pieces
    def image_file(self, img) -> str:
        key = id(img)
        if key not in self._image_names:
            ext = "jpg" if img.ext in ("jpeg", "jpg") else "png"
            name = f"images/img{len(self.images) + 1}.{ext}"
            self.images.append((name, img.data, "image/jpeg" if ext == "jpg" else "image/png"))
            self._image_names[key] = name
        return self._image_names[key]

    def inline(self, runs: list[Run]) -> str:
        images = self.result.inline_images
        out = []
        for r in runs:
            if r.marker:  # "[Note 3]", "[12]", "[21][24]": each one a link to its note or reference
                def link(m: re.Match) -> str:
                    target = self.anchors.get(m.group())
                    t = _x(m.group())
                    return f'<a epub:type="noteref" href="{target}">{t}</a>' if target else t

                out.append(re.sub(r"\[[^\]]+\]|[^\[]+", lambda m: link(m) if m.group().startswith("[") else _x(m.group()),
                                  r.text))
                continue
            parts = []
            for ch in r.text:
                img = images.get(ch)
                if img is None:
                    parts.append(_x(ch))
                    continue
                size = img.text_size or 10.0
                h_pt = (img.width_pt or img.width * 72 / 300) * img.height / max(1, img.width)
                style = f"height:{h_pt / size:.2f}em;vertical-align:-{(img.descent or 0) / size:.2f}em"
                parts.append(f'<img class="math" src="{self.image_file(img)}" alt="{_x(img.alt or "formula")}" '
                             f'style="{style}"/>')
            t = "".join(parts)
            if not t:
                continue
            if r.superscript:
                t = f"<sup>{t}</sup>"
            elif r.subscript:
                t = f"<sub>{t}</sub>"
            if r.italic:
                t = f"<i>{t}</i>"
            if r.bold:
                t = f"<b>{t}</b>"
            out.append(t)
        return "".join(out).strip()

    def table(self, it: RItem) -> str:
        tab = it.table
        rows = tab.rows if tab else []
        if tab is None or not tab.reliable or not rows or self.s.table_mode == "image":
            if tab is not None and tab.fallback_image is not None:
                img = tab.fallback_image
                return (f'<figure class="table-picture"><img src="{self.image_file(img)}" '
                        f'alt="{_x(doc_label(self.result.language, "table_picture"))}"/></figure>')
            return ""
        n = max(len(r) for r in rows)
        head = max(1, min(tab.header_rows, len(rows) - 1)) if len(rows) > 1 else 0
        bold = tab.bold_cells or set()

        def row_html(ri: int, row: list[str], tag: str) -> str:
            cells = list(row) + [""] * (n - len(row))
            return "<tr>" + "".join(
                f"<{tag}>{'<b>' + _x(c) + '</b>' if (ri, ci) in bold and tag == 'td' else _x(c)}</{tag}>"
                for ci, c in enumerate(cells)) + "</tr>"

        html = ["<table>"]
        if head:
            html += ["<thead>"] + [row_html(ri, rows[ri], "th") for ri in range(head)] + ["</thead>"]
        html += ["<tbody>"] + [row_html(ri, rows[ri], "td") for ri in range(head, len(rows))] + ["</tbody>", "</table>"]
        return "\n".join(html)

    # ------------------------------------------------------------------ chapters
    def chapters(self) -> tuple[list[tuple[str, str, list[str]]], list[tuple[int, str, str]]]:
        """(file, title, xhtml body parts) per chapter, and the table of contents (level, title, href)."""
        items = self.result.items
        # a new chapter starts at the title and at every top-level heading
        groups: list[list[RItem]] = [[]]
        for it in items:
            if it.kind in ("heading", "title") and (it.level or 1) <= 1 and groups[-1]:
                groups.append([])
            groups[-1].append(it)
        names = [f"text/ch{i + 1:03d}.xhtml" for i in range(len(groups))]
        # first pass: where every note and reference lives, so markers in the text can link to them
        for name, group in zip(names, groups):
            for n, it in enumerate(group):
                if it.marker and it.kind in ("endnote", "reference", "list_item", "paragraph"):
                    here = f"{Path(name).name}#{self._id(name, n)}"
                    m = it.marker.strip()
                    self.anchors.setdefault(m, here)
                    if it.kind == "reference" and re.fullmatch(r"\d+\.", m):
                        self.anchors.setdefault(f"[{m[:-1]}]", here)  # cited in the text as [12]
        out, toc = [], []
        for name, group in zip(names, groups):
            self.chapter = name
            parts: list[str] = []
            title = ""
            i = 0
            while i < len(group):
                it = group[i]
                aid = self._id(name, i)
                k = it.kind
                if k in ("title", "heading", "box_heading"):
                    level = 1 if k == "title" else min(6, (it.level or 1) + (1 if self._has_title() else 0))
                    text = self.inline(it.runs)
                    cls = ' class="box"' if k == "box_heading" else ""
                    parts.append(f'<h{level} id="{aid}"{cls}>{text}</h{level}>')
                    plain = re.sub(r"<[^>]+>", "", text)
                    title = title or plain
                    if level <= 3 and plain:
                        toc.append((level, plain, f"{Path(name).name}#{aid}"))
                elif k == "image":
                    cap = group[i + 1] if i + 1 < len(group) and group[i + 1].kind == "caption" else None
                    if it.image is not None:
                        alt = it.image.alt or (re.sub(r"<[^>]+>", "", self.inline(cap.runs)) if cap else "") \
                            or doc_label(self.result.language, "figure")
                        fig = f'<figure id="{aid}"><img src="../{self.image_file(it.image)}" alt="{_x(alt)}"/>'
                        if cap is not None:
                            fig += f"<figcaption>{self.inline(cap.runs)}</figcaption>"
                            i += 1
                        parts.append(fig + "</figure>")
                elif k == "equation":
                    if it.image is not None:
                        size = it.image.text_size or 10.0
                        w_em = (it.natural_width or it.image.width * 72 / 300) / size
                        alt = it.image.alt or doc_label(self.result.language, "formula")
                        parts.append(f'<div class="equation" id="{aid}"><img src="../{self.image_file(it.image)}" '
                                     f'alt="{_x(alt)}" style="width:{w_em:.1f}em"/></div>')
                elif k == "table":
                    t = self.table(it).replace('src="images/', 'src="../images/')
                    if t:
                        parts.append(f'<div class="table" id="{aid}">{t}</div>')
                elif k == "caption":
                    parts.append(f'<p class="caption" id="{aid}">{self.inline(it.runs)}</p>')
                else:
                    cls = {"box_paragraph": "box", "quote": "quote", "endnote": "note", "small": "small",
                           "about": "about", "list_item": "item", "reference": "reference"}.get(k, "")
                    marker = f'<span class="marker">{_x(it.marker)}</span> ' if it.marker else ""
                    et = ' epub:type="footnote"' if k == "endnote" else ""
                    c = f' class="{cls}"' if cls else ""
                    parts.append(f'<p id="{aid}"{c}{et}>{marker}{self.inline(it.runs)}</p>')
                i += 1
            parts = [p.replace('src="images/', 'src="../images/') for p in parts]
            out.append((name, title, parts))
        return out, toc

    def _has_title(self) -> bool:
        return any(it.kind == "title" for it in self.result.items)

    @staticmethod
    def _id(name: str, n: int) -> str:
        return f"{Path(name).stem}-{n}"

    # ------------------------------------------------------------------ style
    def css(self, font_files: list[tuple[str, bool, bool]], family: str) -> str:
        s = self.s
        size = s.font_size or 12
        faces = "".join(
            f'@font-face {{ font-family: "{family}"; src: url("{f}"); font-weight: {"bold" if b else "normal"}; '
            f'font-style: {"italic" if it else "normal"}; }}\n' for f, b, it in font_files)
        generic = f'"{family}", "{s.font}", sans-serif'
        align = s.alignment if s.alignment in ("left", "center", "justify") else "left"
        return faces + f"""
body {{ font-family: {generic}; line-height: {s.line_spacing:.2f};
  letter-spacing: {s.letter_spacing / size:.3f}em; word-spacing: {max(0.0, s.word_spacing) / size:.3f}em;
  text-align: {align}; hyphens: none; -epub-hyphens: none; -webkit-hyphens: none; }}
p {{ margin: 0 0 {s.paragraph_spacing / size:.2f}em 0; text-indent: 0; }}
h1, h2, h3, h4, h5, h6 {{ font-weight: bold; line-height: 1.3; margin: 1.4em 0 0.6em 0; text-align: left; }}
h1 {{ font-size: 1.5em; }} h2 {{ font-size: 1.3em; border-bottom: 1px solid currentColor; padding-bottom: 0.15em; }}
h3 {{ font-size: 1.15em; }} h4, h5, h6 {{ font-size: 1.05em; }}
.box {{ border-left: 0.25em solid #7A2E3A; padding: 0.2em 0 0.2em 0.8em; }}
.quote {{ margin-left: 1.5em; font-style: italic; }}
.item {{ margin-left: 1.5em; }}
.marker {{ font-weight: bold; }}
.note, .small, .about, .reference {{ font-size: 0.92em; }}
.caption, figcaption {{ font-size: 0.92em; font-style: italic; margin-top: 0.3em; }}
figure {{ margin: 1em 0; }}
figure img, .table-picture img {{ max-width: 100%; height: auto; }}
.equation {{ text-align: center; margin: 0.8em 0; }}
.equation img {{ max-width: 100%; height: auto; }}
img.math {{ display: inline; max-width: none; }}
.table {{ overflow-x: auto; margin: 1em 0; }}
table {{ border-collapse: collapse; font-size: 0.92em; }}
th, td {{ border: 1px solid currentColor; padding: 0.25em 0.5em; text-align: left; vertical-align: top; }}
a {{ text-decoration: none; }}
"""


def _nested_list(entries: list[tuple[int, str]]) -> str:
    """An <ol> tree from (heading level, html) entries. Levels become depths first (an entry nests under
    the nearest earlier entry with a lower level), so skipped levels and odd orders stay well-formed."""
    depths: list[int] = []
    ancestors: list[int] = []
    for level, _ in entries:
        while ancestors and ancestors[-1] >= level:
            ancestors.pop()
        depths.append(len(ancestors))
        ancestors.append(level)
    html: list[str] = []
    cur = -1
    for depth, (_, item) in zip(depths, entries):
        if depth > cur:
            html.append("<ol>")
        else:
            html.append("</li>")
            html.append("</ol></li>" * (cur - depth))
        html.append(f"<li>{item}")
        cur = depth
    if cur >= 0:
        html.append("</li>" + "</ol></li>" * cur + "</ol>")
    return "".join(html)


def _page(title: str, body: str, lang: str) -> str:
    return (f'<?xml version="1.0" encoding="utf-8"?>\n<!DOCTYPE html>\n'
            f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            f'lang="{lang}" xml:lang="{lang}">\n<head><meta charset="utf-8"/><title>{_x(title)}</title>'
            f'<link rel="stylesheet" type="text/css" href="../style.css"/></head>\n<body>\n{body}\n</body>\n</html>\n')


def _font_files(s: FormatSettings) -> tuple[str, list[tuple[str, bytes, bool, bool]]]:
    """The font to embed: only the openly licensed fonts that come with the app, never system fonts."""
    fam = get_family(s.font)
    out = []
    seen = set()
    for path, bold, italic in ((fam.regular, False, False), (fam.bold, True, False), (fam.italic, False, True),
                               (fam.bold_italic, True, True)):
        if not path or path in seen:
            continue
        p = Path(path).resolve()
        if p.parent != _FONT_DIR or not p.exists():
            continue  # a font installed on this computer (e.g. Verdana): its licence may not allow sharing
        seen.add(path)
        out.append((f"fonts/{p.name}", p.read_bytes(), bold, italic))
    return fam.name, out


def build_epub(result: ComposeResult, s: FormatSettings, title: str = "", author: str = "") -> bytes:
    lang = result.language or "en"
    book = _Book(result, s)
    chapters, toc = book.chapters()
    family, fonts = _font_files(s)
    title = title or next((t for _, t, _ in chapters if t), "") or "Converted document"
    book_id = f"urn:uuid:{uuid.uuid4()}"
    modified = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(zipfile.ZipInfo("mimetype"), "application/epub+zip", compress_type=zipfile.ZIP_STORED)

        def put(name: str, data, deflate: bool = True):
            z.writestr(name, data, compress_type=zipfile.ZIP_DEFLATED if deflate else zipfile.ZIP_STORED)

        put("META-INF/container.xml",
            '<?xml version="1.0" encoding="utf-8"?>\n<container version="1.0" '
            'xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n<rootfiles><rootfile full-path="OEBPS/content.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles>\n</container>\n')
        manifest = ['<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
                    '<item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
                    '<item id="css" href="style.css" media-type="text/css"/>']
        spine = []
        for n, (name, ch_title, parts) in enumerate(chapters):
            put(f"OEBPS/{name}", _page(ch_title or title, "\n".join(parts), lang))
            manifest.append(f'<item id="c{n + 1}" href="{name}" media-type="application/xhtml+xml"/>')
            spine.append(f'<itemref idref="c{n + 1}"/>')
        for n, (name, data, media) in enumerate(book.images):
            put(f"OEBPS/{name}", data, deflate=False)
            manifest.append(f'<item id="i{n + 1}" href="{name}" media-type="{media}"/>')
        for n, (name, data, _, _) in enumerate(fonts):
            put(f"OEBPS/{name}", data)
            manifest.append(f'<item id="f{n + 1}" href="{name}" media-type="font/ttf"/>')
        put("OEBPS/style.css", book.css([(f, b, i) for f, _, b, i in fonts], family))

        # table of contents: EPUB 3 navigation page, plus the older NCX for older readers
        entries = toc or [(1, title, f"{Path(chapters[0][0]).name}")]
        nav_items = _nested_list([(level, f'<a href="text/{href}">{_x(text)}</a>') for level, text, href in entries])
        nav_body = (f'<nav epub:type="toc" id="toc"><h1>{_x(doc_label(lang, "contents"))}</h1>'
                    + nav_items + "</nav>")
        put("OEBPS/nav.xhtml", _page(doc_label(lang, "contents"), nav_body, lang).replace("../style.css", "style.css"))
        points = "".join(f'<navPoint id="p{n + 1}" playOrder="{n + 1}"><navLabel><text>{_x(text)}</text></navLabel>'
                         f'<content src="text/{href}"/></navPoint>' for n, (_, text, href) in enumerate(entries))
        put("OEBPS/toc.ncx",
            f'<?xml version="1.0" encoding="utf-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">'
            f'<head><meta name="dtb:uid" content="{book_id}"/></head><docTitle><text>{_x(title)}</text></docTitle>'
            f'<navMap>{points}</navMap></ncx>\n')
        creator = f"<dc:creator>{_x(author)}</dc:creator>" if author else ""
        put("OEBPS/content.opf",
            f'<?xml version="1.0" encoding="utf-8"?>\n<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
            f'unique-identifier="bookid" xml:lang="{lang}">\n<metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
            f'<dc:identifier id="bookid">{book_id}</dc:identifier><dc:title>{_x(title)}</dc:title>'
            f'<dc:language>{lang}</dc:language>{creator}'
            f'<meta property="dcterms:modified">{modified}</meta>'
            f'<meta property="schema:accessMode">textual</meta><meta property="schema:accessMode">visual</meta>'
            f'<meta property="schema:accessibilityFeature">structuralNavigation</meta>'
            f'<meta property="schema:accessibilityFeature">alternativeText</meta>'
            f'<meta property="schema:accessibilityFeature">tableOfContents</meta>'
            f'<meta property="schema:accessibilityHazard">none</meta>'
            f'<meta property="schema:accessibilitySummary">Reformatted for easier reading; the author\'s wording '
            f'is unchanged.</meta></metadata>\n'
            f'<manifest>{"".join(manifest)}</manifest>\n<spine toc="ncx">{"".join(spine)}</spine>\n</package>\n')
    return buf.getvalue()


def chapter_texts(data: bytes) -> list[str]:
    """The text of each chapter of an EPUB made here, in reading order (for tests and checks)."""
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = sorted(n for n in z.namelist() if n.startswith("OEBPS/text/"))
        out = []
        for n in names:
            html = z.read(n).decode("utf-8")
            html = re.sub(r"</?(?:b|i|sup|sub|a|span)(?:\s[^>]*)?>", "", html)  # inside a line: no gap
            text = re.sub(r"<[^>]+>", " ", html)  # paragraphs, headings, cells: a gap
            out.append(re.sub(r"\s+", " ", unescape(text)).strip())
        return out
