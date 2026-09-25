"""Plain text and Markdown export."""
from __future__ import annotations

from .compose import ComposeResult, RItem


_images: dict = {}


def _unpack(text: str) -> str:
    """Small formula pictures in the text become their text form."""
    if not _images:
        return text
    return "".join(_images[c].alt if c in _images and _images[c].alt else c for c in text)


def _plain(item: RItem) -> str:
    return _unpack("".join(r.text for r in item.runs)).strip()


def build_text(result: ComposeResult) -> str:
    global _images
    _images = result.inline_images
    out: list[str] = []
    for it in result.items:
        if it.kind == "equation":
            out.append("    " + (it.image.alt if it.image else ""))
        elif it.kind == "image":
            out.append("[Image]")
        elif it.kind == "table":
            if it.table and it.table.reliable:
                out.append("\n".join(" | ".join(r) for r in it.table.rows))
            else:
                out.append("[Table - see PDF export]")
        elif it.kind in ("heading", "title", "box_heading"):
            text = _plain(it)
            out.append(text + "\n" + ("=" if it.kind == "title" else "-") * min(len(text), 60))
        else:
            prefix = f"{it.marker} " if it.marker else ""
            out.append(prefix + _plain(it))
    return "\n\n".join(x for x in out if x) + "\n"


def _md_runs(item: RItem, bionic: bool = True) -> str:
    parts = []
    for r in item.runs:
        t = _unpack(r.text).replace("*", "\\*").replace("_", "\\_")
        if r.superscript and not r.marker:
            t = f"<sup>{t}</sup>"
        elif r.subscript:
            t = f"<sub>{t}</sub>"
        if r.bold and t.strip():
            lead = t[: len(t) - len(t.lstrip())]
            trail = t[len(t.rstrip()):]
            t = f"{lead}**{t.strip()}**{trail}"
        if r.italic and t.strip():
            lead = t[: len(t) - len(t.lstrip())]
            trail = t[len(t.rstrip()):]
            t = f"{lead}*{t.strip()}*{trail}"
        parts.append(t)
    return "".join(parts).strip()


def build_markdown(result: ComposeResult) -> str:
    global _images
    _images = result.inline_images
    out: list[str] = []
    for it in result.items:
        if it.kind == "equation":
            out.append("> " + (it.image.alt if it.image else "").replace("*", "\\*").replace("_", "\\_")
                       + "  \n> *(equation - see the PDF export)*")
        elif it.kind == "title":
            out.append("# " + _plain(it))
        elif it.kind in ("heading", "box_heading"):
            out.append("#" * min(6, (it.level or 1) + 1) + " " + _plain(it))
        elif it.kind == "image":
            out.append("*[Image - see PDF export]*")
        elif it.kind == "table":
            if it.table and it.table.reliable and it.table.rows:
                rows = it.table.rows
                n = max(len(r) for r in rows)
                norm = [[c.replace("|", "\\|") for c in r] + [""] * (n - len(r)) for r in rows]
                lines = ["| " + " | ".join(norm[0]) + " |", "|" + "---|" * n]
                lines += ["| " + " | ".join(r) + " |" for r in norm[1:]]
                out.append("\n".join(lines))
            else:
                out.append("*[Table - see PDF export]*")
        elif it.kind == "list_item":
            out.append(f"- {it.marker} {_md_runs(it)}" if it.marker not in ("•", "-", "*", "–") else f"- {_md_runs(it)}")
        elif it.kind in ("box_paragraph", "quote"):
            out.append("> " + _md_runs(it))
        elif it.kind == "caption":
            out.append("*" + _plain(it) + "*")
        elif it.kind == "about":
            out.append("---\n\n*" + _plain(it) + "*")
        else:
            prefix = f"{it.marker} " if it.marker else ""
            out.append(prefix + _md_runs(it))
    return "\n\n".join(out) + "\n"
