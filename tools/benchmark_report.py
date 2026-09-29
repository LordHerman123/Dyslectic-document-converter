"""The benchmark report: one HTML page with charts from benchmark results (see tools/benchmark.py).

    python tools/benchmark_report.py benchmarks/results/1.15.0-local.json [older results ...] -o report.html

The first file is the run shown; older result files (optional) add a "versions" chart, so later versions can be
compared with this one.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

TEMPLATE = Path(__file__).with_name("benchmark_report.html")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("results", nargs="+")
    p.add_argument("-o", "--out", default="benchmarks/report.html")
    args = p.parse_args()
    runs = [json.loads(Path(f).read_text(encoding="utf-8")) for f in args.results]
    corpus = json.loads((Path(__file__).resolve().parents[1] / "benchmarks" / "corpus.json").read_text("utf-8"))
    titles = {d["name"]: d.get("title", d["name"]) for d in corpus["documents"]}
    data = json.dumps({"runs": runs, "titles": titles}, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.read_text(encoding="utf-8").replace("/*DATA*/null", data)
    Path(args.out).write_text(html, encoding="utf-8")
    print(f"written {args.out}")


if __name__ == "__main__":
    main()
