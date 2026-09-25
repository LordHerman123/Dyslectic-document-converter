"""User settings, presets and persistence.

Presets are simply formatting configurations. They are not medical
treatments and are not guaranteed to help every reader.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path


@dataclass
class FormatSettings:
    # Typography
    # Defaults follow the look of the reference conversions the user liked:
    # Verdana-like sans at 13 pt, 1.6 line spacing, generous paragraph gaps,
    # a ~15 cm left-aligned column on a cream page panel.
    font: str = "DejaVu Sans"
    font_size: float = 13.0  # pt
    line_spacing: float = 1.6  # multiple of font size
    paragraph_spacing: float = 14.0  # pt after each paragraph
    letter_spacing: float = 0.0  # extra pt between characters
    word_spacing: float = 1.5  # extra pt between words
    alignment: str = "left"  # left / center / justify
    heading_scale: float = 1.0  # multiplier for heading sizes

    # Page (A4) and reading column, in cm
    margin_top: float = 2.5
    margin_bottom: float = 2.5
    margin_left: float = 2.8
    margin_right: float = 2.8
    reading_width: float = 15.0  # maximum text column width in cm

    # Bionic / first-part bolding
    bold_word_start: bool = False
    bold_amount: str = "auto"  # first_letter / 25 / 40 / auto
    bold_in_references: bool = False

    # Structure and transformations (all reversible)
    remove_headers_footers: bool = True
    move_citations: bool = False
    move_footnotes: bool = True
    include_contents: bool = True
    table_mode: str = "auto"  # auto / image
    show_decorative_images: bool = False  # logos, badges, ornaments

    # OCR
    ocr_language: str = "auto"  # auto / en / nl
    ocr_correction: str = "review"  # automatic / review / disabled
    ocr_confidence_threshold: float = 0.9
    correct_selectable_text: bool = False

    # Output
    page_tint: str = "cream"  # none / cream / blue (screen PDFs only)
    boxed_sections: bool = True  # shaded boxes for abstract / quotes, rules under headings
    about_note: bool = True  # short "about this version" note at the end
    ink_saving: bool = False
    text_color: str = "#1a1a1a"
    page_numbers: bool = True

    def copy(self, **changes) -> "FormatSettings":
        data = asdict(self)
        data.update(changes)
        return FormatSettings(**data)

    @classmethod
    def from_dict(cls, data: dict) -> "FormatSettings":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


PRESETS: dict[str, FormatSettings] = {
    "Standard": FormatSettings(),
    "Spacious": FormatSettings(
        font_size=14.0,
        line_spacing=1.8,
        paragraph_spacing=18.0,
        word_spacing=2.5,
        letter_spacing=0.3,
        reading_width=13.0,
    ),
    "High Readability": FormatSettings(
        font="Atkinson Hyperlegible",
        font_size=15.0,
        line_spacing=2.0,
        paragraph_spacing=20.0,
        word_spacing=3.0,
        letter_spacing=0.6,
        reading_width=12.0,
        heading_scale=1.15,
        bold_word_start=True,
    ),
    "Compact print": FormatSettings(
        font_size=11.5,
        line_spacing=1.45,
        paragraph_spacing=9.0,
        word_spacing=0.8,
        margin_top=2.0, margin_bottom=2.0, margin_left=2.0, margin_right=2.0,
        reading_width=16.0,
        page_tint="none",
        ink_saving=True,
    ),
}

PRESET_DISCLAIMER = (
    "Presets are formatting configurations only. They are not medical treatments "
    "and may not suit every reader - adjust any setting to what works for you."
)


@dataclass
class AISettings:
    mode: str = "local_only"  # local_only / ai_assisted
    provider: str = "mistral"  # mistral / anthropic / gemini
    model: str = ""
    consent_given: bool = False  # user accepted that content is sent to the provider
    use_for_citations: bool = True
    use_for_ocr: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "AISettings":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


def app_data_dir() -> Path:
    """Per-user writable directory (works on desktop and inside Flet on Android)."""
    env = os.environ.get("DYSLEXIA_CONVERTER_HOME") or os.environ.get("FLET_APP_STORAGE_DATA")
    if env:
        path = Path(env)
    elif sys.platform.startswith("win"):
        path = Path(os.environ.get("APPDATA", Path.home())) / "DyslexiaConverter"
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / "DyslexiaConverter"
    else:
        path = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "dyslexia-converter"
    path.mkdir(parents=True, exist_ok=True)
    return path


@dataclass
class SettingsStore:
    """Loads and saves settings as JSON in the app data directory."""

    directory: Path = field(default_factory=app_data_dir)

    @property
    def path(self) -> Path:
        return self.directory / "settings.json"

    def _read(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _write(self, data: dict) -> None:
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
        tmp.replace(self.path)

    def load_format(self) -> FormatSettings:
        data = self._read().get("format")
        return FormatSettings.from_dict(data) if data else FormatSettings()

    def save_format(self, settings: FormatSettings) -> None:
        data = self._read()
        data["format"] = asdict(settings)
        self._write(data)

    def has_saved_format(self) -> bool:
        return "format" in self._read()

    def load_ai(self) -> AISettings:
        data = self._read().get("ai")
        return AISettings.from_dict(data) if data else AISettings()

    def save_ai(self, settings: AISettings) -> None:
        data = self._read()
        data["ai"] = asdict(settings)  # never contains the API key
        self._write(data)

    def load_ui(self) -> dict:
        return self._read().get("ui", {})

    def save_ui(self, ui: dict) -> None:
        data = self._read()
        data["ui"] = ui
        self._write(data)

    def reset_format(self) -> FormatSettings:
        data = self._read()
        data.pop("format", None)
        self._write(data)
        return FormatSettings()

    def preset(self, name: str) -> FormatSettings:
        if name == "My Settings":
            return self.load_format()
        return PRESETS.get(name, FormatSettings()).copy()
