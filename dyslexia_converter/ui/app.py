"""Flet user interface (desktop, web, and Android via ``flet build apk``).

All document processing lives in the UI-independent core package; this
module only wires controls to it. Heavy work runs in a worker thread so the
interface stays responsive.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Callable, Optional

import flet as ft

from .. import pipeline, speech
from ..ai.assistant import PRIVACY_NOTICE, AIAssistant, ConsentRequired
from ..ai.keystore import KeyStore, install_log_redaction, redact
from ..ai.providers import PROVIDERS, AIError
from .. import DONATE_URL, PROJECT_URL, RELEASES_URL, __version__
from ..extract.ocr import default_engine, find_tesseract
from ..fonts import FONT_CHOICES, get_family
from ..render import preview
from ..settings import PRESET_DISCLAIMER, PRESETS, FormatSettings, SettingsStore
from ..transform.spelling import CustomWords
from .i18n import LANGUAGES, Translator, system_language
from .theme import make_theme, palette

log = logging.getLogger("dyslexia_converter")

# settings that change how the PDF is read, not just how it is laid out
RELOAD_KEYS = {"split_spreads", "scan_text_source", "ocr_language"}

EXPORTS = [("pdf", "PDF", "pdf"), ("printable_pdf", "Printable PDF", "pdf"), ("docx", "Word (DOCX)", "docx"),
           ("epub", "EPUB (e-reader)", "epub"), ("txt", "Plain text", "txt"), ("md", "Markdown", "md")]
# document languages (codes used by the core) and their English names (translated in the UI)
DOC_LANGUAGES = [("en", "English"), ("nl", "Dutch"), ("de", "German"), ("fr", "French"), ("es", "Spanish"),
                 ("it", "Italian"), ("pt", "Portuguese")]


def _speed_text(v: float) -> str:
    """1.0×, 1.25×, 0.5×"""
    s = f"{v:.2f}".rstrip("0")
    return (s + "0" if s.endswith(".") else s) + "×"


class ConverterApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.store = SettingsStore()
        self.settings: FormatSettings = self.store.load_format() if self.store.has_saved_format() \
            else PRESETS["Standard"].copy()
        self.ai_settings = self.store.load_ai()
        self.ui = {"text_scale": 1.0, "high_contrast": False, "dark_mode": False, **self.store.load_ui()}
        if self.ui.get("app_language") not in LANGUAGES:
            self.ui["app_language"] = system_language()
        self.t = Translator(self.ui["app_language"])
        self.keystore = KeyStore()
        self.assistant = AIAssistant(self.ai_settings, self.keystore)
        self.custom_words = CustomWords()
        self.session: Optional[pipeline.Session] = None
        self.source_path: Optional[str] = None
        self.converted_pdf: Optional[bytes] = None
        self.orig_page = 0
        self.conv_page = 0
        self.orig_count = 0
        self.conv_count = 0
        self.view_mode = "side"
        self.speaker = speech.Speaker()
        self._read_units: Optional[list] = None  # sentences of the converted PDF, made when reading starts
        self._read_pos: Optional[int] = None  # sentence being read (kept when paused)
        self._reading = False
        self._hl_busy = False
        self._hl_next: Optional[tuple[int, int]] = None
        self._render_task: Optional[asyncio.Task] = None
        self._controls: dict[str, ft.Control] = {}
        self.file_picker = ft.FilePicker()
        install_log_redaction()

    # ================================================================ helpers
    def fs(self, base: float = 15) -> float:
        return round(base * float(self.ui.get("text_scale", 1.0)), 1)

    def text(self, value: str, size: float = 15, **kw) -> ft.Text:
        return ft.Text(value, size=self.fs(size), **kw)

    def lang_name(self, code: str) -> str:
        return self.t(dict(DOC_LANGUAGES).get(code, code))

    def notify(self, message: str, error: bool = False) -> None:
        if error or len(message) > 90:
            # long or important messages stay visible in the notices panel instead of a pop-up
            self._notices = [("warning" if error else "info", message, None)] + getattr(self, "_notices", [])
            self._render_notices()
            self.page.update()
            return
        self.page.show_dialog(ft.SnackBar(ft.Text(message, size=self.fs(15)),
                                          bgcolor=ft.Colors.RED_700 if error else None,
                                          duration=ft.Duration(seconds=6 if error else 4)))

    # ---------------------------------------------------------------- notices
    def set_notices(self, notices: list[tuple[str, str, Optional[tuple[str, Callable]]]]) -> None:
        """Show (kind, message, optional (button label, handler)) notices below the header."""
        self._notices = list(notices)
        self._render_notices()

    def _render_notices(self) -> None:
        items = getattr(self, "_notices", [])
        self.notice_list.controls.clear()
        for idx, (kind, message, action) in enumerate(items):
            icon = {"warning": ft.Icons.WARNING_AMBER, "action": ft.Icons.TOUCH_APP}.get(kind, ft.Icons.INFO_OUTLINE)
            color = self.pal.get(f"notice_{kind}", self.pal["notice_info"])
            controls: list[ft.Control] = [ft.Icon(icon, size=20),
                                          ft.Text(self.t.message(message), size=self.fs(13), expand=True,
                                                  selectable=True)]
            if action:
                label, handler = action
                controls.append(ft.FilledButton(label, on_click=handler))
            controls.append(ft.IconButton(ft.Icons.CLOSE, tooltip=self.t("Dismiss"), data=idx,
                                          on_click=self._dismiss))
            self.notice_list.controls.append(ft.Container(
                ft.Row(controls, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                bgcolor=color, border_radius=8, padding=ft.Padding.symmetric(horizontal=10, vertical=4)))
        self.notices.visible = bool(items)
        # grow with the content up to a limit; beyond that the list scrolls
        self.notices.height = min(150, 52 * len(items)) if items else 0

    def _dismiss(self, e) -> None:
        idx = e.control.data
        if 0 <= idx < len(getattr(self, "_notices", [])):
            del self._notices[idx]
        self._render_notices()
        self.page.update()

    def _review_notice(self) -> Optional[tuple[str, str, Optional[tuple[str, Callable]]]]:
        if not self.session:
            return None
        pending = len(self.session.pending_corrections())
        if not pending:
            return None

        async def open_review(e):
            self.tabs.selected_index = self.review_tab_index
            self.page.update()

        msg = (self.t("1 word needs your decision: OCR wasn't sure how to read it.") if pending == 1 else
               self.t("{n} words need your decision: OCR wasn't sure how to read them.", n=pending))
        return ("action", msg, (self.t("Review now"), open_review))

    def update_review_notice(self) -> None:
        notices = [n for n in getattr(self, "_notices", []) if n[0] != "action"]
        rn = self._review_notice()
        self._notices = ([rn] if rn else []) + notices
        self._render_notices()

    async def in_thread(self, fn: Callable, *args):
        return await asyncio.to_thread(fn, *args)

    # ================================================================ build
    def build(self) -> None:
        p = self.page
        t = self.t
        p.title = f"Dyslexia Converter {__version__}"
        p.padding = 0
        self.apply_theme()
        self._controls = {}

        self.status = self.text(t("Open a PDF to start. Your original file is never changed."), 14,
                                max_lines=1, overflow=ft.TextOverflow.ELLIPSIS)
        self.progress = ft.ProgressBar(value=0, visible=False)
        # longer messages (warnings, decisions waiting) go here: wrapped, scrollable, dismissable
        self.notice_list = ft.Column(spacing=4, scroll=ft.ScrollMode.AUTO)
        self.notices = ft.Container(self.notice_list, visible=False, height=0)
        # a status (not a button): small icon + text, on the right of the top bar
        self.mode_icon = ft.Icon(self._mode_icon(), size=self.fs(18), color=self._mode_color())
        self.mode_text = self.text(self._mode_label(), 13, color=self.pal["muted"])
        self.mode_chip = ft.Row([self.mode_icon, self.mode_text], spacing=6, tight=True,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                tooltip=t("Where your document content is processed"))
        logo = ft.Image(src="logo_small.png", width=self.fs(38), height=self.fs(38), semantics_label="Logo",
                        filter_quality=ft.FilterQuality.HIGH)
        open_btn = ft.FilledButton(t("Open PDF"), icon=ft.Icons.FOLDER_OPEN, on_click=self.on_open,
                                   tooltip=t("Choose a PDF to convert"))
        header = ft.Container(
            ft.Row([
                ft.Row([logo, self.text("Dyslexia Converter", 22, weight=ft.FontWeight.BOLD), open_btn,
                        self.coffee_button()], spacing=12, wrap=True, expand=True,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                self.mode_chip,  # pushed to the far right
            ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10))

        narrow = (p.width or 1200) < 820
        settings_panel, preview_panel = self.build_convert_tab()
        if narrow:  # phones: layout settings and preview get their own tabs
            convert = [(t("Layout"), ft.Icons.TUNE, ft.Container(settings_panel, padding=12, expand=True)),
                       (t("Preview"), ft.Icons.PREVIEW, ft.Container(preview_panel, padding=8, expand=True))]
        else:
            convert = [(t("Convert"), ft.Icons.TUNE, ft.Row([
                ft.Container(settings_panel, width=400, padding=ft.Padding.only(left=12, right=4)),
                ft.VerticalDivider(width=1),
                ft.Container(preview_panel, expand=True, padding=8)], expand=True,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH))]
        self.preview_tab_index = 1 if narrow else 0
        self.review_tab_index = len(convert)
        tabs = convert + [
            (t("OCR review"), ft.Icons.SPELLCHECK, self.build_review_tab()),
            (t("Document map"), ft.Icons.ACCOUNT_TREE, self.build_map_tab()),
            (t("AI settings"), ft.Icons.SMART_TOY_OUTLINED, self.build_ai_tab()),
            (t("Settings"), ft.Icons.SETTINGS_OUTLINED, self.build_settings_tab()),
            (t("Help"), ft.Icons.HELP_OUTLINE, self.build_help_tab())]
        self.settings_tab_index = len(tabs) - 2
        self.tabs = ft.Tabs(
            length=len(tabs), selected_index=0, animation_duration=ft.Duration(milliseconds=0), expand=True,
            content=ft.Column([
                ft.TabBar(tabs=[ft.Tab(label=label, icon=i) for label, i, _ in tabs], scrollable=True),
                ft.TabBarView(controls=[c for _, _, c in tabs], expand=True),
            ], expand=True, spacing=0))
        p.add(ft.Column([header, ft.Container(ft.Column([self.status, self.progress, self.notices], spacing=4),
                                              padding=ft.Padding.symmetric(horizontal=16)),
                         self.tabs], expand=True, spacing=4))

    async def rebuild(self, tab: Optional[int] = None) -> None:
        """Build the whole window again (after changing the app language or text size), keeping the document."""
        first, last = self.tf_first.value, self.tf_last.value
        self.stop_reading()
        self.page.controls.clear()
        self.build()
        self.tf_first.value, self.tf_last.value = first, last
        if tab is not None:
            self.tabs.selected_index = tab
        if self.session:
            self.status.value = self.doc_status()
            self._update_doc_language_option()
            self.refresh_review()
            self.refresh_map()
            await self.show_pages()
        else:
            self._render_notices()
        self.page.update()

    def coffee_button(self) -> ft.Control:
        """Optional donation link; opens PayPal in the browser. Nothing is sent from the app."""
        return ft.FilledTonalButton(self.t("Like the app? Buy me a coffee"), icon=ft.Icons.COFFEE, url=DONATE_URL,
                                    tooltip=self.t("Opens PayPal in your web browser (optional)"))

    def apply_theme(self) -> None:
        dark = bool(self.ui.get("dark_mode"))
        self.pal = palette(dark, bool(self.ui.get("high_contrast")))
        # the app itself uses a bundled, highly legible font (works offline too)
        self.page.fonts = {"Atkinson": "fonts/AtkinsonHyperlegible-Regular.ttf"}
        theme = make_theme(self.pal, "Atkinson")
        self.page.theme = self.page.dark_theme = theme
        self.page.theme_mode = ft.ThemeMode.DARK if dark else ft.ThemeMode.LIGHT
        self.page.bgcolor = self.pal["bg"]

    def restyle(self) -> None:
        """Re-apply the palette to the few controls that carry their own colours."""
        self.apply_theme()
        self._update_mode_status()
        self.font_note.color = self.pal["muted"]
        for panel in (self.orig_panel, self.conv_panel):
            panel.controls[1].border = ft.Border.all(1, self.pal["frame"])
        self._render_notices()
        self.page.update()

    def _mode_label(self) -> str:
        if self.ai_settings.mode == "ai_assisted":
            return self.t("AI-assisted")
        return self.t("Local-only") if (self.page.width or 1200) < 820 else \
            self.t("Local-only: nothing leaves this device")

    def _mode_color(self) -> str:
        return self.pal["status_ai"] if self.ai_settings.mode == "ai_assisted" else self.pal["status_local"]

    def _mode_icon(self) -> str:
        return ft.Icons.CLOUD_OUTLINED if self.ai_settings.mode == "ai_assisted" else ft.Icons.LOCK_OUTLINE

    def _update_mode_status(self) -> None:
        self.mode_icon.icon = self._mode_icon()
        self.mode_icon.color = self._mode_color()
        self.mode_text.value = self._mode_label()
        self.mode_text.color = self.pal["muted"]

    # ---------------------------------------------------------------- convert tab
    def slider(self, key: str, label: str, lo: float, hi: float, step: float, unit: str) -> ft.Control:
        value_text = self.text(f"{getattr(self.settings, key):g} {unit}", 14)
        divisions = int(round((hi - lo) / step))

        def changed(e):
            v = round(float(e.control.value) / step) * step
            value_text.value = f"{v:g} {unit}"
            value_text.update()

        async def done(e):
            v = round(float(e.control.value) / step) * step
            setattr(self.settings, key, round(v, 2))
            await self.settings_changed()

        s = ft.Slider(value=getattr(self.settings, key), min=lo, max=hi, divisions=divisions,
                      label="{value}", on_change=changed, on_change_end=done, expand=True,
                      tooltip=label)
        self._controls[key] = s
        self._controls[key + "_text"] = value_text
        return ft.Column([ft.Row([self.text(label, 14), ft.Container(expand=True), value_text]), s], spacing=0)

    def switch(self, key: str, label: str, help_text: str = "") -> ft.Control:
        async def changed(e):
            setattr(self.settings, key, bool(e.control.value))
            await self.settings_changed(reload=key in RELOAD_KEYS)

        sw = ft.Switch(label=label, value=getattr(self.settings, key), on_change=changed,
                       label_text_style=ft.TextStyle(size=self.fs(14)), tooltip=help_text or label)
        self._controls[key] = sw
        return sw

    def dropdown(self, key: str, label: str, options: list[tuple[str, str]]) -> ft.Dropdown:
        async def changed(e):
            setattr(self.settings, key, e.control.value)
            await self.settings_changed(reload=key in RELOAD_KEYS)

        d = ft.Dropdown(label=label, value=str(getattr(self.settings, key)), expand=True,
                        options=[ft.DropdownOption(key=k, text=v) for k, v in options], on_select=changed,
                        text_size=self.fs(14))
        self._controls[key] = d
        return d

    def build_convert_tab(self) -> ft.Control:
        t = self.t
        presets = ["Standard", "Spacious", "High Readability", "Compact print", "My Settings"]
        self.preset_dd = ft.Dropdown(label=t("Preset"), value="", expand=True, text_size=self.fs(14),
                                     options=[ft.DropdownOption(key=p, text=t(p)) for p in presets],
                                     on_select=self.on_preset)
        self.font_note = self.text(self._font_note(), 12, color=self.pal["muted"])
        self.doc_lang_dd = self.dropdown("ocr_language", t("Document language"),
                                         [("auto", t("Detect automatically"))] +
                                         [(code, t(name)) for code, name in DOC_LANGUAGES])

        def section(title: str, controls: list[ft.Control], expanded: bool = False) -> ft.Control:
            return ft.ExpansionTile(title=self.text(title, 16, weight=ft.FontWeight.BOLD), expanded=expanded,
                                    controls=[ft.Container(ft.Column(controls, spacing=10),
                                                           padding=ft.Padding.only(left=8, right=8, top=8, bottom=10))],
                                    maintain_state=True)

        settings_col = ft.Column([
            ft.Row([self.preset_dd]),
            self.text(t(PRESET_DISCLAIMER), 12, italic=True),
            ft.Row([self.doc_lang_dd]),
            self.text(t("Detected from the text of each PDF. Choose a language if the guess is wrong: it sets the "
                        "dictionary for OCR, spelling fixes and rejoining split words."), 12),
            section(t("Text"), [
                ft.Row([self.dropdown("font", t("Font"), [(f, f) for f in FONT_CHOICES])]),
                self.font_note,
                self.slider("font_size", t("Font size"), 9, 24, 0.5, "pt"),
                self.slider("line_spacing", t("Line spacing"), 1.0, 3.0, 0.1, "×"),
                self.slider("paragraph_spacing", t("Paragraph spacing"), 0, 36, 1, "pt"),
                self.slider("letter_spacing", t("Letter spacing"), 0, 3, 0.1, "pt"),
                self.slider("word_spacing", t("Word spacing"), 0, 10, 0.5, "pt"),
                ft.Row([self.dropdown("alignment", t("Alignment"),
                                      [("left", t("Left (recommended)")), ("center", t("Centre")),
                                       ("justify", t("Justified"))])]),
            ], expanded=True),
            section(t("Page"), [
                self.slider("reading_width", t("Reading width"), 8, 17, 0.5, "cm"),
                self.slider("margin_top", t("Top margin"), 0.5, 5, 0.1, "cm"),
                self.slider("margin_bottom", t("Bottom margin"), 0.5, 5, 0.1, "cm"),
                self.slider("margin_left", t("Left margin"), 0.5, 5, 0.1, "cm"),
                self.slider("margin_right", t("Right margin"), 0.5, 5, 0.1, "cm"),
                ft.Row([self.dropdown("page_tint", t("Page colour (screen PDF)"),
                                      [("cream", t("Cream")), ("blue", t("Light blue")), ("none", t("White"))])]),
                self.switch("boxed_sections", t("Boxes for abstract & quotes, lines under headings")),
                self.switch("ink_saving", t("Ink-saving mode (no backgrounds or decorations)")),
                self.switch("page_numbers", t("Page numbers")),
                self.switch("include_contents", t("Contents page (document map)")),
            ]),
            section(t("Bold start of words"), [
                self.switch("bold_word_start", t("Bold the first part of each word"),
                            t("Changes only how words look, never the text")),
                ft.Row([self.dropdown("bold_amount", t("How much"),
                                      [("first_letter", t("First letter")), ("25", t("First 25%")),
                                       ("40", t("First 40%")), ("auto", t("Automatic"))])]),
                self.switch("bold_in_references", t("Also in references and citations")),
            ]),
            section(t("Structure"), [
                self.switch("move_footnotes", t("Move footnotes to the end")),
                self.switch("move_citations", t("Move author-year citations to numbers [1]"),
                            t("Automated citation detection can make mistakes. Original citation text is kept.")),
                self.text(t("Automated citation detection can make mistakes; the original citation text is "
                            "always kept in the list."), 12, italic=True),
                self.switch("remove_headers_footers", t("Hide running headers, footers and page numbers")),
                self.switch("show_decorative_images", t("Show logos and decorative images")),
                ft.Row([self.dropdown("table_mode", t("Tables"),
                                      [("auto", t("Rebuild as tables when reliable")),
                                       ("image", t("Always keep as picture"))])]),
                self.switch("about_note", t("Add an 'About this version' note at the end")),
            ]),
            section(t("Scanned documents (OCR)"), [
                ft.Row([self.dropdown("ocr_correction", t("OCR correction"),
                                      [("review", t("Review uncertain corrections")),
                                       ("automatic", t("Automatic (high confidence only)")),
                                       ("disabled", t("Off"))])]),
                self.switch("split_spreads", t("Split two-page book scans into single pages")),
                ft.Row([self.dropdown("scan_text_source", t("Text of scanned pages"),
                                      [("auto", t("Clean up and read the scan (best quality)")),
                                       ("text_layer", t("Use the scanner's own text layer (faster)"))])]),
                self.text(t("Scans are straightened, gutter shadows and dark borders are removed, and two-page "
                            "spreads are split before the text is read."), 12),
                self.text(t("OCR: Tesseract found") if default_engine() else
                          t("OCR: not available - install Tesseract to convert scanned PDFs. Scans that already "
                            "contain a text layer can still be converted."), 12),
            ]),
            section(t("Pages to convert"), [
                ft.Row([
                    tf_first := ft.TextField(label=t("From page"), value="", width=120,
                                             keyboard_type=ft.KeyboardType.NUMBER),
                    tf_last := ft.TextField(label=t("To page"), value="", width=120,
                                            keyboard_type=ft.KeyboardType.NUMBER),
                    ft.OutlinedButton(t("Apply"), on_click=self.on_page_range),
                ], wrap=True),
                self.text(t("Leave empty to convert all pages. Useful when a PDF starts with the end of "
                            "another article."), 12),
            ]),
            ft.Row([
                ft.FilledButton(t("Save as My Settings"), icon=ft.Icons.SAVE, on_click=self.on_save_settings),
                ft.OutlinedButton(t("Restore defaults"), icon=ft.Icons.RESTORE, on_click=self.on_restore_defaults),
            ], wrap=True),
        ], scroll=ft.ScrollMode.AUTO, spacing=8, expand=True)
        self.tf_first, self.tf_last = tf_first, tf_last

        # preview
        self.orig_img = ft.Image(src=_blank_png(), fit=ft.BoxFit.CONTAIN, expand=True,
                                 semantics_label=t("Original page"))
        self.conv_img = ft.Image(src=_blank_png(), fit=ft.BoxFit.CONTAIN, expand=True, gapless_playback=True,
                                 semantics_label=t("Converted page"))
        self.orig_label = self.text(t("Original"), 13)
        self.conv_label = self.text(t("Converted"), 13)
        self.view_seg = ft.SegmentedButton(
            segments=[ft.Segment(value="orig", label=ft.Text(t("Original"), no_wrap=True)),
                      ft.Segment(value="side", label=ft.Text(t("Both"), no_wrap=True)),
                      ft.Segment(value="conv", label=ft.Text(t("Converted"), no_wrap=True))],
            selected=[self.view_mode], show_selected_icon=False, on_change=self.on_view_mode)

        def nav(which: str, label: ft.Text) -> ft.Row:
            async def prev(e):
                await self.page_step(which, -1)

            async def nxt(e):
                await self.page_step(which, 1)

            return ft.Row([
                ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip=t("Previous page"), on_click=prev),
                label,
                ft.IconButton(ft.Icons.CHEVRON_RIGHT, tooltip=t("Next page"), on_click=nxt),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=2)

        self.orig_panel = ft.Column([nav("orig", self.orig_label),
                                     ft.Container(self.orig_img, expand=True,
                                                  border=ft.Border.all(1, self.pal["frame"]))],
                                    expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    visible=self.view_mode in ("orig", "side"))
        self.conv_panel = ft.Column([nav("conv", self.conv_label),
                                     ft.Container(self.conv_img, expand=True,
                                                  border=ft.Border.all(1, self.pal["frame"]))],
                                    expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    visible=self.view_mode in ("conv", "side"))
        export_buttons = [ft.OutlinedButton(t(label), icon=ft.Icons.DOWNLOAD, data=fmt, on_click=self.on_export,
                                            tooltip=t("Save as {format}", format=t(label)))
                          for fmt, label, _ in EXPORTS]
        preview_col = ft.Column([
            ft.Row([self.view_seg], wrap=True),
            self.build_read_bar(),
            ft.Row([self.orig_panel, self.conv_panel], expand=True, vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Row([self.text(t("Export:"), 14, weight=ft.FontWeight.BOLD)] + export_buttons, wrap=True),
        ], expand=True)

        return settings_col, preview_col

    def _update_doc_language_option(self) -> None:
        """Show the detected language next to 'Detect automatically'."""
        label = self.t("Detect automatically")
        if self.session and self.settings.ocr_language == "auto":
            label = self.t("Detect automatically (found: {language})",
                           language=self.lang_name(self.session.document.language))
        self.doc_lang_dd.options[0] = ft.DropdownOption(key="auto", text=label)

    # ---------------------------------------------------------------- review tab
    def build_review_tab(self) -> ft.Control:
        t = self.t
        self.review_summary = self.text(t("No scanned document loaded."), 14)
        self.review_list = ft.ListView(expand=True, spacing=8, padding=8)
        self.word_field = ft.TextField(label=t("Add a word to your dictionary"), width=280,
                                       on_submit=self.on_add_word)
        self.words_view = self.text(", ".join(sorted(self.custom_words.words)) or t("(none yet)"), 13)
        return ft.Container(ft.Column([
            self.text(t("OCR corrections"), 18, weight=ft.FontWeight.BOLD),
            self.text(t("Corrections use a local dictionary. The original OCR text is kept, so every "
                        "correction can be undone."), 13),
            self.review_summary,
            ft.Row([ft.OutlinedButton(t("Undo all corrections"), icon=ft.Icons.UNDO, on_click=self.on_undo_all)]),
            self.review_list,
            ft.Divider(),
            self.text(t("My dictionary (names, technical terms, abbreviations)"), 15, weight=ft.FontWeight.BOLD),
            ft.Row([self.word_field, ft.OutlinedButton(t("Add"), on_click=self.on_add_word)], wrap=True),
            self.words_view,
        ], expand=True), padding=16, expand=True)

    def refresh_review(self) -> None:
        t = self.t
        self.update_review_notice()
        self.review_list.controls.clear()
        if not self.session or not self.session.document.ocr_used:
            self.review_summary.value = t("No OCR was needed for this document.") if self.session else \
                t("No scanned document loaded.")
            return
        session = self.session
        corr = session.document.corrections
        pending = session.pending_corrections()
        mine = [c for c in corr if c.source == "user"]
        others = [c for c in corr if c.source != "user" and not session.replaced_by_user(c)]
        done = [c for c in others if c.applied]
        rejected = [c for c in others if c.status == "rejected"]
        mode = {"review": t("Review uncertain corrections"), "automatic": t("Automatic (high confidence only)"),
                "disabled": t("Off")}.get(self.settings.ocr_correction, self.settings.ocr_correction)
        self.review_summary.value = t("{done} correction(s) applied, {pending} waiting for your review. Mode: {mode}.",
                                      done=len(done) + len(mine), pending=len(pending), mode=mode)
        source_names = {"dictionary": t("dictionary"), "ai": "AI", "user": t("typed by you")}
        for c in pending + mine + done + rejected:
            before, word, after = session.correction_sentence(c)
            actions = []
            if c.source == "user":
                status = t("Your correction")
                actions.append(ft.OutlinedButton(t("Undo"), icon=ft.Icons.UNDO, data=c.id,
                                                 on_click=self.on_remove_user_edit))
            else:
                status = {"pending": t("Waiting for review"), "auto": t("Applied automatically"),
                          "accepted": t("Accepted"), "rejected": t("Rejected (original kept)")}[c.status]
                if c.status in ("pending", "rejected"):
                    actions.append(ft.FilledButton(t("Accept"), data=c.id, on_click=self.on_accept))
                if c.status in ("pending", "auto", "accepted"):
                    actions.append(ft.OutlinedButton(t("Reject") if c.status == "pending" else t("Undo"),
                                                     data=c.id, on_click=self.on_reject))
            # the pencil: retype the sentence yourself when neither the scan nor the suggestion is right
            actions.append(ft.TextButton(t("Edit"), icon=ft.Icons.EDIT_OUTLINED, data=c.id,
                                         tooltip=t("Type the text yourself"), on_click=self.on_edit_text))
            if c.source != "user":
                actions.append(ft.TextButton(t("'{word}' is correct - add to dictionary", word=c.original),
                                             data=c.original, on_click=self.on_add_word_from_review))
            info = status if c.source == "user" else \
                t("Confidence {pct}%", pct=round(c.confidence * 100)) + f"  ·  {status}"
            self.review_list.controls.append(ft.Card(content=ft.Container(ft.Column([
                ft.Row([self.text(c.original, 16, weight=ft.FontWeight.BOLD),
                        ft.Icon(ft.Icons.ARROW_FORWARD, size=18, tooltip=t("suggested")),
                        self.text(c.replacement, 16, weight=ft.FontWeight.BOLD),
                        self.text(info + "  ·  " + source_names.get(c.source, c.source), 12)], wrap=True),
                self.text(t("In the text:"), 12, color=self.pal["muted"]),
                # the whole sentence, with the uncertain word highlighted
                ft.Text(spans=[
                    ft.TextSpan(before),
                    ft.TextSpan(word, style=ft.TextStyle(weight=ft.FontWeight.BOLD, bgcolor=self.pal["notice_warning"],
                                                         decoration=ft.TextDecoration.UNDERLINE,
                                                         decoration_color=self.pal["primary"])),
                    ft.TextSpan(after)], size=self.fs(15), selectable=True),
                ft.Row(actions, wrap=True),
            ], spacing=4), padding=12)))

    def _correction(self, cid: str):
        return next((c for c in self.session.document.corrections if c.id == cid), None) if self.session else None

    async def on_edit_text(self, e):
        """Let the user retype the sentence; only what they change is stored (and can be undone)."""
        t = self.t
        c = self._correction(e.control.data)
        if c is None:
            return
        field = ft.TextField(value=self.session.editable_sentence(c), multiline=True, min_lines=3, max_lines=10,
                             autofocus=True, text_size=self.fs(16), width=640)

        async def save(_):
            self.page.pop_dialog()
            edit = self.session.edit_text(c, field.value or "")
            if edit is None:
                self.notify(t("Nothing was changed."))
                return
            self.refresh_review()
            await self.rerender()
            self.notify(t("Your correction was saved. You can undo it at any time."))

        def cancel(_):
            self.page.pop_dialog()

        self.page.show_dialog(ft.AlertDialog(
            modal=True, title=self.text(t("Correct the text"), 18, weight=ft.FontWeight.BOLD),
            content=ft.Column([
                self.text(t("Type the sentence as it should read. Only the words you change are replaced; the "
                            "scan itself is not changed and you can undo this."), 13),
                field], tight=True, spacing=12),
            actions=[ft.TextButton(t("Cancel"), on_click=cancel),
                     ft.FilledButton(t("Save"), icon=ft.Icons.CHECK, on_click=save)]))

    async def on_remove_user_edit(self, e):
        self.session.remove_user_edit(e.control.data)
        self.refresh_review()
        await self.rerender()

    # ---------------------------------------------------------------- map tab
    def build_map_tab(self) -> ft.Control:
        t = self.t
        self.map_list = ft.ListView(expand=True, spacing=2, padding=8)
        return ft.Container(ft.Column([
            self.text(t("Document map"), 18, weight=ft.FontWeight.BOLD),
            self.text(t("Headings found in the document. Select one to show it in the preview. "
                        "Nothing here is invented: only headings present in the original are listed."), 13),
            self.map_list,
        ], expand=True), padding=16, expand=True)

    def refresh_map(self) -> None:
        self.map_list.controls.clear()
        if not self.converted_pdf:
            return
        import pymupdf
        with pymupdf.open(stream=self.converted_pdf, filetype="pdf") as d:
            toc = d.get_toc()
        for level, title, pg in toc:
            self.map_list.controls.append(ft.ListTile(
                title=self.text(title, 15 if level <= 1 else 14,
                                weight=ft.FontWeight.BOLD if level <= 1 else ft.FontWeight.NORMAL),
                trailing=self.text(self.t("page {n}", n=pg), 12), data=pg - 1, on_click=self.on_map_click,
                content_padding=ft.Padding.only(left=12 + 24 * (level - 1))))
        if not toc:
            self.map_list.controls.append(self.text(self.t("No headings were detected."), 14))

    async def on_map_click(self, e):
        self.conv_page = int(e.control.data)
        if self.view_mode == "side":
            self._original_follows()
        self.tabs.selected_index = self.preview_tab_index
        self.page.update()
        await self.show_pages()

    # ---------------------------------------------------------------- AI tab
    def build_ai_tab(self) -> ft.Control:
        t = self.t
        a = self.ai_settings
        self.ai_mode = ft.RadioGroup(value=a.mode, on_change=self.on_ai_mode, content=ft.Column([
            ft.Radio(value="local_only", label=t("Local-only - no document content leaves this device")),
            ft.Radio(value="ai_assisted", label=t("AI-assisted - selected snippets may be sent to your AI provider")),
        ]))
        self.ai_provider = ft.Dropdown(label=t("Provider"), value=a.provider, width=260, text_size=self.fs(14),
                                       options=[ft.DropdownOption(key=k, text=v.label) for k, v in PROVIDERS.items()],
                                       on_select=self.on_ai_provider)
        self.ai_model = ft.Dropdown(label=t("Model"), width=260, text_size=self.fs(14), on_select=self.on_ai_model)
        self.ai_key = ft.TextField(label=t("API key"), password=True, can_reveal_password=True, width=380)
        self.ai_key_status = self.text("", 13)
        self.ai_note = self.text("", 13, italic=True)
        self.ai_usage = self.text(t("No AI requests made in this session."), 13)
        self.ai_log_summary = self.text("", 13)
        self.ai_log_list = ft.Column(spacing=0)
        self.refresh_ai_log()
        self.ai_cit = ft.Checkbox(label=t("Uncertain citations"), value=a.use_for_citations,
                                  on_change=self.on_ai_tasks)
        self.ai_ocr = ft.Checkbox(label=t("Uncertain OCR words"), value=a.use_for_ocr, on_change=self.on_ai_tasks)
        self._refresh_ai_controls()
        return ft.Container(ft.Column([
            self.text(t("AI assistance (optional)"), 18, weight=ft.FontWeight.BOLD),
            self.text(t("The converter works fully without AI. AI is only asked about items local rules are "
                        "unsure about, in small snippets, and answers are cached so nothing is sent twice."), 13),
            self.ai_mode,
            ft.Row([self.ai_provider, self.ai_model], wrap=True),
            self.ai_note,
            ft.Row([self.ai_key, ft.FilledButton(t("Save key"), on_click=self.on_save_key),
                    ft.OutlinedButton(t("Remove key"), on_click=self.on_remove_key)], wrap=True),
            self.ai_key_status,
            self.text(t("Your AI provider may charge you for API usage."), 13, weight=ft.FontWeight.BOLD),
            self.text(t("Use AI for:"), 14), ft.Row([self.ai_cit, self.ai_ocr], wrap=True),
            ft.Row([ft.FilledButton(t("Ask AI about uncertain items now"), icon=ft.Icons.SMART_TOY,
                                    on_click=self.on_run_ai),
                    ft.OutlinedButton(t("Clear AI cache"), on_click=self.on_clear_cache)], wrap=True),
            self.ai_usage,
            ft.Divider(),
            self.text(t("Privacy log: everything sent to the AI provider"), 18, weight=ft.FontWeight.BOLD),
            self.text(t("Each request is listed with the exact text that left this device and the answer that "
                        "came back. The log is kept only on this device; your API key is never part of it."), 13),
            self.ai_log_summary,
            ft.Row([ft.OutlinedButton(t("Save log..."), icon=ft.Icons.SAVE_ALT, on_click=self.on_save_ai_log),
                    ft.OutlinedButton(t("Clear log"), icon=ft.Icons.DELETE_OUTLINE, on_click=self.on_clear_ai_log)],
                   wrap=True),
            self.ai_log_list,
        ], scroll=ft.ScrollMode.AUTO, spacing=10, expand=True), padding=16, expand=True)

    LOG_SHOWN = 50  # latest requests shown in the AI tab; the saved log has them all

    def refresh_ai_log(self) -> None:
        t = self.t
        entries = self.assistant.log.entries()
        if not entries:
            self.ai_log_summary.value = t("Nothing has been sent to an AI provider yet.")
            self.ai_log_list.controls = []
            return
        self.ai_log_summary.value = t(
            "{n} request(s) logged: {chars} characters of document text sent, {tin} tokens in ({cached} from "
            "cache), {tout} tokens out.", n=len(entries), chars=sum(e.document_chars for e in entries),
            tin=sum(e.input_tokens for e in entries), cached=sum(e.cached_tokens for e in entries),
            tout=sum(e.output_tokens for e in entries))
        self.ai_log_list.controls = [self._log_tile(e) for e in reversed(entries[-self.LOG_SHOWN:])]

    def _log_tile(self, e) -> ft.Control:
        import time
        t = self.t
        task = t("Citations") if e.task == "citations" else t("OCR words")
        stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(e.when))
        title = f"{stamp} · {task} · {e.provider} / {e.model}"
        sub = t("{items} item(s), {chars} characters of document text, {tin} tokens in, {tout} tokens out",
                items=e.items, chars=e.document_chars, tin=e.input_tokens, tout=e.output_tokens)
        if e.error:
            sub += " · " + t("failed")

        def block(label: str, value: str) -> ft.Control:
            return ft.Column([self.text(label, 13, weight=ft.FontWeight.BOLD),
                              ft.Container(self.text(value, 12, selectable=True),
                                           padding=8, border_radius=6, bgcolor=self.pal["surface_low"])],
                             spacing=4)

        return ft.ExpansionTile(
            title=self.text(title, 14), subtitle=self.text(sub, 12, color=self.pal["muted"]),
            controls=[ft.Container(ft.Column([
                block(t("Document snippets sent"), e.prompt),
                block(t("Answer received"), e.answer or e.error),
                block(t("Instructions and examples sent (the same for every request of this kind)"), e.system),
            ], spacing=10), padding=ft.Padding.only(left=8, right=8, bottom=10))])

    async def on_save_ai_log(self, e):
        t = self.t
        data = self.assistant.log.as_text().encode("utf-8")
        if not data:
            self.notify(t("Nothing has been sent to an AI provider yet."))
            return
        path = await self.file_picker.save_file(dialog_title=t("Save privacy log"), file_name="ai_privacy_log.txt",
                                                allowed_extensions=["txt"], file_type=ft.FilePickerFileType.CUSTOM,
                                                src_bytes=data)
        if path and not self.page.web and not self.page.platform.is_mobile():
            if not Path(path).exists() or Path(path).stat().st_size != len(data):
                Path(path).write_bytes(data)
        if path or self.page.web:
            self.notify(t("Privacy log saved."))

    async def on_clear_ai_log(self, e):
        t = self.t
        if not await self.confirm(t("Clear log"), t("Remove the privacy log from this device?"), t("Clear log"),
                                  t("Cancel")):
            return
        self.assistant.log.clear()
        self.refresh_ai_log()
        self.page.update()

    def _refresh_ai_controls(self) -> None:
        cls = PROVIDERS.get(self.ai_settings.provider)
        models = cls.models if cls else []
        self.ai_model.options = [ft.DropdownOption(key=m, text=m) for m in models]
        self.ai_model.value = self.ai_settings.model or (cls.default_model if cls else None)
        self.ai_note.value = self.t(cls.note) if cls else ""
        has = bool(self.keystore.get(self.ai_settings.provider))
        self.ai_key_status.value = (self.t("A key is saved ({where}).", where=self.t(self.keystore.backend)) if has
                                    else self.t("No key saved for this provider."))
        if hasattr(self, "mode_chip"):
            self._update_mode_status()

    async def on_ai_mode(self, e):
        mode = e.control.value
        if mode == "ai_assisted" and not self.ai_settings.consent_given:
            ok = await self.confirm(self.t("Before using AI"), self.t(PRIVACY_NOTICE),
                                    self.t("I understand, enable AI"), self.t("Stay local-only"))
            if not ok:
                self.ai_mode.value = "local_only"
                self.page.update()
                return
            self.ai_settings.consent_given = True
        self.ai_settings.mode = mode
        self.store.save_ai(self.ai_settings)
        self._refresh_ai_controls()
        self.page.update()

    async def on_ai_provider(self, e):
        self.ai_settings.provider = e.control.value
        self.ai_settings.model = ""
        self.store.save_ai(self.ai_settings)
        self._refresh_ai_controls()
        self.page.update()

    async def on_ai_model(self, e):
        self.ai_settings.model = e.control.value
        self.store.save_ai(self.ai_settings)

    async def on_ai_tasks(self, e):
        self.ai_settings.use_for_citations = bool(self.ai_cit.value)
        self.ai_settings.use_for_ocr = bool(self.ai_ocr.value)
        self.store.save_ai(self.ai_settings)

    async def on_save_key(self, e):
        key = (self.ai_key.value or "").strip()
        if not key:
            self.notify(self.t("Enter a key first."), error=True)
            return
        self.keystore.set(self.ai_settings.provider, key)
        self.ai_key.value = ""
        self._refresh_ai_controls()
        self.page.update()
        self.notify(self.t("API key saved on this device."))

    async def on_remove_key(self, e):
        self.keystore.remove(self.ai_settings.provider)
        self._refresh_ai_controls()
        self.page.update()
        self.notify(self.t("API key removed."))

    async def on_clear_cache(self, e):
        self.assistant.cache.clear()
        self.notify(self.t("AI cache cleared."))

    async def on_run_ai(self, e):
        t = self.t
        if not self.session:
            self.notify(t("Open a PDF first."), error=True)
            return
        if self.ai_settings.mode != "ai_assisted":
            self.notify(t("AI is off. Choose 'AI-assisted' above to use it."), error=True)
            return
        if not self.assistant.has_key:
            self.notify(t.message("No API key entered. Add one in AI Settings."), error=True)
            return
        try:
            requests = await self.in_thread(self.session.ai_preview, self.assistant, self.settings)
        except Exception as ex:
            log.error("AI preview failed: %s", redact(str(ex)))
            requests = []
        if requests and not await self.confirm(t("Send to the AI provider?"), self._ai_preview(requests),
                                               t("Send"), t("Cancel")):
            return
        self.busy(True, t("Sending uncertain snippets to the AI provider..."))
        try:
            summary = t.message(await self.in_thread(self.session.run_ai, self.assistant, self.settings))
            sent = [u for u in self.assistant.usage if not u.cached]
            cached = sum(u.items for u in self.assistant.usage if u.cached)
            self.ai_usage.value = summary + ". " + t(
                "This session: {n} request(s), {cached} item(s) answered from earlier answers, {tin} tokens in, "
                "{tout} tokens out.", n=len(sent), cached=cached, tin=sum(u.input_tokens for u in sent),
                tout=sum(u.output_tokens for u in sent))
            self.status.value = summary
            self.notify(summary)
        except ConsentRequired as ex:
            self.notify(t.message(str(ex).split("\n")[0]), error=True)
        except AIError as ex:
            self.notify(t.message(str(ex)) + " " + t("The local result was kept."), error=True)
        except Exception as ex:
            log.error("AI failed: %s", redact(str(ex)))
            self.notify(t("The AI request failed; the local result was kept."), error=True)
        finally:
            self.busy(False)
        self.refresh_ai_log()
        self.refresh_review()
        await self.rerender()

    def _ai_preview(self, requests) -> ft.Control:
        """What asking the AI now would send: every document snippet, and the size of the fixed part."""
        t = self.t
        items = sum(len(r.keys) for r in requests)
        doc_chars = sum(len(r.prompt) for r in requests)
        fixed = sum(len(r.system) for r in requests)
        lines = [ft.Text(t("{n} request(s) with {items} snippet(s): {chars} characters of document text. Each "
                           "request also carries fixed instructions with made-up examples ({fixed} characters in "
                           "all), which contain nothing from your document.", n=len(requests), items=items,
                           chars=doc_chars, fixed=fixed), size=self.fs(14)),
                 ft.Text(t("This is exactly the document text that will be sent:"), size=self.fs(14),
                         weight=ft.FontWeight.BOLD)]
        for r in requests:
            label = t("Citations") if r.task.name == "citations" else t("OCR words")
            lines.append(ft.Text(label, size=self.fs(13), weight=ft.FontWeight.BOLD))
            lines.append(ft.Container(ft.Text(r.prompt, size=self.fs(12), selectable=True),
                                      padding=8, border_radius=6, bgcolor=self.pal["surface_low"]))
        return ft.Container(ft.Column(lines, spacing=8, scroll=ft.ScrollMode.AUTO), width=640, height=420)

    # ---------------------------------------------------------------- settings tab
    def build_settings_tab(self) -> ft.Control:
        t = self.t
        from ..settings import app_data_dir

        app_lang = ft.Dropdown(label=t("App language"), value=self.t.lang, width=260, text_size=self.fs(14),
                               options=[ft.DropdownOption(key=k, text=v) for k, v in LANGUAGES.items()],
                               on_select=self.on_app_language)
        dark = ft.Switch(label=t("Dark mode"), value=bool(self.ui.get("dark_mode")), on_change=self.on_dark_mode,
                         label_text_style=ft.TextStyle(size=self.fs(14)))
        contrast = ft.Switch(label=t("High-contrast colours"), value=bool(self.ui.get("high_contrast")),
                             on_change=self.on_contrast, label_text_style=ft.TextStyle(size=self.fs(14)))
        scale = ft.Dropdown(label=t("App text size"), value=str(self.ui.get("text_scale", 1.0)), width=260,
                            text_size=self.fs(14),
                            options=[ft.DropdownOption(key=str(v), text=label) for v, label in
                                     [(1.0, t("Normal")), (1.15, t("Large")), (1.3, t("Larger")),
                                      (1.5, t("Largest"))]],
                            on_select=self.on_ui_scale)
        tess = find_tesseract()

        def heading(s: str) -> ft.Control:
            return self.text(s, 17, weight=ft.FontWeight.BOLD)

        def card(controls: list[ft.Control]) -> ft.Control:
            return ft.Card(content=ft.Container(ft.Column(controls, spacing=10), padding=16))

        return ft.Container(ft.Column([
            self.text(t("Settings"), 20, weight=ft.FontWeight.BOLD),
            card([heading(t("Appearance")),
                  ft.Row([app_lang, scale], wrap=True, spacing=16),
                  ft.Row([dark, contrast], wrap=True, spacing=24),
                  self.text(t("These only change the app. Your exported documents keep their own layout "
                              "and colours (see the Convert tab)."), 12, italic=True)]),
            card([heading(t("Text recognition (OCR)")),
                  self.text(t("Tesseract: {path}", path=tess) if tess else
                            t("Tesseract was not found. Scanned pages fall back to the text the scanner stored. "
                              "Get it at https://github.com/UB-Mannheim/tesseract/wiki"), 13, selectable=True),
                  self.text(t("Scanned documents are only read once: the result is saved on this device, so "
                              "opening the same PDF again is almost instant."), 13),
                  ft.Row([ft.OutlinedButton(t("Clear saved OCR results"), icon=ft.Icons.DELETE_OUTLINE,
                                            on_click=self.on_clear_ocr_cache)])]),
            card([heading(t("Privacy and storage")),
                  self.text(t("Everything is processed on this device unless you switch on AI (see AI settings). "
                              "Your settings, dictionary and saved OCR results are stored here:"), 13),
                  self.text(str(app_data_dir()), 12, selectable=True)]),
            card([heading(t("Support")),
                  self.text(t("The app is free. If it helps you, you can buy the maker a coffee. This is "
                              "completely optional and changes nothing in the app."), 13),
                  ft.Row([self.coffee_button()])]),
            self.text(f"Dyslexia Converter {__version__}", 12),
        ], scroll=ft.ScrollMode.AUTO, spacing=12, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            padding=16, expand=True)

    async def on_app_language(self, e):
        self.ui["app_language"] = e.control.value
        self.store.save_ui(self.ui)
        self.t = Translator(e.control.value)
        await self.rebuild(tab=self.settings_tab_index)

    async def on_ui_scale(self, e):
        self.ui["text_scale"] = float(e.control.value)
        self.store.save_ui(self.ui)
        await self.rebuild(tab=self.settings_tab_index)

    async def on_contrast(self, e):
        self.ui["high_contrast"] = bool(e.control.value)
        self.store.save_ui(self.ui)
        self.restyle()

    async def on_dark_mode(self, e):
        self.ui["dark_mode"] = bool(e.control.value)
        self.store.save_ui(self.ui)
        self.restyle()

    async def on_clear_ocr_cache(self, e):
        n = await self.in_thread(pipeline.clear_ocr_cache)
        self.notify(self.t("Saved OCR results cleared ({n} document(s)).", n=n))

    # ---------------------------------------------------------------- help tab
    def build_help_tab(self) -> ft.Control:
        t = self.t
        return ft.Container(ft.Column([
            self.text(t("How it works"), 18, weight=ft.FontWeight.BOLD),
            self.text(t("1. Open a PDF. Text is extracted locally; scanned pages are read with OCR.\n"
                        "2. Headings, lists, tables, figures, footnotes and references are detected with "
                        "simple rules - no AI needed.\n"
                        "3. Adjust the settings; the preview updates.\n"
                        "4. Export to PDF, printable PDF, Word, EPUB, text or Markdown."), 14),
            self.text(t("What never changes"), 16, weight=ft.FontWeight.BOLD),
            self.text(t("The author's words. The converter does not summarise, paraphrase, simplify or remove "
                        "text. Your original PDF is never modified or overwritten."), 14),
            self.text(t("Document language"), 16, weight=ft.FontWeight.BOLD),
            self.text(t("The language of each PDF is detected automatically from its text. If the guess is "
                        "wrong, choose the language at the top of the Convert tab."), 14),
            self.text(t("About the presets and fonts"), 16, weight=ft.FontWeight.BOLD),
            self.text(t(PRESET_DISCLAIMER) + " " + t("No single font is best for every reader with dyslexia."), 14),
            self.text(t("App language, dark mode and text size are in the Settings tab."), 14),
            self.text(t("Updates and source code"), 16, weight=ft.FontWeight.BOLD),
            self.text(t("You are using version {version}. The newest version, what changed in it, and the "
                        "source code are on GitHub.", version=__version__), 14),
            ft.Row([
                ft.FilledButton(t("Get the newest version"), icon=ft.Icons.SYSTEM_UPDATE_ALT, url=RELEASES_URL,
                                tooltip=t("Opens the download page in your web browser")),
                ft.OutlinedButton(t("Project on GitHub"), icon=ft.Icons.OPEN_IN_NEW, url=PROJECT_URL,
                                  tooltip=t("Opens GitHub in your web browser")),
            ], wrap=True),
            self.text(PROJECT_URL, 12, selectable=True, color=self.pal["muted"]),
        ], scroll=ft.ScrollMode.AUTO, spacing=10, expand=True), padding=16, expand=True)

    # ================================================================ dialogs
    async def confirm(self, title: str, message, yes: str, no: str) -> bool:
        """Ask a yes/no question. ``message`` is text or a control (for longer content)."""
        fut: asyncio.Future = asyncio.get_running_loop().create_future()

        def close(result: bool):
            def handler(e):
                self.page.pop_dialog()
                if not fut.done():
                    fut.set_result(result)
            return handler

        dlg = ft.AlertDialog(modal=True, title=self.text(title, 18, weight=ft.FontWeight.BOLD),
                             content=self.text(message, 14) if isinstance(message, str) else message,
                             actions=[ft.TextButton(no, on_click=close(False)),
                                      ft.FilledButton(yes, on_click=close(True))])
        self.page.show_dialog(dlg)
        return await fut

    def busy(self, on: bool, message: str = "") -> None:
        self.progress.visible = on
        self.progress.value = None if on else 0
        if message:
            self.status.value = message
        self.page.update()

    # ================================================================ events
    async def on_open(self, e):
        files = await self.file_picker.pick_files(dialog_title=self.t("Choose a PDF"), allowed_extensions=["pdf"],
                                                  file_type=ft.FilePickerFileType.CUSTOM,
                                                  with_data=self.page.web)
        if not files:
            return
        f = files[0]
        path = f.path
        if not path and f.bytes:  # web: keep a private working copy; the upload itself is untouched
            from ..settings import app_data_dir
            tmp = app_data_dir() / "uploads"
            tmp.mkdir(exist_ok=True)
            path = str(tmp / Path(f.name).name)
            Path(path).write_bytes(f.bytes)
        self.source_path = path
        await self.load_document()

    async def on_page_range(self, e):
        if self.source_path:
            await self.load_document()

    def _page_range(self) -> Optional[tuple[int, int]]:
        try:
            a = int(self.tf_first.value) if self.tf_first.value else None
            b = int(self.tf_last.value) if self.tf_last.value else None
        except ValueError:
            self.notify(self.t("Page numbers must be whole numbers."), error=True)
            return None
        if a is None and b is None:
            return None
        return (a or 1, b or 10 ** 6)

    def doc_status(self) -> str:
        t = self.t
        d = self.session.document
        name = Path(self.source_path).name
        scanner_text = any(p.text_source == "scanner" for p in d.pages)
        kind = {"text": t("selectable text"),
                "scanned": t("scanned pages (the scanner's stored text was used)") if scanner_text
                else t("scanned pages (text read with OCR)"),
                "mixed": t("a mix of text and scanned pages (OCR used where needed)")}[d.pdf_type]
        return t("{name}: {kind}. Language: {language}.", name=name, kind=kind, language=self.lang_name(d.language))

    async def load_document(self) -> None:
        name = Path(self.source_path).name
        self.busy(True, self.t("Reading {name}...", name=name))

        def progress(msg: str, frac: float) -> None:
            self.status.value = self.t.message(msg)
            self.progress.value = frac
            try:
                self.page.update()
            except Exception:
                pass

        try:
            self.session = await self.in_thread(
                lambda: pipeline.load(self.source_path, self.settings, progress=progress,
                                      custom_words=self.custom_words, pages=self._page_range()))
        except Exception as ex:
            self.busy(False, self.t("Could not read {name}.", name=name))
            self.notify(self.t("Could not read this PDF:") + " " + redact(str(ex)), error=True)
            return
        d = self.session.document
        self.orig_count = preview.page_count(self.source_path)
        self.orig_page = (self._page_range() or (1, 1))[0] - 1
        self.conv_page = 0
        self.busy(False, self.doc_status())
        self._update_doc_language_option()
        self._notices = [("warning", w, None) for w in d.warnings]
        self.refresh_review()
        await self.rerender()

    async def on_preset(self, e):
        name = e.control.value
        self.settings = self.store.preset(name)
        self.sync_controls()
        await self.settings_changed(recompute=True)

    def sync_controls(self) -> None:
        for key, ctl in self._controls.items():
            if key.endswith("_text"):
                continue
            v = getattr(self.settings, key)
            ctl.value = str(v) if isinstance(ctl, ft.Dropdown) else v
            if key + "_text" in self._controls:
                unit = self._controls[key + "_text"].value.split(" ", 1)[-1]
                self._controls[key + "_text"].value = f"{v:g} {unit}"
        self.page.update()

    async def on_save_settings(self, e):
        self.store.save_format(self.settings)
        self.notify(self.t("Saved as 'My Settings'. They will be used next time you open the app."))

    async def on_restore_defaults(self, e):
        self.settings = self.store.reset_format()
        self.sync_controls()
        self.preset_dd.value = "Standard"
        await self.settings_changed(recompute=True)
        self.notify(self.t("Default settings restored."))

    def _font_note(self) -> str:
        return self.t.message(get_family(self.settings.font).substitute_note)

    async def settings_changed(self, recompute: bool = False, reload: bool = False) -> None:
        if reload and self.source_path:
            self.font_note.value = self._font_note()
            await self.load_document()
            return
        self.font_note.value = self._font_note()
        if self.session and self.session.document.ocr_used and recompute:
            self.session.recompute_corrections(self.settings)
            self.refresh_review()
        if self.preset_dd.value and self.preset_dd.value != "My Settings":
            self.preset_dd.value = ""
        self.page.update()
        await self.rerender()

    async def rerender(self) -> None:
        if not self.session:
            return
        self.stop_reading()  # the pages change: what was being read no longer matches
        self.busy(True, self.status.value)
        try:
            self.converted_pdf = await self.in_thread(self.session.export, "pdf", self.settings)
            self.conv_count = preview.page_count(self.converted_pdf)
            self.conv_page = min(self.conv_page, self.conv_count - 1)
        except Exception as ex:
            log.exception("render failed")
            self.notify(self.t("Could not build the preview:") + " " + redact(str(ex)), error=True)
        finally:
            self.busy(False)
        self.refresh_map()
        await self.show_pages()

    # ---------------------------------------------------------------- read aloud
    def build_read_bar(self) -> ft.Control:
        t = self.t
        self.read_btn = ft.FilledButton(t("Read aloud"), icon=ft.Icons.VOLUME_UP, on_click=self.on_read,
                                        tooltip=t("Reads the converted document aloud with the voices on this "
                                                  "computer, from the page you are looking at. Nothing leaves "
                                                  "this device."))
        self.pause_btn = ft.IconButton(ft.Icons.PAUSE, tooltip=t("Pause"), on_click=self.on_read_pause,
                                       disabled=True)
        self.stop_btn = ft.IconButton(ft.Icons.STOP, tooltip=t("Stop"), on_click=self.on_read_stop, disabled=True)
        speed = float(self.ui.get("read_speed", 1.0))
        self.speed_label = self.text(_speed_text(speed), 13)
        self.speed_slider = ft.Slider(min=0.5, max=2.0, divisions=6, value=speed, width=150,
                                      on_change_end=self.on_read_speed)
        voices = self.speaker.voices() if self._speech_allowed() else []
        self.voice_dd = ft.Dropdown(label=t("Voice"), width=260, text_size=self.fs(13), dense=True,
                                    options=[ft.DropdownOption(key="auto", text=t("Automatic"))]
                                    + [ft.DropdownOption(key=vid, text=name) for vid, name in voices],
                                    value=self.ui.get("read_voice", "auto"), on_select=self.on_read_voice)
        self.follow_cb = ft.Checkbox(label=t("Turn pages along"), value=bool(self.ui.get("read_follow", True)),
                                     on_change=self.on_read_follow)
        available = bool(voices)
        if not available:
            self.read_btn.disabled = True
            self.read_btn.tooltip = t("No speech voices were found on this device.")
        return ft.Container(ft.Row([
            self.read_btn, self.pause_btn, self.stop_btn,
            self.text(t("Speed"), 13), self.speed_slider, self.speed_label, self.voice_dd, self.follow_cb,
        ], wrap=True, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=8, vertical=2), border_radius=10,
            bgcolor=self.pal["surface_low"], visible=self._speech_allowed())

    def _speech_allowed(self) -> bool:
        """Speech plays on the computer running the app: in the web version that is the server, not the reader."""
        return not self.page.web

    def _update_read_buttons(self) -> None:
        t = self.t
        self.read_btn.content = t("Read aloud") if self._read_pos is None or self._reading else t("Continue")
        self.read_btn.disabled = self._reading or not self.speaker.voices()
        self.pause_btn.disabled = not self._reading
        self.stop_btn.disabled = not self._reading and self._read_pos is None

    def _voice(self) -> Optional[str]:
        v = self.ui.get("read_voice", "auto")
        if v and v != "auto":
            return v
        lang = self.session.document.language if self.session else "en"
        return self.speaker.voice_for(lang)

    async def on_read(self, e):
        if not self.converted_pdf or self._reading:
            return
        if self._read_units is None:
            pages = sorted(self._page_map())
            skip = frozenset(range(pages[0])) if pages else frozenset()  # the contents page(s)
            self._read_units = await self.in_thread(lambda: speech.reading_units(self.converted_pdf,
                                                                                 skip_pages=skip))
        units = self._read_units
        if not units:
            self.notify(self.t("There is no text to read on these pages."))
            return
        start = self._read_pos
        if start is None or start >= len(units) or units[start].page != self.conv_page:
            start = speech.first_sentence_on(units, self.conv_page)  # read from the page being looked at
        loop = asyncio.get_running_loop()

        def post(coro):
            try:
                asyncio.run_coroutine_threadsafe(coro, loop)
            except RuntimeError:
                pass  # the app is closing

        self._reading = True
        self._read_pos = start
        self._update_read_buttons()
        self.page.update()
        self.speaker.start(units, start, float(self.ui.get("read_speed", 1.0)), self._voice(),
                           on_word=lambda si, wi: post(self._show_word(si, wi)),
                           on_sentence=lambda si: post(self._show_word(si, 0)),
                           on_done=lambda finished: post(self._read_done(finished)))

    async def _show_word(self, si: int, wi: int) -> None:
        """Highlight the sentence and word being read; turn the page when the reading moves on."""
        if not self._reading or self._read_units is None or si >= len(self._read_units):
            return
        self._hl_next = (si, wi)
        if self._hl_busy:
            return  # a highlight is being drawn; it picks up the newest position when done
        self._hl_busy = True
        try:
            while self._hl_next is not None and self._reading:
                si, wi = self._hl_next
                self._hl_next = None
                self._read_pos = si
                sentence = self._read_units[si]
                word = sentence.words[min(wi, len(sentence.words) - 1)]
                page = word.page
                if page != self.conv_page:
                    if not self.follow_cb.value:
                        continue
                    self.conv_page = page
                    self.conv_label.value = f"{self.t('Converted')} {self.conv_page + 1} / {self.conv_count}"
                    if self.view_mode == "side":
                        before = self.orig_page
                        self._original_follows(1)
                        if self.orig_page != before and self.source_path:
                            self.orig_img.src = await self.in_thread(preview.render_page, self.source_path,
                                                                     self.orig_page, 800)
                            self.orig_label.value = f"{self.t('Original')} {self.orig_page + 1} / {self.orig_count}"
                rects = [r for w in sentence.words if w.page == page for r in w.rects]
                self.conv_img.src = await self.in_thread(preview.render_highlight, self.converted_pdf, page, 800,
                                                         rects, [r for r in word.rects], bool(self.ui.get("dark_mode")))
                self.page.update()
        finally:
            self._hl_busy = False

    async def _read_done(self, finished: bool) -> None:
        was_reading = self._reading
        self._reading = False
        if finished:
            self._read_pos = None
        self._update_read_buttons()
        if finished and was_reading:
            await self.show_pages()  # remove the highlight
        else:
            self.page.update()

    def stop_reading(self) -> None:
        """Stop and forget the position (the document or its layout changed)."""
        self._reading = False
        self.speaker.stop()
        self._read_pos = None
        self._read_units = None
        if hasattr(self, "read_btn"):
            self._update_read_buttons()

    async def on_read_pause(self, e):
        self._reading = False
        self.speaker.stop()
        self._update_read_buttons()
        self.page.update()

    async def on_read_stop(self, e):
        self._reading = False
        self.speaker.stop()
        self._read_pos = None
        self._update_read_buttons()
        await self.show_pages()

    async def _restart_reading(self) -> None:
        if self._reading:
            await self.on_read_pause(None)
            await self.on_read(None)

    async def on_read_speed(self, e):
        self.ui["read_speed"] = round(float(e.control.value), 2)
        self.speed_label.value = _speed_text(self.ui["read_speed"])
        self.store.save_ui(self.ui)
        self.page.update()
        await self._restart_reading()  # the new speed starts with the current sentence

    async def on_read_voice(self, e):
        self.ui["read_voice"] = e.control.value
        self.store.save_ui(self.ui)
        await self._restart_reading()

    async def on_read_follow(self, e):
        self.ui["read_follow"] = bool(e.control.value)
        self.store.save_ui(self.ui)

    async def show_pages(self) -> None:
        if self.source_path:
            self.orig_img.src = await self.in_thread(preview.render_page, self.source_path, self.orig_page, 800)
            self.orig_label.value = f"{self.t('Original')} {self.orig_page + 1} / {self.orig_count}"
        if self.converted_pdf:
            self.conv_img.src = await self.in_thread(preview.render_page, self.converted_pdf, self.conv_page, 800)
            self.conv_label.value = f"{self.t('Converted')} {self.conv_page + 1} / {self.conv_count}"
        self.page.update()

    async def page_step(self, which: str, delta: int) -> None:
        if which == "orig":
            self.orig_page = max(0, min(self.orig_count - 1, self.orig_page + delta))
            if self.view_mode == "side":
                self._converted_follows()
        else:
            self.conv_page = max(0, min(self.conv_count - 1, self.conv_page + delta))
            if self.view_mode == "side":
                self._original_follows(delta)
        await self.show_pages()

    def _page_map(self) -> dict[int, list[int]]:
        return getattr(self.session, "page_map", None) or {}

    def _original_follows(self, delta: int = 1) -> None:
        """Side by side: the original turns once the converted pages have moved past its content."""
        shown = self._page_map().get(self.conv_page)
        if not shown or self.orig_page in shown:
            return  # contents/notes pages, or the original page is still being read
        target = min(shown) if delta >= 0 else max(shown)
        self.orig_page = max(0, min(self.orig_count - 1, target))

    def _converted_follows(self) -> None:
        """Side by side: the converted view jumps to where the original page's content starts."""
        pages = sorted(self._page_map().items())
        hit = next((p for p, src in pages if self.orig_page in src), None)
        if hit is None:  # a page without text (a picture page): the next content after it
            hit = next((p for p, src in pages if min(src) > self.orig_page), None)
        if hit is not None:
            self.conv_page = max(0, min(self.conv_count - 1, hit))

    async def on_view_mode(self, e):
        mode = list(e.control.selected)[0] if e.control.selected else "side"
        self.view_mode = mode
        self.orig_panel.visible = mode in ("orig", "side")
        self.conv_panel.visible = mode in ("conv", "side")
        self.page.update()

    async def on_export(self, e):
        t = self.t
        if not self.session:
            self.notify(t("Open a PDF first."), error=True)
            return
        fmt = e.control.data
        ext = next(x for f, _, x in EXPORTS if f == fmt)
        stem = Path(self.source_path).stem
        suffix = "_printable" if fmt == "printable_pdf" else "_readable"
        self.busy(True, t("Preparing export..."))
        try:
            data = await self.in_thread(self.session.export, fmt, self.settings)
        except Exception as ex:
            self.busy(False)
            self.notify(t("Export failed:") + " " + redact(str(ex)), error=True)
            return
        self.busy(False, t("Choose where to save the file."))
        path = await self.file_picker.save_file(dialog_title=t("Save converted file"),
                                                file_name=f"{stem}{suffix}.{ext}",
                                                allowed_extensions=[ext], file_type=ft.FilePickerFileType.CUSTOM,
                                                src_bytes=data)
        if path and not self.page.web and not self.page.platform.is_mobile():
            if Path(path).resolve() == Path(self.source_path).resolve():
                self.notify(t("That is the original PDF - choose a different name so it is not overwritten."),
                            error=True)
                return
            if not Path(path).exists() or Path(path).stat().st_size != len(data):
                Path(path).write_bytes(data)
        if path or self.page.web:
            self.status.value = t("Saved {name}.", name=Path(path).name if path else t("file"))
            self.page.update()

    # ---- review events
    async def on_accept(self, e):
        self.session.set_correction(e.control.data, "accepted")
        self.refresh_review()
        await self.rerender()

    async def on_reject(self, e):
        self.session.set_correction(e.control.data, "rejected")
        self.refresh_review()
        await self.rerender()

    async def on_undo_all(self, e):
        if self.session:
            self.session.revert_all_corrections()
            self.refresh_review()
            await self.rerender()

    async def on_add_word(self, e):
        w = (self.word_field.value or "").strip()
        if w:
            await self._add_word(w)
            self.word_field.value = ""
            self.page.update()

    async def on_add_word_from_review(self, e):
        await self._add_word(e.control.data)

    async def _add_word(self, word: str) -> None:
        self.custom_words.add(word)
        self.words_view.value = ", ".join(sorted(self.custom_words.words))
        if self.session and self.session.document.ocr_used:
            self.session.recompute_corrections(self.settings)
            self.refresh_review()
            await self.rerender()
        self.page.update()
        self.notify(self.t("'{word}' added to your dictionary.", word=word))


def _blank_png() -> bytes:
    import io

    from PIL import Image
    # transparent, so the empty preview takes the app's background (light or dark)
    buf = io.BytesIO()
    Image.new("RGBA", (60, 85), (0, 0, 0, 0)).save(buf, "PNG")
    return buf.getvalue()


def main(page: ft.Page) -> None:
    app = ConverterApp(page)
    app.build()
    page.update()


ASSETS_DIR = str(Path(__file__).resolve().parent.parent / "assets")


def run() -> None:
    ft.run(main, assets_dir=ASSETS_DIR)
