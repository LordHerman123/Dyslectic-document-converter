"""Build the Windows release of Dyslexia Converter (a folder with DyslexiaConverter.exe + bundled Tesseract).

Run on Windows from the repository root:

    python windows/build.py                     # uses an installed Tesseract (C:\\Program Files\\Tesseract-OCR)
    python windows/build.py --tesseract-dir D:\\tesseract
    python windows/build.py --no-tesseract       # app only (scans then use the scanner's own text)

Output (in dist/):
    DyslexiaConverter/                        the app folder: double-click DyslexiaConverter.exe
    DyslexiaConverter-<version>-windows.zip   the same folder zipped, ready to send to people

The GitHub workflow .github/workflows/windows-release.yml runs this script on a Windows machine
and also wraps the folder into an installer (windows/installer.iss).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "windows"
APP_NAME = "DyslexiaConverter"
# Tesseract language data shipped with the app (the app's document languages + orientation detection)
LANGUAGES = ["eng", "nld", "deu", "fra", "spa", "ita", "por", "osd"]
PYINSTALLER_EXTRA = ["--collect-data=spellchecker", "--collect-data=docx", "--collect-data=reportlab",
                     "--collect-submodules=dyslexia_converter", "--hidden-import=pytesseract",
                     "--collect-submodules=pyttsx3", "--collect-submodules=comtypes"]  # speech drivers load by name
TESSDATA_URL = "https://github.com/tesseract-ocr/tessdata/raw/main/{lang}.traineddata"


def version() -> str:
    ns: dict = {}
    exec((ROOT / "dyslexia_converter" / "__init__.py").read_text(encoding="utf-8"), ns)
    return ns["__version__"]


def run(cmd: list[str]) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, cwd=ROOT)


def find_installed_tesseract() -> Path | None:
    candidates = []
    for var in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
        base = os.environ.get(var)
        if base:
            candidates += [Path(base) / "Tesseract-OCR", Path(base) / "Programs" / "Tesseract-OCR"]
    exe = shutil.which("tesseract")
    if exe:
        candidates.append(Path(exe).resolve().parent)
    for c in candidates:
        if (c / "tesseract.exe").is_file() or (c / "tesseract").is_file():
            return c
    return None


def pack_app(dist: Path) -> Path:
    """Package the Flet app with PyInstaller (via `flet pack`) as a one-folder app."""
    sep = ";" if os.name == "nt" else ":"
    args = [
        sys.executable, "-m", "flet_cli.cli", "pack", "main.py",
        "--name", APP_NAME,
        "--icon", str(HERE / "app.ico"),
        "--onedir",
        "--distpath", str(dist),
        "--add-data", f"dyslexia_converter/assets{sep}dyslexia_converter/assets",
        "--product-name", "Dyslexia Converter",
        "--file-description", "Dyslexia Converter - readable PDFs",
        "--product-version", version(),
        "--file-version", ".".join((version().split(".") + ["0", "0", "0"])[:4]),
        "--company-name", "Dyslexia Converter",
        "--copyright", "Open source; see LICENSES",
        "-y",
    ]
    # extra PyInstaller options: data files the libraries load at runtime
    for extra in PYINSTALLER_EXTRA:
        args.append(f"--pyinstaller-build-args={extra}")
    run(args)
    folder = dist / APP_NAME
    if not folder.is_dir():
        raise SystemExit(f"Packaging failed: {folder} was not created")
    return folder


def add_tesseract(app: Path, source: Path, offline: bool) -> None:
    """Copy Tesseract next to the .exe and make sure the language data is there."""
    target = app / "tesseract"
    if target.exists():
        shutil.rmtree(target)
    print(f"Bundling Tesseract from {source}")
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("unins*", "*.html", "doc", "tessdata"))
    tessdata = target / "tessdata"
    tessdata.mkdir(exist_ok=True)
    src_data = source / "tessdata"
    if (src_data / "configs").is_dir():
        shutil.copytree(src_data / "configs", tessdata / "configs", dirs_exist_ok=True)
    for lang in LANGUAGES:
        dst = tessdata / f"{lang}.traineddata"
        if (src_data / dst.name).is_file():
            shutil.copy2(src_data / dst.name, dst)
        elif not offline:
            print(f"Downloading {lang}.traineddata")
            urllib.request.urlretrieve(TESSDATA_URL.format(lang=lang), dst)
        else:
            print(f"Warning: {lang}.traineddata not found and --offline given; language skipped")
    (target / "ABOUT.txt").write_text(
        "Tesseract OCR (https://github.com/tesseract-ocr/tesseract), Apache License 2.0.\n"
        "Windows build by UB Mannheim (https://github.com/UB-Mannheim/tesseract/wiki).\n"
        "Language data from https://github.com/tesseract-ocr/tessdata (Apache License 2.0).\n",
        encoding="utf-8")


def add_docs(app: Path, with_tesseract: bool) -> None:
    licenses = app / "LICENSES"
    licenses.mkdir(exist_ok=True)
    for f in (ROOT / "dyslexia_converter" / "assets" / "fonts").glob("LICENSE-*"):
        shutil.copy2(f, licenses / f.name)
    shutil.copy2(HERE / "THIRD_PARTY_NOTICES.txt", licenses / "THIRD_PARTY_NOTICES.txt")
    shutil.copy2(HERE / "README_FOR_USERS.txt", app / "README.txt")
    if not with_tesseract:
        with open(app / "README.txt", "a", encoding="utf-8") as fh:
            fh.write("\nNOTE: this copy was built without Tesseract. Scanned PDFs use the text the scanner "
                     "stored in the PDF. Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki "
                     "for better results.\n")


def make_zip(app: Path, dist: Path) -> Path:
    out = dist / f"{APP_NAME}-{version()}-windows.zip"
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for f in sorted(app.rglob("*")):
            if f.is_file():
                z.write(f, Path(APP_NAME) / f.relative_to(app))
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tesseract-dir", type=Path, help="folder containing tesseract.exe (default: installed copy)")
    ap.add_argument("--no-tesseract", action="store_true", help="build without bundling Tesseract")
    ap.add_argument("--offline", action="store_true", help="do not download missing language data")
    ap.add_argument("--dist", type=Path, default=ROOT / "dist")
    args = ap.parse_args()

    args.dist.mkdir(parents=True, exist_ok=True)
    app = pack_app(args.dist)
    with_tesseract = not args.no_tesseract
    if with_tesseract:
        source = args.tesseract_dir or find_installed_tesseract()
        if source is None:
            raise SystemExit("Tesseract not found. Install it (https://github.com/UB-Mannheim/tesseract/wiki), "
                             "pass --tesseract-dir, or use --no-tesseract.")
        add_tesseract(app, source, args.offline)
    add_docs(app, with_tesseract)
    z = make_zip(app, args.dist)
    size = sum(f.stat().st_size for f in app.rglob("*") if f.is_file()) / 1e6
    print(f"\nDone: {app}  ({size:.0f} MB)\nZip:  {z}  ({z.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
