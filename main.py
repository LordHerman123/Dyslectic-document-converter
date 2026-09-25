"""App entry point for `python main.py`, `flet run` and the packaged Windows app."""
import sys

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        from dyslexia_converter.selftest import run

        sys.exit(run(sys.argv[2:]))

    import flet as ft

    from dyslexia_converter.ui.app import ASSETS_DIR, main

    ft.run(main, assets_dir=ASSETS_DIR)
