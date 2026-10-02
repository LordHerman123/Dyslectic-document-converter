# Taking the app to Android

The code is split so the Android version doesn't need a rewrite:

* **Core** (`dyslexia_converter/` without `ui/`): plain Python with no UI code. File access goes through
  paths and bytes. The app data folder comes from `FLET_APP_STORAGE_DATA` or `DYSLEXIA_CONVERTER_HOME`.
* **UI** (`dyslexia_converter/ui/app.py`): Flet, which is Flutter underneath. The same UI already runs on
  desktop and in a browser. On narrow screens it switches to separate *Settings* and *Preview* tabs.
* **OCR** sits behind the `OcrEngine` interface in `extract/ocr.py`, so a phone-friendly engine can be
  plugged in without touching the rest.

## Status (branch `android_dev`)

* **Building:** the *Android build* workflow (`.github/workflows/android-build.yml`) runs `flet build apk` on
  every push to `android_dev`. The APKs (one per processor type; phones and tablets almost always need
  `arm64-v8a`) are under the workflow run's *Artifacts*. Install one on a device with "install unknown apps"
  allowed for your browser or file manager.
* **Packages:** Flet's Android index (pypi.flet.dev) has every native package the converter needs for Python
  3.12 to 3.14: PyMuPDF, NumPy, Pillow, RapidFuzz, lxml and pyjnius. The rest is pure Python.
* **Reading aloud** uses the device's own voices (Android `TextToSpeech` through pyjnius, see
  `AndroidEngine` in `speech.py`): every installed offline voice and language, at the chosen speed. Android
  does not tell Python which word is being said, so the highlight is paced along the sentence. The natural
  (Piper) voices are desktop-only for now: Piper's speech sounds component has no Android build.
* **Phone screens:** focus mode fits the page to the screen width and its top bar scrolls sideways; the
  reading view (*Read along*) suits a phone best, because the text itself reflows.
* **Not yet:** OCR of scanned pages (no Tesseract on Android, see point 2 below), opening files shared from
  other apps, and testing on real devices.

## Route 1: Flet APK (same code base)

```bash
pip install "flet[all]>=1.0,<2"
flet build apk          # uses main.py and [tool.flet] in pyproject.toml
```

Before shipping, check these:

1. **Binary packages.** Flet builds Python packages for Android from its mobile package index.
   `reportlab`, `python-docx`, `pyspellchecker`, `httpx` and `pillow` are pure Python or widely available.
   `pymupdf` and `rapidfuzz` are native and must be available for Android/arm64 in that index; check the
   current list. Fallbacks if one is missing:
   * `rapidfuzz` is only used for Levenshtein distance and fuzzy matching of TOC titles. It's easy to
     replace with a small pure-Python function.
   * `pymupdf` is used for reading PDFs, rendering previews and finding tables. `pypdfium2` (rendering)
     together with `pdfplumber` (text and tables) could replace it behind the same `pdf_reader` functions.
2. **OCR.** `pytesseract` calls the `tesseract` program, which doesn't exist on Android. Choose one of:
   * Google ML Kit Text Recognition (on-device and free), called through a small Flutter/Kotlin
     extension that returns words with bounding boxes. Wrap it in a class that implements `OcrEngine`
     (`recognize(png, languages) -> OcrResult`).
   * Tesseract4Android with bundled `eng`/`nld` traineddata, used the same way.

   Until then, the app converts text PDFs on Android and shows a clear message for scanned pages, which
   are kept as images rather than dropped.
3. **Files.** `FilePicker.pick_files()` and `save_file(src_bytes=...)` already use the Android system
   file dialogs. The app works on a private copy and never writes to the picked PDF.
4. **API keys.** On Android, keys are saved in a private file in the app's own storage, which other
   apps can't read. For extra protection you can add Android Keystore encryption later.

## Route 2: native Kotlin app

If you later want a fully native app (Jetpack Compose UI):

* Keep this Python core as the reference behaviour and test suite, and embed it with **Chaquopy**
  (Python inside an Android app). The UI calls `pipeline.load(...)` and `Session.export(...)`.
  Native wheel availability applies here too; see Route 1, point 1.
* Or port it module by module. Each stage is small and covered by tests (`tests/`), which makes a
  port checkable. Android equivalents: PdfRenderer or PdfiumAndroid (rendering), PdfBox-Android (text
  and positions), ML Kit (OCR), and a Kotlin layout writer using `android.graphics.pdf.PdfDocument` or
  iText/OpenPDF for export.

## UI guidelines for the Android version

* Keep the tab order: Settings → Preview → OCR review → Document map → AI settings → Help.
* Large touch targets and no animations: tab animations are already off. Keep the app text-size and
  high-contrast options.
* Keep the mode chip in the header ("Local-only" or "AI-assisted") so it's always clear whether content
  can leave the device.
