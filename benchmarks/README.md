# Benchmarks

Numbers for how well documents come out of the converter, to compare versions with each other.

- `corpus.json`: the test documents (by file name; the files themselves are not in the repository, most are
  published papers) and the group each belongs to: journal papers, scans, printed web pages, test documents.
- `web/`: web pages made for the tests, with `pages.json` listing for each page the article's paragraphs that must
  be kept, the clutter that must go and its headings. A real saved page is listed in `corpus.json` (`web`).
- `results/`: one file per run, named after the version and modes (`1.15.0-local.json`).

## Running

```
python tools/benchmark.py run --docs FOLDER                 # local-only, plus the OCR test and web pages
python tools/benchmark.py run --docs FOLDER --ai mistral    # also AI-assisted (key from MISTRAL_API_KEY)
python tools/benchmark.py compare benchmarks/results/1.15.0-local.json benchmarks/results/NEW.json
python tools/benchmark_report.py benchmarks/results/NEW.json benchmarks/results/1.15.0-local.json -o report.html
```

The AI key is read from the provider's environment variable (`MISTRAL_API_KEY`, `ANTHROPIC_API_KEY`,
`GEMINI_API_KEY`) and never written anywhere; the run keeps nothing in the app's own data folder.

## The scores

All are percentages, higher is better, measured automatically (see the top of `tools/benchmark.py`):

| Score | Measures |
|---|---|
| Content kept | words of the original found in the conversion (figures and formulas shown as pictures, and page furniture, are not counted as lost) |
| Nothing added | words of the conversion found in the original (garbled or invented words lower it) |
| Sentences intact | runs of five words of the original still together: reading order, columns, split words |
| Clutter removed | running headers, footers and page numbers that did not end up in the text |
| Headings found | the PDF's bookmarks found as headings (PDFs with bookmarks, and web pages) |
| Real words | dictionary words, relative to the original's own share (plain share for scans without a known text) |
| Article kept | web pages: the article's paragraphs found |

The OCR test scans the first three pages of every text PDF (a slightly skewed 200 dpi grey JPEG image, as from a
copier) and measures the same scores on what text recognition reads back, with the PDF's own text as the answer.

Every run uses the same settings (the Standard preset with citations left in their sentences), so a change in a
score is a change in the converter.
