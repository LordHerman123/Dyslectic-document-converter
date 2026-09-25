"""App entry point for `python main.py`, `flet run` and `flet build apk`."""
import flet as ft

from dyslexia_converter.ui.app import ASSETS_DIR, main

if __name__ == "__main__":
    ft.run(main, assets_dir=ASSETS_DIR)
