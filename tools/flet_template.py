"""The `flet build` app shell, changed so that the Mac and Linux apps open a document given at start.

The stock shell (Flet's build template) takes the first command-line argument as the address of a development
server. An app started with a document ("Open with", a PDF dropped on the app's icon) then tries to connect to
that file and stays blank. This unpacks the template of the installed Flet version and lets a document path or
file:// address through to the app instead; a real development address (tcp://, http://, a socket path) still
works as before.

    python tools/flet_template.py OUT_DIR

prints the template folder to pass to `flet build --template`.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

MAIN_DART = "{{cookiecutter.out_dir}}/lib/main.dart"
ANCHOR = "Map<String, String> environmentVariables = Map.from(Platform.environment);\n"
HELPERS = """
// A document given on the command line ("Open with", a file dropped on the app's icon) is for the app, not the
// address of a development server (added by tools/flet_template.py of Dyslexia Converter).
bool _isDocument(String arg) {
  final a = arg.toLowerCase();
  return a.startsWith("file:") ||
      [".pdf", ".docx", ".epub", ".html", ".htm"].any((ext) => a.endsWith(ext));
}

bool _devMode() => _args.isNotEmpty && !_isDocument(_args[0]);
"""
# (old, new, how many times the old text must occur)
CHANGES = [
    (ANCHOR, ANCHOR + HELPERS, 1),
    ("(isDesktopPlatform() && _args.isNotEmpty)", "(isDesktopPlatform() && _devMode())", 2),
    ("} else if (_args.isNotEmpty && isDesktopPlatform()) {", "} else if (_devMode() && isDesktopPlatform()) {", 1),
]


def template_zip() -> Path:
    """The build template of the installed Flet version (downloaded once by Flet's own cache)."""
    import flet.version
    from flet_cli.commands.build_base import DEFAULT_TEMPLATE_URL
    from flet_cli.utils.template_cache import get_cached_template_zip

    version = flet.version.flet_version
    return get_cached_template_zip(DEFAULT_TEMPLATE_URL.format(version=version), version)


def patch(source: str) -> str:
    """main.dart with the changes; stops when the template no longer has the expected code."""
    for old, new, count in CHANGES:
        found = source.count(old)
        if found != count:
            raise SystemExit(f"flet_template: expected {count}x {old.strip()!r} in main.dart, found {found}; "
                             "the Flet build template changed, so check this patch")
        source = source.replace(old, new)
    return source


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "build/flet-template").resolve()
    with zipfile.ZipFile(template_zip()) as z:
        z.extractall(out)
    roots = [p.parent for p in out.rglob("cookiecutter.json")]
    if len(roots) != 1:
        raise SystemExit(f"flet_template: expected one template in the archive, found {len(roots)}")
    dart = roots[0] / MAIN_DART
    dart.write_text(patch(dart.read_text(encoding="utf-8")), encoding="utf-8")
    print(roots[0])


if __name__ == "__main__":
    main()
