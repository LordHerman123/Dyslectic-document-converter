"""Build the offline English dictionary (dyslexia_converter/assets/dictionary/en.json.gz).

Source: Open English WordNet 2022 (CC BY 4.0, https://en-word.net), as packaged for NLTK:
    https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/corpora/wordnet2022.zip

Usage:  python tools/build_dictionary.py path/to/wordnet2022.zip

Kept per word (single words only): up to three meanings per part of speech, each with its first example,
plus WordNet's lists of irregular forms (went -> go, mice -> mouse), so the app can find the base word.
"""
from __future__ import annotations

import gzip
import json
import sys
import zipfile
from pathlib import Path

POS = {"noun": "n", "verb": "v", "adj": "a", "adv": "r"}
OUT = Path(__file__).resolve().parent.parent / "dyslexia_converter" / "assets" / "dictionary" / "en.json.gz"


def main(zip_path: str) -> None:
    z = zipfile.ZipFile(zip_path)
    root = next(n.split("/")[0] for n in z.namelist() if n.endswith("data.noun"))

    def lines(name: str):
        for line in z.read(f"{root}/{name}").decode("utf-8").splitlines():
            if line and not line.startswith(" "):
                yield line

    gloss = {}
    for name, p in POS.items():
        for line in lines(f"data.{name}"):
            head, _, text = line.partition(" | ")
            parts = [x.strip() for x in text.strip().split(";")]
            meaning = "; ".join(x for x in parts if x and not x.startswith('"'))
            example = next((x.strip('"') for x in parts if x.startswith('"')), "")
            gloss[(p, head.split()[0])] = (meaning, example)

    entries: dict[str, list] = {}
    for name, p in POS.items():
        for line in lines(f"index.{name}"):
            f = line.split()
            lemma = f[0]
            if "_" in lemma:  # phrases: the app looks up one word at a time
                continue
            senses, pointers = int(f[2]), int(f[3])
            offsets = f[4 + pointers + 2:4 + pointers + 2 + senses]
            entries.setdefault(lemma, []).extend([p, *gloss[(p, o)]] for o in offsets[:3])

    exc = {}
    for name, p in POS.items():
        pairs = {}
        for line in lines(f"{name}.exc"):
            form, *bases = line.split()
            if "_" not in form and bases and "_" not in bases[0]:
                pairs[form] = bases[0]
        exc[p] = pairs

    data = {"source": "Open English WordNet 2022 (CC BY 4.0, https://en-word.net)", "entries": entries, "exc": exc}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(gzip.compress(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode(), 9, mtime=0))
    print(f"{len(entries)} words, {OUT.stat().st_size / 1e6:.1f} MB -> {OUT}")


if __name__ == "__main__":
    main(sys.argv[1])
