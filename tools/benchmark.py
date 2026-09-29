"""Benchmark: how well documents come out of the converter, as numbers to compare between versions.

    python tools/benchmark.py run --docs FOLDER [--only NAME ...] [--ai PROVIDER] [--no-ocr-test]
    python tools/benchmark.py compare benchmarks/results/A.json benchmarks/results/B.json

The documents themselves are not in the repository (most are published papers); ``benchmarks/corpus.json`` lists
them by file name inside FOLDER, with the group each belongs to. Web pages are in ``benchmarks/web`` (pages made
for the tests, with the text that must be kept and the clutter that must go) plus any listed in the corpus.

Every score is a percentage (higher is better), measured automatically:

content kept      words of the original found in the conversion (as a bag of words, so moved notes still count)
nothing added     words of the conversion found in the original (garbled or invented words lower it)
sentences intact  runs of five words of the original that are still together: text in the right reading order,
                  columns not mixed, words not split
clutter removed   running headers and footers and page numbers of the original that did not end up in the text
headings found    entries of the PDF's own bookmarks (outline) found as headings (only PDFs that have bookmarks)
real words        share of words (3+ letters) that are dictionary words, relative to the original's own share
                  (for scans without an original text, the plain share)

For text PDFs, the reference is the PDF's own text. For scans, it is the known text where there is one (a scan
made from a text PDF). The OCR test scans the first pages of every text PDF (rendered as a slightly skewed
200 dpi image, as from a copier) and measures the same scores on what text recognition reads back.

``--ai PROVIDER`` runs the AI-assisted mode as well: the key comes from the provider's environment variable
(MISTRAL_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY) and is never written anywhere; answers are kept in a
temporary folder that is removed afterwards. Web pages are opened the same way in both modes (AI does not take
part in reading a web page), so they are only measured once.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import statistics
import sys
import tempfile
import time
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
BENCH = ROOT / "benchmarks"
OCR_TEST_PAGES = 3
METRICS = ("content_kept", "nothing_added", "sentences_intact", "clutter_removed", "headings_found", "real_words")
LABELS = {"content_kept": "Content kept", "nothing_added": "Nothing added", "sentences_intact": "Sentences intact",
          "clutter_removed": "Clutter removed", "headings_found": "Headings found", "real_words": "Real words",
          "article_kept": "Article kept", "overall": "Overall"}


# ----------------------------------------------------------------------------- text measures
def words(text: str) -> list[str]:
    """The words of a text, compared the same way everywhere: ligatures undone, words broken over a line joined,
    lower case, punctuation left out."""
    text = unicodedata.normalize("NFKC", text or "")
    text = re.sub(r"(\w)[-­‐]\s*\n\s*(\w)", r"\1\2", text)
    return re.findall(r"[^\W_]+(?:['’][^\W_]+)?", text.lower())


def bag_scores(ref: list[str], out: list[str]) -> tuple[float, float]:
    """(content kept, nothing added): overlap of the two bags of words, from each side."""
    if not ref or not out:
        return 0.0, 0.0
    common = sum((Counter(ref) & Counter(out)).values())
    return common / len(ref), common / len(out)


def runs_intact(ref: list[str], out: list[str], n: int = 5) -> float:
    """Share of the original's runs of ``n`` words that appear together in the conversion."""
    grams = [tuple(ref[i:i + n]) for i in range(len(ref) - n + 1)]
    if not grams:
        return 0.0
    have = {tuple(out[i:i + n]) for i in range(len(out) - n + 1)}
    return sum(g in have for g in grams) / len(grams)


_SPELL: dict = {}


def real_word_share(text: str, language: str) -> float | None:
    """Share of words with 3+ letters that are in the dictionary of the language (None: no dictionary)."""
    from spellchecker import SpellChecker

    if language not in _SPELL:
        try:
            _SPELL[language] = SpellChecker(language=language)
        except Exception:
            _SPELL[language] = None
    spell = _SPELL[language]
    ws = [w for w in words(text) if len(w) >= 3 and w.isalpha()]
    if spell is None or not ws:
        return None
    known = spell.known(set(ws))
    return sum(w in known for w in ws) / len(ws)


def _line_key(text: str) -> str:
    return re.sub(r"\d+", "#", re.sub(r"\s+", " ", unicodedata.normalize("NFKC", text).strip().lower()))


def _furniture_key(text: str) -> str:
    key = _line_key(text)
    return "#" if re.fullmatch(r"(page )?#( of #)?", key) else key


EDGE = 0.09  # running headers and footers are in the top and bottom 9% of a page


def _visual_lines(page) -> list[tuple[int, str]]:
    """The lines of text as seen on the page (words at the same height joined left to right), as (height key,
    text), whatever pieces the PDF stores its text in (some store every word on its own)."""
    rows: dict = {}
    for x0, y0, x1, y1, w, *_ in page.get_text("words"):
        rows.setdefault(round((y0 + y1) / 2 / 3), []).append((x0, w))
    return [(k, " ".join(w for _, w in sorted(v))) for k, v in sorted(rows.items())]


def running_lines(pdf_path: str, pages: range) -> tuple[list[str], set]:
    """Page furniture of the original: lines repeated at the top or bottom of several pages (running headers and
    footers, with page numbers made alike), and page numbers standing alone. Returns their texts (one per
    occurrence) and where they are ({(page, height key)})."""
    import pymupdf

    found: dict = {}
    with pymupdf.open(pdf_path) as doc:
        for n in pages:
            page = doc[n]
            h = page.rect.height
            for k, text in _visual_lines(page):
                if not (k * 3 < h * EDGE or k * 3 > h * (1 - EDGE)):
                    continue
                found.setdefault(_furniture_key(text), []).append((n, k))
    need = max(2, int(len(pages) * 0.3))
    texts, where = [], set()
    for key, places in found.items():
        if len(places) >= need or key == "#":
            texts += [key] * len(places)
            where.update(places)
    return texts, where


def clutter_left(furniture: list[str], out_lines: list[str]) -> float:
    """Share of the furniture lines that did not come through into the conversion's text."""
    if not furniture:
        return None
    have = Counter()
    for line in out_lines:
        have[_furniture_key(line)] += 1
    need = Counter(furniture)
    left = sum(min(have[k], c) for k, c in need.items())
    return 1 - left / sum(need.values())


def headings_found(outline: list[str], headings: list[str]) -> float | None:
    """Share of the PDF's bookmarks found among the conversion's headings (close matches count)."""
    from rapidfuzz import fuzz

    outline = [t for t in outline if len(words(t)) >= 1]
    if not outline:
        return None
    found = 0
    for t in outline:
        a = " ".join(words(t))
        if any(fuzz.ratio(a, " ".join(words(h))) >= 85 or  # the same, or one inside the other (3+ words)
               (len(words(t)) >= 3 and a in " ".join(words(h))) or
               (len(words(h)) >= 3 and " ".join(words(h)) in a) for h in headings):
            found += 1
    return found / len(outline)


# ----------------------------------------------------------------------------- one document
def converted(session, settings) -> tuple[str, list[str], list[str]]:
    """(text, lines, headings) of the conversion as the reader gets it (the converter's own closing note left out)."""
    result = session.compose(settings)
    lines, heads = [], []
    for it in result.items:
        if it.kind == "about":
            continue
        text = "".join(r.text for r in it.runs)
        if it.table is not None:
            text = "\n".join(" ".join(row) for row in it.table.rows)
        if it.marker:
            text = f"{it.marker} {text}"
        lines.append(text)
        if it.kind in ("title", "heading", "box_heading"):
            heads.append(text)
    return "\n".join(lines), lines, heads


def settings_for_measuring():
    from dyslexia_converter.settings import PRESETS

    s = PRESETS["Standard"].copy()
    s.move_citations = False  # citations stay in their sentences, so sentences can be compared with the original
    return s


def reference_text(pdf_path: str, pages: range, pictures: dict | None = None, skip: set | None = None) -> str:
    """The PDF's own text of ``pages``, in its reading order. A word drawn more than once at the same place (some
    archives stack their text layer) counts once. Words inside ``pictures`` ({page: [rect]}: figures and formulas
    the conversion shows as pictures of the original) and on the lines in ``skip`` ({(page, height key)}: page
    furniture) are left out."""
    import pymupdf

    out = []
    with pymupdf.open(pdf_path) as doc:
        for n in pages:
            rects = [pymupdf.Rect(r) for r in (pictures or {}).get(n, [])]
            seen, line, last = set(), [], None
            for x0, y0, x1, y1, w, block, ln, _ in doc[n].get_text("words"):
                if (n, round((y0 + y1) / 2 / 3)) in (skip or ()):
                    continue
                if any(r.contains(pymupdf.Point((x0 + x1) / 2, (y0 + y1) / 2)) for r in rects):
                    continue
                key = (w, round(x0 / 2), round(y0 / 2))
                if key in seen:
                    continue
                seen.add(key)
                if (block, ln) != last and line:
                    out.append(" ".join(line))
                    line = []
                last = (block, ln)
                line.append(w)
            if line:
                out.append(" ".join(line))
    return "\n".join(out)


def pictures_of(doc) -> dict:
    """{page: [rect]} of the blocks the conversion shows as pictures of the original (figures, formulas)."""
    out: dict = {}
    for b in doc.blocks:
        if b.image is not None and b.bbox and b.page is not None:
            out.setdefault(b.page, []).append(tuple(b.bbox))
    return out


def measure_pdf(path: str, reference: str | None, settings, assistant=None, pages=None) -> dict:
    """Scores for one PDF (or its first ``pages``). ``reference``: a text PDF with the true text (the file itself
    for text PDFs, the source of a scan made from one), or None."""
    import pymupdf

    from dyslexia_converter import pipeline

    t0 = time.time()
    session = pipeline.load(path, settings, pages=(1, pages) if pages else None)
    ai = None
    if assistant is not None:
        before = len(assistant.log.entries())
        summary = session.run_ai(assistant, settings)
        ai = {"summary": summary, "requests": len(assistant.log.entries()) - before}
    doc = session.document
    text, lines, heads = converted(session, settings)
    out = words(text)
    with pymupdf.open(path) as pdf:
        n = pdf.page_count if not pages else min(pages, pdf.page_count)
        # bookmarks that only name a page or picture ("image 3", "Page 12") are not headings
        outline = [t for lvl, t, p in pdf.get_toc() if 0 <= p - 1 < n and
                   not re.fullmatch(r"(image|page|pg|p|scan|figure|fig)\.?\s*\d+", t.strip(), re.I)] if not pages else []
    res = {"pages": n, "pdf_type": doc.pdf_type, "language": doc.language, "seconds": round(time.time() - t0, 1)}
    if reference == path and doc.pdf_type != "text":
        reference = None  # its own text layer is incomplete (the converter reads pages with OCR): no answer key
    if ai:
        res["ai"] = ai
    if reference:
        # a text PDF measured against itself: its figures are pictures in both; a scan: nothing is left out
        # the content is the text without its page furniture (whether that is removed is measured on its own)
        furniture, where = running_lines(reference, range(n))
        ref_text = reference_text(reference, range(n), pictures_of(doc) if reference == path else None, where)
        ref = words(ref_text)
        res["content_kept"], res["nothing_added"] = bag_scores(ref, out)
        res["sentences_intact"] = runs_intact(ref, out)
        res["clutter_removed"] = clutter_left(furniture, lines)
        mine, theirs = real_word_share(text, doc.language), real_word_share(ref_text, doc.language)
        res["real_words"] = min(1.0, mine / theirs) if mine is not None and theirs else None
    else:
        res["clutter_removed"] = clutter_left(running_lines(path, range(n))[0], lines)
        res["real_words"] = real_word_share(text, doc.language)
    res["headings_found"] = headings_found(outline, heads)
    return res


def scanned_copy(src: str, dst: str, pages: int, dpi: int = 200) -> None:
    """An image-only copy of the first pages of a PDF, as from a copier: grey, slightly skewed, JPEG."""
    import pymupdf
    from PIL import Image

    out = pymupdf.open()
    with pymupdf.open(src) as doc:
        for n in range(min(pages, doc.page_count)):
            pix = doc[n].get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
            im = Image.frombytes("L", (pix.width, pix.height), pix.samples)
            im = im.rotate(0.4, resample=Image.BICUBIC, expand=False, fillcolor=255)
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=80)
            page = out.new_page(width=doc[n].rect.width, height=doc[n].rect.height)
            page.insert_image(page.rect, stream=buf.getvalue())
    out.save(dst)


def measure_web(page: dict, folder: Path) -> dict:
    """Scores for one saved web page: the article kept (its sentences found), the clutter left out, headings and
    real words. ``page``: {"file", "keep": [...], "drop": [...], "headings": [...]}."""
    from dyslexia_converter import pipeline
    from dyslexia_converter.extract import web

    html = (folder / page["file"]).read_text(encoding="utf-8", errors="replace")
    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        try:
            title, article, lang = web.extract_article(html, page.get("url", ""))
        except web.WebPageError as e:
            return {"error": str(e), "article_kept": 0.0, "clutter_removed": None}
        saved = Path(tmp) / "page.html"
        saved.write_text(f"<html lang=\"{lang or 'en'}\"><head><meta charset='utf-8'><title>{title}</title>"
                         f"</head><body>{article}</body></html>", encoding="utf-8")
        s = settings_for_measuring()
        session = pipeline.load(str(saved), s)
        text, lines, heads = converted(session, s)
    flat = " ".join(words(text))
    keep = [k for k in page["keep"]]
    kept = sum(" ".join(words(k)) in flat for k in keep) / len(keep) if keep else None
    drop = page.get("drop", [])
    removed = sum(" ".join(words(d)) not in flat for d in drop) / len(drop) if drop else None
    res = {"article_kept": kept, "clutter_removed": removed, "seconds": round(time.time() - t0, 1),
           "real_words": real_word_share(text, session.document.language)}
    if page.get("headings"):
        res["headings_found"] = headings_found(page["headings"], heads)
    return res


def overall(res: dict) -> float | None:
    vals = [res[k] for k in METRICS + ("article_kept",) if res.get(k) is not None]
    return sum(vals) / len(vals) if vals else None


# ----------------------------------------------------------------------------- the run
def make_assistant(provider: str, home: Path):
    from dyslexia_converter.ai.assistant import Assistant, AICache
    from dyslexia_converter.ai.keystore import KeyStore
    from dyslexia_converter.settings import AISettings

    store = KeyStore(home)
    if not store.env_key(provider):
        raise SystemExit(f"No key for {provider}: set its environment variable (the key is never stored).")
    from dyslexia_converter.ai.log import RequestLog

    return Assistant(AISettings(mode="ai_assisted", provider=provider, consent_given=True), keystore=store,
                     cache=AICache(home / "ai_cache.json"), log=RequestLog(home / "ai_requests.jsonl"))


def run(args) -> None:
    from dyslexia_converter import __version__

    corpus = json.loads((BENCH / "corpus.json").read_text(encoding="utf-8"))
    docs = Path(args.docs)
    home = Path(tempfile.mkdtemp(prefix="dc-bench-"))
    os.environ["DYSLEXIA_CONVERTER_HOME"] = str(home)  # nothing of the benchmark stays in the app's own data
    modes = ["local"] + (["ai"] if args.ai else [])
    results = {"version": __version__, "date": time.strftime("%Y-%m-%d"), "ai_provider": args.ai or None,
               "documents": {}, "ocr_test": {}, "web": {}}
    settings = settings_for_measuring()
    try:
        assistant = make_assistant(args.ai, home) if args.ai else None
        for item in corpus["documents"]:
            name = item["name"]
            if args.only and name not in args.only:
                continue
            path = docs / item["file"]
            if not path.exists():
                print(f"skipped {name}: {path} not found", flush=True)
                continue
            ref = docs / item["reference"] if item.get("reference") else None
            entry = {"group": item["group"], "title": item.get("title", name)}
            for mode in modes:
                try:
                    r = measure_pdf(str(path), str(ref) if ref else None if item.get("scan") else str(path),
                                    settings, assistant if mode == "ai" else None)
                except Exception as e:  # a crash is a result too
                    r = {"error": repr(e)}
                r["overall"] = overall(r)
                entry[mode] = r
                print(f"{mode:5} {name:16} " + "  ".join(f"{LABELS[k]} {r[k] * 100:5.1f}"
                                                         for k in METRICS + ("overall",) if r.get(k) is not None),
                      flush=True)
            results["documents"][name] = entry
            complete = entry["local"].get("pdf_type") == "text"  # its own text is the answer key of the OCR test
            if not args.no_ocr_test and not item.get("scan") and complete:
                with tempfile.TemporaryDirectory() as tmp:
                    scan = str(Path(tmp) / "scan.pdf")
                    scanned_copy(str(path), scan, OCR_TEST_PAGES)
                    ocr = {"group": item["group"]}
                    for mode in modes:
                        try:
                            r = measure_pdf(scan, str(path), settings, assistant if mode == "ai" else None,
                                            pages=OCR_TEST_PAGES)
                        except Exception as e:
                            r = {"error": repr(e)}
                        r.pop("headings_found", None)
                        r["overall"] = overall(r)
                        ocr[mode] = r
                        print(f"{mode:5} {name + ' (scan)':16} " + "  ".join(
                            f"{LABELS[k]} {r[k] * 100:5.1f}" for k in METRICS + ("overall",) if r.get(k) is not None),
                            flush=True)
                    results["ocr_test"][name] = ocr
        for folder, pages in [(BENCH / "web", json.loads((BENCH / "web" / "pages.json").read_text("utf-8"))),
                              (docs, corpus.get("web", []))]:
            for page in pages:
                if args.only and page["name"] not in args.only:
                    continue
                if not (folder / page["file"]).exists():
                    print(f"skipped {page['name']}: not found", flush=True)
                    continue
                r = measure_web(page, folder)
                r["overall"] = overall(r)
                results["web"][page["name"]] = {"title": page.get("title", page["name"]),
                                                "real_page": page.get("real", False), "local": r}
                print(f"web   {page['name']:16} " + "  ".join(f"{LABELS[k]} {r[k] * 100:5.1f}" for k in
                                                          ("article_kept", "clutter_removed", "headings_found",
                                                           "real_words", "overall") if r.get(k) is not None),
                      flush=True)
    finally:
        shutil.rmtree(home, ignore_errors=True)
    out = Path(args.out or BENCH / "results" / f"{__version__}-{'-'.join(modes)}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"written {out}")
    summary(results)


def _mean(values) -> float | None:
    values = [v for v in values if v is not None]
    return statistics.fmean(values) if values else None


def summary(results: dict) -> None:
    """Averages per group and mode."""
    groups: dict = {}
    for part, rows in (("documents", results["documents"]), ("ocr_test", results["ocr_test"])):
        for name, entry in rows.items():
            for mode in ("local", "ai"):
                if mode in entry:
                    key = (entry["group"] + (" (OCR test)" if part == "ocr_test" else ""), mode)
                    groups.setdefault(key, []).append(entry[mode])
    for name, entry in results["web"].items():
        groups.setdefault(("Web pages", "local"), []).append(entry["local"])
    print(f"\n{'group':34} {'mode':5} " + " ".join(f"{LABELS[k][:10]:>10}" for k in METRICS + ("article_kept", "overall")))
    for (group, mode), rows in sorted(groups.items()):
        cells = []
        for k in METRICS + ("article_kept", "overall"):
            m = _mean(r.get(k) for r in rows)
            cells.append(f"{m * 100:10.1f}" if m is not None else f"{'-':>10}")
        print(f"{group:34} {mode:5} " + " ".join(cells))


def compare(args) -> None:
    """Differences between two result files, per document and score (in percentage points)."""
    a, b = (json.loads(Path(p).read_text(encoding="utf-8")) for p in (args.a, args.b))
    print(f"{a['version']} ({a['date']}) -> {b['version']} ({b['date']})")
    for part in ("documents", "ocr_test", "web"):
        for name in sorted(set(a[part]) | set(b[part])):
            for mode in ("local", "ai"):
                x, y = a[part].get(name, {}).get(mode), b[part].get(name, {}).get(mode)
                if not x or not y:
                    continue
                diffs = [f"{LABELS[k]} {(y[k] - x[k]) * 100:+.1f}" for k in METRICS + ("article_kept", "overall")
                         if x.get(k) is not None and y.get(k) is not None and abs(y[k] - x[k]) >= 0.005]
                if diffs:
                    print(f"{part:9} {name:16} {mode:5} " + ", ".join(diffs))


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--docs", required=True, help="folder with the documents listed in benchmarks/corpus.json")
    r.add_argument("--only", nargs="*")
    r.add_argument("--ai", choices=["mistral", "anthropic", "gemini"])
    r.add_argument("--no-ocr-test", action="store_true")
    r.add_argument("--out")
    c = sub.add_parser("compare")
    c.add_argument("a")
    c.add_argument("b")
    args = p.parse_args()
    run(args) if args.cmd == "run" else compare(args)


if __name__ == "__main__":
    main()
