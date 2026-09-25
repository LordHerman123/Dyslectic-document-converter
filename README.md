# Dyslexia Converter

Converts PDFs (academic papers, textbooks, reports) into cleaner, more
dyslexia-friendly layouts that are easy to read on screen and to print on A4.

**It reformats the document. It never rewrites it.** The converter does not summarise, paraphrase,
simplify or drop text. Every optional change (OCR fixes, moving citations, moving footnotes, bolding
the start of words) is stored separately from the extracted text, can be switched off, and can be undone.
Your original PDF is only ever read, never modified.

Everything works **locally and without AI**. AI is an optional extra that you turn on with your own
API key. When it's on, it only sees small snippets that the local rules couldn't decide.

## Download for Windows (version 1.3)

Get `DyslexiaConverter-1.3.1-setup.exe` (installer) or `DyslexiaConverter-1.3.1-windows.zip` (unzip and
double-click `DyslexiaConverter.exe`) from the repository's **Releases** page. Text recognition (Tesseract)
is included; nothing else needs to be installed. How the Windows build is made: [windows/README.md](windows/README.md).

## Quick start (from source)

```bash
pip install -r requirements.txt
# for scanned PDFs, also install Tesseract OCR:
#   Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-nld
#   macOS:         brew install tesseract tesseract-lang
#   Windows:       https://github.com/UB-Mannheim/tesseract/wiki

python main.py                                  # desktop app
python -m dyslexia_converter paper.pdf          # command line -> paper_readable.pdf
```

Command-line examples:

```bash
python -m dyslexia_converter paper.pdf -f docx --preset Spacious
python -m dyslexia_converter paper.pdf --font OpenDyslexic --size 14 --bold-start --reading-width 13
python -m dyslexia_converter scan.pdf --language nl --ocr-correction automatic
python -m dyslexia_converter chapter.pdf --pages 3-18 --move-citations -f printable_pdf
```

## What it does

| Area | Details |
|---|---|
| PDF input | Checks each page for selectable text, scanned images, or both. Reports whether OCR was used. Password-protected PDFs get a clear error. Optional page range. |
| OCR | Tesseract (English, Dutch, German, French, Spanish, Italian, Portuguese — whichever language packs are installed). Rebuilds lines, paragraphs, headings and reading order. Pictures and ruled tables on scanned pages are kept as images. |
| Book scans & photocopies | Pages made of image tiles, with or without a copier's hidden text layer, are recognised as scans. Each scan is cleaned before reading: two-page spreads are split at the gutter, gutter shadows and uneven lighting are flattened, dark scanner borders are removed, each page is straightened (deskewed), and sideways or upside-down scans are turned the right way up. Words broken across lines or pages are rejoined. Book running headers ("12 CHAPTER TITLE" / "Section 13") are removed, section headings and epigraphs are recognised, and numbered photo captions stay with their picture. Pages are OCR'd in parallel at 225 dpi, and the result is saved on this device, so reopening the same PDF takes well under a second. Without Tesseract, the scanner's own text layer is used when there is one; pages where that text is garbled are shown as pictures of the original, with a note. |
| OCR correction | Uses local dictionaries (pyspellchecker: English, Dutch, German, French, Spanish, Italian, Portuguese) plus the typical OCR mix-ups (`rn`→`m`, `l`→`i`, `0`→`o`, …). Only high-confidence fixes are applied automatically. Modes: Automatic, Review (Accept/Reject in the app) and Off. The review shows the whole sentence around each word, with the word highlighted. If neither the scan nor the suggestion is right (for example a word split in two, like “diffe ent”), the pencil (Edit) lets you retype the sentence; only the words you change are stored, as your own correction, and Undo brings back the scanned text. Names, abbreviations, identifiers, British/American spellings, words that are correct in another of these languages (such as a quoted French term) and your own dictionary words are left alone. |
| Structure | Title, authors, numbered and unnumbered headings with levels, paragraphs (rejoined across columns and pages), bullet and numbered lists, captions linked to their figure or table, footnotes, references and running headers/footers. All of this uses simple rules based on font size, weight, typeface, position, white space and numbering. The PDF's own bookmarks are used when present. |
| Reading order | Multi-column aware (recursive XY-cut): column 1 is read before column 2, and full-width titles and figures stay in place. |
| Tables | Ruled tables and caption-anchored tables without rules are rebuilt as real tables that repeat the header row and can split across pages. If a table can't be rebuilt reliably, it's kept as a picture of the original. |
| Images | Raster images and vector figures (charts drawn as paths, including their labels) are kept. Captions stay with their figure. Logos and badges are hidden by default (there's a setting to show them). |
| Typography | Font (Atkinson Hyperlegible, OpenDyslexic, Verdana, Arial, Tahoma, DejaVu Sans, Liberation Sans), font size, line spacing, paragraph spacing, letter spacing, word spacing, alignment (left by default), four page margins, and a separate reading-width limit. |
| Bold word starts | Optional bolding of the first part of each word: first letter, 25%, 40% or automatic. Punctuation, URLs, numbers, identifiers and acronyms are skipped, and so are citations and references unless you switch that on. |
| Citations | Optional: author-year citations become `[n]` markers that point to the numbered reference list. Unmatched citations get their own list, and the original citation text is always kept. Numeric citations, ranges (`[3–7]`) and lists (`[2, 5, 8]`) are recognised. Uncertain cases are left unchanged, or passed to the AI if you allow it. |
| Footnotes | Optional: footnotes move to a Notes section at the end, with `[Note n]` markers in the text. Page notes such as affiliations and licences are kept too. |
| Document map | Clickable headings in the app, PDF bookmarks, and a Contents page. Headings in DOCX exports show up in Word's Navigation pane. |
| Preview | Original, converted, or both side by side, with page navigation. Changing a setting re-renders the preview without re-reading the PDF. |
| Export | PDF, printable PDF (no tints or backgrounds, black text), DOCX, plain text and Markdown. PDFs are A4, keep selectable Unicode text and embed font subsets. Headings stay with the text that follows them, and paragraphs avoid widow and orphan lines. |
| Settings | Presets: Standard, Spacious, High Readability, Compact print and My Settings. Settings are saved between sessions and can be reset to the defaults. |
| App settings | A Settings tab with the app language (English, Nederlands, Français, Deutsch, Español, Italiano; the device language is used at first start), dark mode, high-contrast colours and app text size. These change straight away, even with a document open, and only affect the app, not your exported documents. The tab also shows where Tesseract was found, lets you clear saved OCR results, and shows where your settings are stored. The look is burgundy & champagne on warm cream (a dark wine colour in dark mode), matching the "Dc" logo. |
| Document language | Detected automatically from each PDF's text and shown next to *Detect automatically*. You can pick English, Dutch, German, French, Spanish, Italian or Portuguese yourself if the guess is wrong: it sets the dictionary for OCR, OCR corrections and rejoining split words. Words the converter adds to a document (Contents, Notes, `[Note 1]`, the "About this version" note) follow the document's language, e.g. *Inhoud*, *Noten*, `[Noot 1]`. The author's text is never translated. |

The **Standard** preset copies the look of the example conversions: a Verdana-like sans (DejaVu Sans) at
13 pt, 1.6 line spacing, 14 pt between paragraphs, a left-aligned column about 15 cm wide on a cream page
panel, bold headings with a thin rule, shaded boxes for the abstract, and shaded table headers.

Presets are formatting configurations only. They are not medical treatments and are not guaranteed to
help every reader. No single font is best for everyone.

## Optional AI

Open *AI settings* in the app and pick **AI-assisted**. The app shows a notice saying that snippets
will be sent to your provider using your key, and nothing is sent until you confirm it. Then:

* Pick a provider: **Mistral AI** (the default; its free "Experiment" plan gives you a key at
  console.mistral.ai, and `mistral-small-latest` is preselected), **Anthropic** (paid API) or
  **Google Gemini**. Choose a model, then enter your key. The key can also be supplied through the
  `MISTRAL_API_KEY`, `ANTHROPIC_API_KEY` or `GEMINI_API_KEY` environment variable. Keys go into the OS keychain when `keyring` is installed.
  Otherwise they're saved in a private file on your device. Keys never go into settings, logs,
  error messages or exports.
* The AI is only asked narrow questions: "is this parenthesis a citation?" and "is this word an OCR
  error?". It gets short snippets, a few at a time. It can't rewrite text: answers that aren't a
  single-word fix are thrown away. AI word suggestions always go to your review list.
* Answers are cached, so the same content is never sent twice. The app shows how many requests were
  made and roughly how many characters were sent.
* Your AI provider may charge for API usage. **Local-only** mode stops everything from leaving the device.

## Project layout

```
dyslexia_converter/
  model.py              Document / Block / Correction data model (immutable source text)
  settings.py           FormatSettings, presets, JSON persistence
  fonts.py              bundled + system fonts, substitution notes
  extract/
    pdf_reader.py       page-type detection, text+layout, figures, tables, OCR pages
    ocr.py              OcrEngine interface + Tesseract engine (swap for Android ML Kit)
    layout.py           multi-column reading order (XY-cut)
  structure/detector.py deterministic structure detection
  transform/
    spelling.py         dictionary OCR correction, custom words, language detection
    citations.py        citation detection + reference matching
    bionic.py           first-part-of-word bolding ranges
  render/
    compose.py          document + settings -> neutral render model (all reversible transforms)
    pdf_writer.py       ReportLab PDF with letter/word spacing, font fallback, outline, TOC
    docx_writer.py      Word export
    text_writer.py      text / Markdown export
    preview.py          page images for the preview
    labels.py           words the converter adds (Contents, Notes...) in the document's language
  ai/                   optional: providers, consent, cache, key storage, redaction
  pipeline.py           load() once, then compose/export as often as settings change
  cli.py                command line
  ui/app.py             Flet app (desktop / web / Android)
  ui/i18n.py            app languages; ui/translations.py holds every text in all six languages
  ui/theme.py           burgundy & champagne light and dark colours
tests/                  pytest suite (generates its own sample PDFs, incl. a scanned one)
```

The processing pipeline is the one from the specification:
`PDF → type detection → text/OCR → structure → OCR correction → citations (local, then optional AI)
→ layout/compose → preview → PDF/DOCX/TXT/MD`. The stages are separate modules. The UI only calls
`pipeline.load()`, `Session.export()` and a few session methods, so a different front end, such as a
native Android app, can reuse the core.

## Tests

```bash
pip install pytest
python -m pytest            # OCR tests are skipped automatically if Tesseract is missing
```

The tests check, among other things, that every paragraph of the original appears word for word in the
output for every preset, that the original PDF's bytes are unchanged after all exports, and that the AI
layer refuses to send anything without consent and never sends the same content twice.

## Android

See [docs/ANDROID.md](docs/ANDROID.md).

## Licences

* Bundled fonts: Atkinson Hyperlegible (SIL OFL 1.1), OpenDyslexic (Bitstream Vera licence), DejaVu Sans
  (Bitstream Vera / public domain) and Liberation Sans (SIL OFL). The licence files are in
  `dyslexia_converter/assets/fonts/`. Arial, Verdana and Tahoma are used only if they're installed on
  the device. Otherwise a similar free font is substituted and the app tells you.
* **PyMuPDF is AGPL-3.0** (a commercial licence is available from Artifex). That's fine for personal use
  and for open-source distribution under the AGPL. Publishing a closed-source app, for example on the Play
  Store, needs either AGPL compliance or a commercial PyMuPDF licence.
