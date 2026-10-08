# Building the app for Windows, macOS and Linux

The same project builds the desktop app for all three systems with [Flet](https://flet.dev)'s `flet build`.
The Python code is shared; only the speech engine and how OCR (Tesseract) is found differ per system.
The build settings for each system are in `pyproject.toml` under `[tool.flet.windows]`, `[tool.flet.macos]` and
`[tool.flet.linux]`.

| | Windows | macOS | Linux |
|---|---|---|---|
| Built by | `windows-release.yml` (installer + zip, on a release tag) | `desktop-builds.yml` | `desktop-builds.yml` |
| Download | `…-setup.exe` / `…-windows.zip` | `…-macos-arm64.zip` (the `.app`) | `…-linux-x86_64.tar.gz` |
| Runs on | Windows 10 and 11 (64-bit) | macOS 11 or later on Apple Silicon (M1 and later) | 64-bit Linux with GTK 3 (Ubuntu 22.04 or later, Debian 12, Fedora 38, …) |
| Tesseract (OCR for scans) | included | install it: `brew install tesseract tesseract-lang` | install it: `sudo apt install tesseract-ocr` (+ `tesseract-ocr-nld` etc. for other languages) |
| Computer voices | Windows voices (all installed in Settings > Time & language > Speech) | the Mac's own voices (System Settings > Accessibility > Spoken Content) | eSpeak NG: `sudo apt install espeak-ng` |
| Natural voices (Piper) | yes | yes | yes |
| MP3 export | yes | yes | yes |
| Drop files on the window | — (use Open file, or drop on the app icon) | yes | yes |
| Voice typing for notes | microphone button (Windows voice typing) | macOS Dictation in the note (press Fn twice) | — |

Everything the app does with documents (conversion, focus mode, highlights and notes, exports, reading aloud) is
the same on all three.

## Getting the builds without setting anything up

Publishing a release (a tag such as `v1.17.0`) builds all three (*Windows release* and *Linux and macOS builds*) and attaches them to that release, so one page has the Windows, Mac and Linux downloads. Both
can also be started by hand from the *Actions* tab (*Run workflow*, choose the branch). Each runs the tests, then **starts the packaged app** and lets it convert a scanned PDF from inside it
(the same self-test as the Windows build: Python, the conversion, OCR with Tesseract, MP3 export and the natural
voices must all work). The files are under the workflow run's *Artifacts*.

## Building on your own computer

You need Python 3.10 or later and the project's packages:

```bash
pip install -r requirements.txt "flet-cli==1.0.1" "flet==1.0.1" "flet-dropzone==0.4.0"
touch dyslexia_converter/assets/dropzone.enabled      # optional: dropping files on the window
```

The first `flet build` downloads Flutter (about 1 GB) by itself.

### Windows

See [windows/README.md](../windows/README.md) (installer and zip with Tesseract included).

### macOS

```bash
xcode-select --install          # once; flet build also needs Xcode 26 or later (App Store) and CocoaPods:
brew install cocoapods tesseract tesseract-lang
flet build macos --arch arm64 --product "Dyslexia Converter" --project DyslexiaConverter
# -> build/macos/DyslexiaConverter.app
```

Xcode 26 is needed to *build* (Flutter's plugins use the newest macOS APIs); the app it makes still runs on
macOS 11 and later.

### Linux (Ubuntu / Debian)

```bash
sudo apt install clang cmake ninja-build pkg-config libgtk-3-dev liblzma-dev \
    libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev libsecret-1-dev
sudo apt install tesseract-ocr espeak-ng zenity      # what the app uses when it runs
flet build linux --product "Dyslexia Converter" --project DyslexiaConverter
# -> build/linux/DyslexiaConverter (run it from that folder; keep the folder together)
```

(Fedora: `sudo dnf install clang cmake ninja-build gtk3-devel xz-devel gstreamer1-devel
gstreamer1-plugins-base-devel libsecret-devel tesseract espeak-ng zenity`.)

### Checking a build

Every build can check itself without a person: start it with these two variables and it converts the given PDF
and writes what it found:

```bash
DYSLEXIA_CONVERTER_READY_FILE=$PWD/ready.txt \
DYSLEXIA_CONVERTER_SELFTEST="$PWD/scan.pdf;$PWD/out.pdf;$PWD/report.txt" \
  "build/linux/DyslexiaConverter"        # macOS: build/macos/DyslexiaConverter.app/Contents/MacOS/DyslexiaConverter
cat ready.txt report.txt                 # "selftest exit 0" when everything works
```

`.github/scripts/desktop-selftest.sh` does this for the CI builds.

## Limitations and notes per system

### macOS

* **Not signed:** the app is not signed with an Apple Developer ID, so the first time macOS says it "cannot be
  opened because Apple cannot check it for malicious software". **Right-click the app → Open → Open** (on macOS 15
  and later: try to open it once, then *System Settings → Privacy & Security → Open Anyway*). Only needed once.
  Signing and notarising (a paid Apple Developer account) removes this.
* **Apple Silicon only:** the natural voices need ONNX Runtime, which no longer ships for Intel Macs. An Intel
  Mac can run the app from source (`pip install -r requirements.txt`, then `python main.py`); the natural voices
  are then not available, everything else works.
* **Tesseract is not included** in the `.app` (unlike Windows): scanned PDFs need `brew install tesseract
  tesseract-lang`. The app finds it in `/opt/homebrew/bin` or `/usr/local/bin` by itself; documents with real text
  work without it.
* **Voices:** the app speaks with the Mac's built-in voices through its `say` program, which does not say which
  word it is on, so the marked word is paced along the sentence (the natural voices mark each word exactly). The
  Mac's joke voices ("Bad News", "Bells", …) are never picked automatically.

### Linux

* **Tesseract and eSpeak NG come from the system** (`sudo apt install tesseract-ocr espeak-ng`); the app works
  without them, but then cannot read scans or speak with computer voices (the natural voices still work).
* **Playing sound** uses `paplay` (PulseAudio / PipeWire), `aplay` (ALSA), `pw-play` or `ffplay`, whichever is
  there; every desktop has one of them.
* **Open and save windows** use `zenity` (GNOME) or `kdialog` (KDE); install one if they do not open.
* **x86-64 build:** the CI build is for 64-bit Intel/AMD PCs. ARM Linux (Raspberry Pi 5 and similar) can build it
  on that machine with the steps above.
* **Glibc:** the build is made on Ubuntu 22.04, so it runs on that and newer distributions; it may not start on
  older ones.

### Windows

Unchanged; see [windows/README.md](../windows/README.md). The app is not code-signed, so SmartScreen asks once
(*More info → Run anyway*).

## How the code handles the differences

* `dyslexia_converter/speech.py`: Windows uses its modern voices (WinRT) or SAPI; macOS its `say` program
  (`MacSayEngine`); Linux pyttsx3 with eSpeak NG. Natural voices (Piper) play through the system's sound
  (`winsound` on Windows, `afplay` on macOS, `paplay`/`aplay` on Linux).
* `dyslexia_converter/extract/ocr.py` (`find_tesseract`): a Tesseract next to the app first (Windows), then the
  system PATH, then the usual install folders (including Homebrew's on a Mac).
* `dyslexia_converter/settings.py`: the settings, highlights and downloaded voices are kept in the app's own data
  folder that Flet gives a built app; run from source, in `%APPDATA%\DyslexiaConverter` (Windows),
  `~/Library/Application Support/DyslexiaConverter` (macOS) or `~/.config/dyslexia-converter` (Linux).
