# Dyslexia Converter

Converts PDFs (academic papers, textbooks, reports) into cleaner, more
dyslexia-friendly layouts that are easy to read on screen and to print on A4.

**It reformats the document. It never rewrites it.** The converter does not summarise, paraphrase,
simplify or drop text. Every optional change (OCR fixes, moving citations, moving footnotes, bolding
the start of words) is stored separately from the extracted text, can be switched off, and can be undone.
Your original PDF is only ever read, never modified.

Everything works **locally and without AI**. AI is an optional extra that you turn on with your own
API key. When it's on, it only sees small snippets that the local rules couldn't decide.

## Download for Windows (version 1.10)

Get `DyslexiaConverter-1.10.0-setup.exe` (installer) or `DyslexiaConverter-1.10.0-windows.zip` (unzip and
double-click `DyslexiaConverter.exe`) from the repository's **Releases** page. Text recognition (Tesseract)
is included; nothing else needs to be installed. How the Windows build is made: [windows/README.md](windows/README.md).

## Quick start (from source)

```bash
pip install -r requirements.txt
# for scanned PDFs, also install Tesseract OCR:
#   Ubuntu/Debian: sudo apt install tesseract-ocr tesseract-ocr-nld
#   macOS:         brew install tesseract tesseract-lang
#   Windows:       https://github.com/UB-Mannheim/tesseract/wiki
# reading aloud uses the computer's voices; on Linux install eSpeak: sudo apt install espeak-ng

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
| Book scans & photocopies | Pages made of image tiles, with or without a copier's hidden text layer, are recognised as scans. Each scan is cleaned before reading: two-page spreads are split at the gutter, gutter shadows and uneven lighting are flattened, dark scanner borders are removed, each page is straightened (deskewed), lines that curve into the book's spine are straightened too, and sideways or upside-down scans are turned the right way up. Words broken across lines or pages are rejoined, also when OCR read stray marks next to the hyphen, and two words run together ("forthe") are split again. Letters at the page edge are kept when a box edge or scanner border runs down the same column. Book running headers ("12 CHAPTER TITLE" / "Section 13") are removed, section headings and epigraphs are recognised, and numbered photo captions stay with their picture. Pages are OCR'd in parallel at 225 dpi, and the result is saved on this device, so reopening the same PDF takes well under a second. Without Tesseract, the scanner's own text layer is used when there is one; pages where that text is garbled are shown as pictures of the original, with a note. |
| OCR correction | Uses local dictionaries (pyspellchecker: English, Dutch, German, French, Spanish, Italian, Portuguese) plus the typical OCR mix-ups (`rn`→`m`, `l`→`i`, `0`→`o`, …). Only high-confidence fixes are applied automatically. Modes: Automatic, Review (Accept/Reject in the app) and Off. The review shows the whole sentence around each word, with the word highlighted. If neither the scan nor the suggestion is right (for example a word split in two, like “diffe ent”), the pencil (Edit) lets you retype the sentence; only the words you change are stored, as your own correction, and Undo brings back the scanned text. Names, abbreviations, identifiers, British/American spellings, words that are correct in another of these languages (such as a quoted French term) and your own dictionary words are left alone. |
| Structure | Title, authors, numbered and unnumbered headings with levels, paragraphs (rejoined across columns and pages), bullet and numbered lists, captions linked to their figure or table, footnotes, references and running headers/footers. All of this uses simple rules based on font size, weight, typeface, position, white space and numbering. The PDF's own bookmarks are used when present. |
| Reading order | Multi-column aware (recursive XY-cut): column 1 is read before column 2, and full-width titles and figures stay in place. |
| Mathematics | Displayed equations (integrals, sums, fractions, matrices, cases, multi-line derivations, with their numbers) are kept exactly as typeset, as sharp pictures at the reading size, with their text as alt text. Long equations broken over lines are shown line by line; an equation number set far to the right is brought next to its formula. Inline formulas stay in the text in a Times-style serif (Times New Roman if installed, otherwise the bundled Liberation Serif), with real sub- and superscripts, ℝ/ℕ/ℂ and script letters, Greek, accents and primes; small stacked parts (an inline fraction, a sum with limits) are drawn as small pictures inside the line. Works with TeX fonts (Computer Modern, AMS, Times/mathptmx, MathTime, STIX, Cambria Math). On scanned pages, which OCR cannot read as maths, displayed formulas are kept as pictures of the page. |
| Tables | Ruled tables, booktabs tables (top, middle and bottom rules only), tables of up to 20 columns, long tables and caption-anchored tables without rules are rebuilt as real tables that repeat the header row and can split across pages. Bold cells (best scores) stay bold and wrapped header rows are joined. Tables full of formulas, and tables that can't be rebuilt reliably, are kept as a picture of the original. Sideways (landscape) tables are kept as a picture turned upright. |
| Images | Raster images and vector figures (charts drawn as paths, including their tick labels and axis titles) are kept. Figure panels side by side are read left to right, each as its own picture, and captions stay with their figure. Logos and badges are hidden by default (there's a setting to show them). |
| Typography | Font (Atkinson Hyperlegible, OpenDyslexic, Verdana, Arial, Tahoma, DejaVu Sans, Liberation Sans), font size, line spacing, paragraph spacing, letter spacing, word spacing, alignment (left by default), four page margins, and a separate reading-width limit. |
| Bold word starts | Optional bolding of the first part of each word: first letter, 25%, 40% or automatic. Punctuation, URLs, numbers, identifiers and acronyms are skipped, and so are citations and references unless you switch that on. |
| Citations | Optional: author-year citations become `[n]` markers that point to the numbered reference list. Unmatched citations get their own list, and the original citation text is always kept. Numeric citations, ranges (`[3–7]`) and lists (`[2, 5, 8]`) are recognised. Uncertain cases are left unchanged, or passed to the AI if you allow it. |
| Footnotes | Optional: footnotes move to a Notes section at the end, with `[Note n]` markers in the text. Page notes such as affiliations and licences are kept too. |
| Document map | Clickable headings in the app, PDF bookmarks, and a Contents page. Headings in DOCX exports show up in Word's Navigation pane. |
| Read aloud | The *Read aloud* button next to Original / Both / Converted opens the read-aloud controls (tap it again to fold them away). *Read aloud* reads the converted document from the page you are looking at, with the voices already on your computer (it works offline; nothing leaves the device). The sentence being read is highlighted, the word being said is boxed, and the pages turn along. One button reads, pauses and continues (a play triangle or pause bars show which); with *tap to read* switched on, click anywhere on the converted page to start reading there (to skip parts you do not need). Speed and voice can be set; the voice follows the document's language. On Windows 10/11 every voice installed in Windows Settings > Time & language > Speech can be used, so documents in Dutch, German, French and other languages are read in their own language; the app says so when a document's language has no voice yet. Desktop app only. |
| Focus mode | *Focus mode* shows the converted document in the whole window, like a PDF reader, so it can be read on a tablet or touch screen without another app. The top bar can be hidden for reading without distractions (Esc or the small button brings it back; on Windows the window goes full screen). Everything else folds out from the bar and away again: the read-aloud controls, the reading settings (font, size, spacing, alignment, bold word starts) and the **View** options: page colour (white, cream, blue, green, grey or dark), **Scroll** through all pages or read **Pages** one at a time (swipe, arrow keys or the side arrows turn the page), **Fit width**, and **Rotate** a quarter turn (for a tablet with screen rotation locked). Zoom with + and − or pinch with two fingers. A **reading ruler** keeps the line you are on clear and fades the rest; tap a line or use the arrow keys to move it, and it follows the voice when reading aloud. |
| Selecting and copying text | With a mouse or pen, drag over the text to select it, like in any PDF reader; double-click a word to select just that word. With a finger, dragging scrolls: press and hold a word, then drag. A slim toolbar appears at the bottom: **Copy**, the four highlight colours, **Note**, **Read** (reads the selection aloud), **Meaning** (for one word) and **•••**, which selects the whole sentence or paragraph and moves the start or end by a word. One tap on a colour highlights and closes the toolbar, with **Undo** in case of a mistake. Tap a highlight to change its colour, add a note, copy it, read it or **Remove** it. Click anywhere else, or press Esc, to clear the selection. Keys: Ctrl+C copies, 1-4 pick a colour, N adds a note, Delete removes a highlight. |
| Word card | Press and hold a word (or right-click it) to open its card: the word in syllables, a button that says it, and what it means. English meanings come from a dictionary inside the app (Open English WordNet), so nothing leaves the device; it also finds the base word (*ran* → *run*, *theories* → *theory*). For other languages the card shows the syllables and offers *Look up online* (Wiktionary, opened in your browser only when you ask). |
| Highlights and notes | A highlighter marks words in yellow, green, blue or pink with a finger, pen or mouse (drag over the words, or tap one word); the eraser removes marks. **Add note** on a card opens the note editor: the words quoted, the colour, and your note, typed or spoken (on Windows the microphone starts Windows voice typing). A note sign in the margin shows where a note is; tap it to read the note, have it read aloud, or edit it. The **notes list** beside the pages shows every highlight and note in reading order, filtered by colour or to those with notes; tap one to go to it, and *Export notes as a list* saves them as a Word document (page, colour, the words quoted and your note) for writing or revising. Highlights and notes are kept on this device per document and stay on the same words when the layout changes. When a document has highlights, the Export menu offers *Include my highlights (PDF)*: the PDF and printable PDF then carry them as ordinary highlight marks, and each note as the highlight's comment, which any PDF reader shows and can remove. |
| Preview | Original, converted, or both side by side, with page navigation. In *Both*, turning a page on one side turns the other side along to the matching content. Changing a setting re-renders the preview without re-reading the PDF. |
| Export | One *Export* button (also in focus mode) opens a menu: PDF, printable PDF (no tints or backgrounds, black text), DOCX, EPUB, plain text and Markdown. PDFs are A4, keep selectable Unicode text and embed font subsets, and are *tagged*: screen readers and read-aloud tools (such as Acrobat's Read Out Loud) follow the headings and paragraphs in order, read formulas and figures from their description, and skip page numbers. The EPUB is a reflowable book for e-readers, tablets and phones: the reading app can change font, size and colours, notes and citations are links, and it passes epubcheck. Headings stay with the text that follows them, and paragraphs avoid widow and orphan lines. |
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
  error?". It can't rewrite text: answers that aren't a single-word fix are thrown away. AI word
  suggestions always go to your review list.
* **As little data as possible.** Each uncertain item is sent with only a few words around it (about 8
  before and 6 after), never whole paragraphs or pages, with the item marked `[[like this]]`. E-mail
  addresses, web links, account numbers and long numbers such as phone numbers are masked first (`[email]`,
  `[link]`, `[number]`); years and year ranges are kept because citations need them.
* **Preview before sending.** *Ask AI about uncertain items now* first shows exactly which document text
  would be sent and how much. Nothing leaves the device until you press *Send*.
* **Privacy log.** Every request is written to a log on your device: the time, provider and model, the
  exact text that was sent, the answer that came back, and the number of tokens. See it in the AI settings
  tab, save it as a text file or clear it. The last 500 requests are kept. The key is never part of it.
* **Few tokens.** Up to 30 items go in one request. Answers only list the exceptions (the ids that are
  citations, the words that are OCR errors), so they are a few tokens long, and the maximum answer
  length is set to match. Answers are cached per item, so the same item is never sent twice, even across
  documents; duplicate snippets in one document are sent once. Gemini's "thinking" is switched off and
  Anthropic runs at low effort, since these are simple yes/no questions. Anthropic gets a JSON schema,
  Mistral and Gemini JSON mode, and an answer that isn't valid JSON is rejected.
* **Worked examples (few-shot).** Each question comes with fixed instructions and 8-10 made-up worked
  examples, including tricky ones (a statistic in brackets, a date range, an abbreviation, a Dutch
  citation, a name that looks misspelled, a wrong spelling suggestion). This part holds nothing from your
  document and is the same for every request. Providers cache repeated prompt starts only above a minimum
  length, which this part (about 350 tokens) is below, so it is
  paid for with each request; sharing it across 30 items keeps that small.
* Your AI provider may charge for API usage. **Local-only** mode stops everything from leaving the device.

## Project layout

```
dyslexia_converter/
  model.py              Document / Block / Correction data model (immutable source text)
  settings.py           FormatSettings, presets, JSON persistence
  fonts.py              bundled + system fonts, substitution notes
  extract/
    pdf_reader.py       page-type detection, text+layout, figures, tables, OCR pages
    scan.py             scan clean-up: spreads, shadows, borders, skew, curled lines
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
    preview.py          page images for the preview (with the read-aloud highlight and highlighter marks)
    pdf_tags.py         tagged PDF structure for screen readers
    epub_writer.py      EPUB 3 export
    labels.py           words the converter adds (Contents, Notes...) in the document's language
  ai/                   optional: providers, prompts (few-shot), privacy masking, request log,
                        consent, cache, key storage, redaction
  speech.py             reading aloud: sentences with their place on the page, speech thread
  highlights.py         highlighter marks and notes in focus mode, kept per document
  dictionary.py         word card: offline English meanings, syllables, online look-up link
  pipeline.py           load() once, then compose/export as often as settings change
  cli.py                command line
  ui/app.py             Flet app (desktop / web / Android)
  ui/focus.py           focus mode: whole-window page reader with highlighter
  ui/i18n.py            app languages; ui/translations.py holds every text in all six languages
  ui/theme.py           burgundy & champagne light and dark colours
tests/                  pytest suite (generates its own sample PDFs, incl. a scanned one)
```

The processing pipeline is the one from the specification:
`PDF → type detection → text/OCR → structure → OCR correction → citations (local, then optional AI)
→ layout/compose → preview → PDF/DOCX/EPUB/TXT/MD`. The stages are separate modules. The UI only calls
`pipeline.load()`, `Session.export()` and a few session methods, so a different front end, such as a
native Android app, can reuse the core.

## For developers

Every module, class and function has a docstring that says what it does and why. Start with
`pipeline.py` (the core's front door) and `ui/app.py` (the window). Some pointers:

* **Flow of a document.** `pipeline.load()` reads the PDF (`extract/pdf_reader.read_pdf`, with OCR through
  `extract/ocr.py` for scanned pages) and detects its structure (`structure/detector.StructureDetector`)
  into a `model.Document`. `Session.export()` composes it for the settings (`render/compose.compose`) and
  hands the result to a writer in `render/`. The source text is never changed: OCR corrections and the
  user's edits are kept separately and applied when composing.
* **Adding a layout setting.** Add a field to `settings.FormatSettings` (and to the presets if needed),
  use it in `render/compose.py` or a writer, and add a control in `ConverterApp.build_convert_tab`
  (`self.slider`, `self.switch` or `self.dropdown` connect it to the setting).
* **Adding an app text.** Wrap it in `t("...")`; `tests/test_i18n.py` fails until
  `ui/translations.py` has it in every app language.
* **Adding an export format.** Write a `build_...(result, settings)` function in `render/`, add it to
  `Session.export()` and to `EXPORTS` in `ui/app.py`.
* **Focus mode.** `ui/focus.py` shows the converted PDF as page pictures (`render/preview.render_highlight`
  draws highlights, the reading ruler, the word being read and the page colour on them). Highlights
  and notes are in `highlights.py`, the word card's dictionary in `dictionary.py`.
* **Seeing the app while developing.** `flet run --web main.py` opens it in the browser.

## Tests

```bash
pip install pytest
python -m pytest            # OCR tests are skipped automatically if Tesseract is missing
```

`tests/stress` holds small LaTeX stress documents (mathematics in every shape, a two-column paper,
wrapped/rotated/long/wide tables and charts, Times-font maths with margin notes) that the tests convert.

The tests check, among other things, that every paragraph of the original appears word for word in the
output for every preset, that the original PDF's bytes are unchanged after all exports, and that the AI
layer refuses to send anything without consent and never sends the same content twice.

## Android

See [docs/ANDROID.md](docs/ANDROID.md).

## Licences

* Bundled fonts: Atkinson Hyperlegible (SIL OFL 1.1), OpenDyslexic (Bitstream Vera licence), DejaVu Sans
  (Bitstream Vera / public domain), Liberation Sans and Liberation Serif (SIL OFL; Liberation Serif is
  used for formulas when Times New Roman isn't installed). The licence files are in
  `dyslexia_converter/assets/fonts/`. Arial, Verdana and Tahoma are used only if they're installed on
  the device. Otherwise a similar free font is substituted and the app tells you.
* **PyMuPDF is AGPL-3.0** (a commercial licence is available from Artifex). That's fine for personal use
  and for open-source distribution under the AGPL. Publishing a closed-source app, for example on the Play
  Store, needs either AGPL compliance or a commercial PyMuPDF licence.
* The English dictionary is derived from Open English WordNet 2022 (CC BY 4.0) and Princeton WordNet
  (WordNet licence); see `dyslexia_converter/assets/dictionary/`. It is rebuilt with
  `python tools/build_dictionary.py wordnet2022.zip`. Syllables use the hyphenation patterns of pyphen
  (LGPL/GPL/MPL).
