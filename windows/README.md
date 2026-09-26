# Windows release (version 1.3)

Everything needed to turn the app into a Windows program you can send to other people.
Recipients don't need Python or Tesseract: both are included.

| File | Purpose |
|---|---|
| `build.py` | Packages the app with `flet pack` (PyInstaller), adds Tesseract + language data, writes the zip. |
| `installer.iss` | Inno Setup script: turns the app folder into `DyslexiaConverter-<version>-setup.exe`. |
| `app.ico`, `app.png` | Program icon (the "Dc" logo). Redraw them with `python windows/make_icon.py`. |
| `make_icon.py`, `logo_font/` | Draws the logo (Playfair Display "D" + Varela Round "c", both SIL OFL; used for the logo only) and writes `app.ico`, `app.png` and the in-app `assets/icon.png` + `assets/logo_small.png`. |
| `README_FOR_USERS.txt` | Copied into the app folder as `README.txt` for recipients. |
| `THIRD_PARTY_NOTICES.txt` | Licences of the included software (copied into `LICENSES/`). |

## Getting the .exe (no setup on your PC)

The GitHub workflow `.github/workflows/windows-release.yml` builds the release on a Windows machine:

* **Publishing a release:** push a tag such as `v1.6.2` (or create a release on GitHub with that tag). The
  workflow builds, runs a real conversion with the finished `.exe` as a self-test, and attaches two
  downloads to the GitHub release:
  * `DyslexiaConverter-1.6.2-setup.exe` — an installer (per user, no administrator rights needed), or
  * `DyslexiaConverter-1.6.2-windows.zip` — unzip anywhere and double-click `DyslexiaConverter.exe`.
* **Test builds:** every pull request that touches the app also builds, and the files are available
  under the workflow run's *Artifacts*. You can also start a build manually from the *Actions* tab.

## Building on your own Windows PC

```powershell
# once: Python 3.11+, Tesseract (https://github.com/UB-Mannheim/tesseract/wiki), and optionally Inno Setup
pip install -r requirements.txt pyinstaller "flet-cli>=1.0,<2" "flet-desktop>=1.0,<2"
python windows\build.py                    # -> dist\DyslexiaConverter\ and dist\DyslexiaConverter-1.6.2-windows.zip
iscc windows\installer.iss                 # optional -> dist\DyslexiaConverter-1.6.2-setup.exe
```

`build.py` copies the installed Tesseract (from `C:\Program Files\Tesseract-OCR`, or `--tesseract-dir`)
into the app folder and downloads missing language data (English, Dutch, German, French, Spanish,
Italian, Portuguese). The app always prefers the Tesseract bundled next to the `.exe`.

Check a build without opening the window:

```powershell
dist\DyslexiaConverter\DyslexiaConverter.exe --selftest some.pdf out.pdf report.txt
```

## Notes

* **Version:** set in `dyslexia_converter/__init__.py` (`__version__`); the build, installer and the app's
  Help tab all use it. Bump it and push a new tag for the next release.
* **SmartScreen:** the program isn't code-signed, so Windows shows "Windows protected your PC" the first
  time. Users click *More info → Run anyway*. A code-signing certificate removes this (optional, paid).
* **Size:** about 250 MB installed (Python, the PDF engine, the UI runtime, Tesseract and 7 languages).
* **Licences:** PyMuPDF is AGPL-3.0. Sharing this open-source app is fine; distributing a closed-source
  or commercial version needs a commercial PyMuPDF licence.
