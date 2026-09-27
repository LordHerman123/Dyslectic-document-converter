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

from .. import highlights, pipeline, speech
from ..ai.assistant import PRIVACY_NOTICE, AIAssistant, ConsentRequired
from ..ai import keys
from ..ai.keystore import ENV_VARS, KeyStore, install_log_redaction, redact
from ..ai.providers import PROVIDERS, AIError
from .. import DONATE_URL, PROJECT_URL, __version__
from ..extract.ocr import default_engine, find_tesseract
from ..fonts import FONT_CHOICES, get_family
from ..render import preview
from ..settings import PRESET_DISCLAIMER, PRESETS, FormatSettings, SettingsStore
from ..transform.spelling import CustomWords
from .focus import FocusMode
from .i18n import LANGUAGES, Translator, system_language
from .theme import make_theme, palette

log = logging.getLogger("dyslexia_converter")

# settings that change how the PDF is read, not just how it is laid out
RELOAD_KEYS = {"split_spreads", "scan_text_source", "ocr_language"}

EXPORTS = [("pdf", "PDF", "pdf"), ("printable_pdf", "Printable PDF", "pdf"), ("docx", "Word (DOCX)", "docx"),
           ("epub", "EPUB (e-reader)", "epub"), ("txt", "Plain text", "txt"), ("md", "Markdown", "md")]
EXPORT_ICONS = {"pdf": ft.Icons.PICTURE_AS_PDF_OUTLINED, "printable_pdf": ft.Icons.PRINT_OUTLINED,
                "docx": ft.Icons.DESCRIPTION_OUTLINED, "epub": ft.Icons.MENU_BOOK_OUTLINED,
                "txt": ft.Icons.NOTES, "md": ft.Icons.CODE}
# fonts for the app itself (menus, buttons): key -> (family, file in assets/fonts, name, note); the first is the
# default. They only change the app, never the converted documents.
APP_FONTS = {
    "atkinson": ("Atkinson", "AtkinsonHyperlegible-Regular.ttf", "Standard",
                 "Atkinson Hyperlegible · clear, distinct letters (default)"),
    "opendyslexic": ("OpenDyslexic", "OpenDyslexic-Regular.ttf", "OpenDyslexic",
                     "Heavier letter bottoms, so letters don't flip"),
    "liberation": ("Liberation", "LiberationSans-Regular.ttf", "Arial-style", "Liberation Sans · plain and familiar"),
    "dejavu": ("DejaVu", "DejaVuSans.ttf", "Verdana-style", "DejaVu Sans · wide letters, open spacing"),
}
# document languages (codes used by the core) and their English names (translated in the UI)
DOC_LANGUAGES = [("en", "English"), ("nl", "Dutch"), ("de", "German"), ("fr", "French"), ("es", "Spanish"),
                 ("it", "Italian"), ("pt", "Portuguese")]


def _speed_text(v: float) -> str:
    """1.0×, 1.25×, 0.5×"""
    s = f"{v:.2f}".rstrip("0")
    return (s + "0" if s.endswith(".") else s) + "×"


class ConverterApp:
    """The whole app window: tabs, controls and the state of the open document.

    One instance per window (see :func:`main`). It holds the user's settings (``settings`` for the document
    layout, ``ai_settings``, and ``ui`` for app preferences such as language, dark mode and read-aloud choices),
    the loaded document (``session``) and the converted PDF shown in the preview (``converted_pdf``). ``build``
    creates the controls; ``rebuild`` recreates them after a language or text size change. Document work runs in a
    thread (:meth:`in_thread`) so the window stays responsive.
    """
    def __init__(self, page: ft.Page):
        """Load the saved settings and set up the helpers (translator, speech, AI assistant, focus mode); nothing
        is shown until :meth:`build`.
        """
        self.page = page
        self.store = SettingsStore()
        self.settings: FormatSettings = self.store.load_format() if self.store.has_saved_format() \
            else PRESETS["Standard"].copy()
        self.ai_settings = self.store.load_ai()
        self.ui = {"text_scale": 1.0, "high_contrast": False, "dark_mode": False, **self.store.load_ui()}
        if self.ui.get("app_language") not in LANGUAGES:
            self.ui["app_language"] = system_language()
        self.t = Translator(self.ui["app_language"])
        # every start begins in selection mode: clicking the text selects it; tap to read is switched on when wanted
        self.ui["tap_to_read"] = False
        self.keystore = KeyStore()
        if keys.migrate(self.ai_settings, self.keystore):  # a key saved by an older version gets a name
            self.store.save_ai(self.ai_settings)
        self.assistant = AIAssistant(self.ai_settings, self.keystore)
        self.key_checks: dict = {}  # key id -> the last connection check (a CheckResult, or "busy")
        self._new_check = None  # (key, result) of the check of the key typed in "Add a key"
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
        self.hl_store = highlights.HighlightStore()
        self.doc_key: Optional[str] = None
        self.hl_items: list = []  # ("Include my highlights" divider, menu item) of each export menu
        self.focus = FocusMode(self)
        self._read_units: Optional[list] = None  # sentences of the converted PDF, made when reading starts
        self._read_pos: Optional[int] = None  # sentence being read (kept when paused)
        self._reading = False
        self._hl_busy = False
        self._hl_next: Optional[tuple[int, int]] = None
        self._render_task: Optional[asyncio.Task] = None
        self._controls: dict[str, ft.Control] = {}
        self.file_picker = ft.FilePicker()
        self.clipboard = ft.Clipboard()  # "Copy" in focus mode
        install_log_redaction()

    # ================================================================ helpers
    def fs(self, base: float = 15) -> float:
        """A font size scaled by the user's text size setting."""
        return round(base * float(self.ui.get("text_scale", 1.0)), 1)

    @staticmethod
    def end_space() -> ft.Control:
        """Room below the last control of a scrolling tab, so it does not sit against the window edge."""
        return ft.Container(height=56)

    def text(self, value: str, size: float = 15, **kw) -> ft.Text:
        """A Text control in the scaled font size."""
        return ft.Text(value, size=self.fs(size), **kw)

    def lang_name(self, code: str) -> str:
        """The translated name of a document language code ("nl" -> "Dutch" in the app's language)."""
        return self.t(dict(DOC_LANGUAGES).get(code, code))

    def notify(self, message: str, error: bool = False) -> None:
        """Tell the user something: a short pop-up, or for errors and long messages an entry in the notices panel
        that stays until dismissed.
        """
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
    def _render_notices(self) -> None:
        """Show the notices (warnings, information, actions such as "review corrections") in the notices panel."""
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
        """The close button of a notice."""
        idx = e.control.data
        if 0 <= idx < len(getattr(self, "_notices", [])):
            del self._notices[idx]
        self._render_notices()
        self.page.update()

    def _review_notice(self) -> Optional[tuple[str, str, Optional[tuple[str, Callable]]]]:
        """A notice that points to the OCR review tab when corrections are waiting, or None."""
        if not self.session:
            return None
        pending = len(self.session.pending_corrections())
        if not pending:
            return None

        async def open_review(e):
            """Switch to the OCR review tab."""
            self.tabs.selected_index = self.review_tab_index
            self.page.update()

        msg = (self.t("1 word needs your decision: OCR wasn't sure how to read it.") if pending == 1 else
               self.t("{n} words need your decision: OCR wasn't sure how to read them.", n=pending))
        return ("action", msg, (self.t("Review now"), open_review))

    def update_review_notice(self) -> None:
        """Refresh the "corrections waiting" notice after corrections change."""
        notices = [n for n in getattr(self, "_notices", []) if n[0] != "action"]
        rn = self._review_notice()
        self._notices = ([rn] if rn else []) + notices
        self._render_notices()

    async def in_thread(self, fn: Callable, *args):
        """Run slow work (reading, converting, rendering) in a worker thread and wait for it without freezing the
        window.
        """
        return await asyncio.to_thread(fn, *args)

    # ================================================================ build
    def build(self) -> None:
        """Create all controls: the header, the tabs (Convert, OCR review, Document map, AI settings, Settings,
        Help) and the status bar.
        """
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
        self.ai_tab_index = len(tabs) - 3
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
        self.focus.active = False
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
        """Use the light or dark (and optionally high-contrast) colours and the app's bundled font."""
        dark = bool(self.ui.get("dark_mode"))
        self.pal = palette(dark, bool(self.ui.get("high_contrast")))
        # the app itself uses a bundled font (works offline too): the one chosen in Settings, Standard by default
        self.page.fonts = {family: "fonts/" + file for family, file, _, _ in APP_FONTS.values()}
        theme = make_theme(self.pal, APP_FONTS.get(self.ui.get("app_font"), APP_FONTS["atkinson"])[0])
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
        """The text of the privacy status in the header (local-only or AI-assisted), shorter on narrow windows."""
        if self.ai_settings.mode == "ai_assisted":
            return self.t("AI-assisted")
        return self.t("Local-only") if (self.page.width or 1200) < 820 else \
            self.t("Local-only: nothing leaves this device")

    def _mode_color(self) -> str:
        """Colour of the privacy status: AI-assisted stands out from local-only."""
        return self.pal["status_ai"] if self.ai_settings.mode == "ai_assisted" else self.pal["status_local"]

    def _mode_icon(self) -> str:
        """Icon of the privacy status: a lock for local-only, a cloud for AI-assisted."""
        return ft.Icons.CLOUD_OUTLINED if self.ai_settings.mode == "ai_assisted" else ft.Icons.LOCK_OUTLINE

    def _update_mode_status(self) -> None:
        """Refresh the privacy status in the header after the AI mode changed."""
        self.mode_icon.icon = self._mode_icon()
        self.mode_icon.color = self._mode_color()
        self.mode_text.value = self._mode_label()
        self.mode_text.color = self.pal["muted"]

    # ---------------------------------------------------------------- convert tab
    def slider(self, key: str, label: str, lo: float, hi: float, step: float, unit: str) -> ft.Control:
        """A labelled slider for one layout setting (``key`` in FormatSettings); the document is converted again
        when it is let go.
        """
        value_text = self.text(f"{getattr(self.settings, key):g} {unit}", 14)
        divisions = int(round((hi - lo) / step))

        def changed(e):
            """Show the value while the slider moves."""
            v = round(float(e.control.value) / step) * step
            value_text.value = f"{v:g} {unit}"
            value_text.update()

        async def done(e):
            """The slider was let go: store the value (rounded to the step) and convert again."""
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
        """A switch for one on/off setting (``key`` in FormatSettings)."""
        async def changed(e):
            """Store the new value; settings that change how the PDF is read load it again."""
            setattr(self.settings, key, bool(e.control.value))
            await self.settings_changed(reload=key in RELOAD_KEYS)

        sw = ft.Switch(label=label, value=getattr(self.settings, key), on_change=changed,
                       label_text_style=ft.TextStyle(size=self.fs(14)), tooltip=help_text or label)
        self._controls[key] = sw
        return sw

    def dropdown(self, key: str, label: str, options: list[tuple[str, str]]) -> ft.Dropdown:
        """A dropdown for one setting (``key`` in FormatSettings) with (value, label) options."""
        async def changed(e):
            """Store the choice; settings that change how the PDF is read load it again."""
            setattr(self.settings, key, e.control.value)
            await self.settings_changed(reload=key in RELOAD_KEYS)

        d = ft.Dropdown(label=label, value=str(getattr(self.settings, key)), expand=True,
                        options=[ft.DropdownOption(key=k, text=v) for k, v in options], on_select=changed,
                        text_size=self.fs(14))
        self._controls[key] = d
        return d

    def build_convert_tab(self) -> ft.Control:
        """The Convert tab: the settings column on the left and the preview (Original / Both / Converted, read
        aloud, focus mode, export) on the right. Returns both columns.
        """
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
            """A collapsible group of settings with a title."""
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
            self.end_space(),
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
            """Previous / next page buttons around a page label, for the original (``which`` = "orig") or
            converted preview.
            """
            async def prev(e):
                """Show the previous page."""
                await self.page_step(which, -1)

            async def nxt(e):
                """Show the next page."""
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
        conv_view = ft.GestureDetector(content=self.conv_img, on_tap_down=self.on_page_tap,
                                       on_size_change=self.on_conv_size, mouse_cursor=ft.MouseCursor.CLICK,
                                       expand=True)
        self.conv_panel = ft.Column([nav("conv", self.conv_label),
                                     ft.Container(conv_view, expand=True,
                                                  border=ft.Border.all(1, self.pal["frame"]))],
                                    expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                    visible=self.view_mode in ("conv", "side"))
        self.build_read_bar()
        preview_col = ft.Column([
            self.build_toolbar(),
            self.read_panel,
            ft.Row([self.orig_panel, self.conv_panel], expand=True, vertical_alignment=ft.CrossAxisAlignment.START),
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
        """The OCR review tab: the corrections made to scanned text (accept, reject, retype) and the user's own
        dictionary.
        """
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
        """Fill the review list with the current document's corrections (or explain why there are none)."""
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
                self.text(t("In the text:"), 12, color=ft.Colors.ON_SURFACE_VARIANT),
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
        """The correction with id ``cid`` in the current document, or None."""
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
            """Store the retyped sentence as a user edit and convert again."""
            self.page.pop_dialog()
            edit = self.session.edit_text(c, field.value or "")
            if edit is None:
                self.notify(t("Nothing was changed."))
                return
            self.refresh_review()
            await self.rerender()
            self.notify(t("Your correction was saved. You can undo it at any time."))

        def cancel(_):
            """Close the dialog without changes."""
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
        """Undo one of the user's own text edits."""
        self.session.remove_user_edit(e.control.data)
        self.refresh_review()
        await self.rerender()

    # ---------------------------------------------------------------- map tab
    def build_map_tab(self) -> ft.Control:
        """The Document map tab: the headings found, to jump to a part of the document."""
        t = self.t
        self.map_list = ft.ListView(expand=True, spacing=2, padding=8)
        return ft.Container(ft.Column([
            self.text(t("Document map"), 18, weight=ft.FontWeight.BOLD),
            self.text(t("Headings found in the document. Select one to show it in the preview. "
                        "Nothing here is invented: only headings present in the original are listed."), 13),
            self.map_list,
        ], expand=True), padding=16, expand=True)

    def refresh_map(self) -> None:
        """List the headings of the converted document (its PDF outline)."""
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
        """A heading in the map: show its page in the preview."""
        self.conv_page = int(e.control.data)
        if self.view_mode == "side":
            self._original_follows()
        self.tabs.selected_index = self.preview_tab_index
        self.page.update()
        await self.show_pages()

    # ---------------------------------------------------------------- AI tab
    def build_ai_tab(self) -> ft.Control:
        """The AI settings tab: local-only or AI-assisted, provider, model, key, what AI may be used for, and the
        privacy log of everything sent.
        """
        t = self.t
        a = self.ai_settings
        self.ai_mode = ft.RadioGroup(value=a.mode, on_change=self.on_ai_mode, content=ft.Column([
            ft.Radio(value="local_only", label=t("Local-only - no document content leaves this device")),
            ft.Radio(value="ai_assisted", label=t("AI-assisted - selected snippets may be sent to your AI provider")),
        ]))
        self.ai_model = ft.Dropdown(label=t("Model"), width=260, text_size=self.fs(14), on_select=self.on_ai_model)
        self.key_list = ft.RadioGroup(value=a.active_key, on_change=self.on_use_key, content=ft.Column(spacing=8))
        self.new_key_name = ft.TextField(label=t("Name"), hint_text=t("e.g. Uni key"), width=200,
                                         text_size=self.fs(14))
        self.new_key_provider = ft.Dropdown(
            label=t("Provider"), value=a.provider, width=210, text_size=self.fs(14), on_select=self.on_new_key_provider,
            options=[ft.DropdownOption(key=k, text=v.label) for k, v in PROVIDERS.items()])
        self.new_key = ft.TextField(label=t("API key"), password=True, can_reveal_password=True, width=320,
                                    text_size=self.fs(14), on_change=self.on_new_key_typed)
        self.new_key_note = self.text("", 12, italic=True)
        self.new_key_status = ft.Container()
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
            self.text(t("API keys"), 16, weight=ft.FontWeight.BOLD),
            self.text(t("Keys are kept on this device ({where}), never in settings or logs. The key marked 'In use' is the "
                        "one AI requests use; click another to switch.", where=t(self.keystore.backend)), 13),
            self.key_list,
            self._add_key_box(),
            ft.Row([self.ai_model], wrap=True),
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
            self.end_space(),
        ], scroll=ft.ScrollMode.AUTO, spacing=10, expand=True), padding=16, expand=True)

    LOG_SHOWN = 50  # latest requests shown in the AI tab; the saved log has them all

    def refresh_ai_log(self) -> None:
        """Show the privacy log: a summary and one entry per request sent to an AI provider."""
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
        """One privacy-log entry, expandable to show exactly what was sent and received."""
        import time
        t = self.t
        task = {"citations": t("Citations"), "summary": t("Summary"), "check": t("Connection check")}.get(
            e.task, t("OCR words"))
        stamp = time.strftime("%Y-%m-%d %H:%M", time.localtime(e.when))
        title = f"{stamp} · {task} · {e.provider} / {e.model}"
        sub = t("{items} item(s), {chars} characters of document text, {tin} tokens in, {tout} tokens out",
                items=e.items, chars=e.document_chars, tin=e.input_tokens, tout=e.output_tokens)
        if e.error:
            sub += " · " + t("failed")

        def block(label: str, value: str) -> ft.Control:
            """A labelled box with selectable text."""
            return ft.Column([self.text(label, 13, weight=ft.FontWeight.BOLD),
                              ft.Container(self.text(value, 12, selectable=True),
                                           padding=8, border_radius=6, bgcolor=ft.Colors.SURFACE_CONTAINER_LOW)],
                             spacing=4)

        return ft.ExpansionTile(
            title=self.text(title, 14), subtitle=self.text(sub, 12, color=ft.Colors.ON_SURFACE_VARIANT),
            controls=[ft.Container(ft.Column([
                block(t("Document snippets sent"), e.prompt),
                block(t("Answer received"), e.answer or e.error),
                block(t("Instructions and examples sent (the same for every request of this kind)"), e.system),
            ], spacing=10), padding=ft.Padding.only(left=8, right=8, bottom=10))])

    async def on_save_ai_log(self, e):
        """Save the privacy log as a text file."""
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
        """Delete the privacy log from this device (after asking)."""
        t = self.t
        if not await self.confirm(t("Clear log"), t("Remove the privacy log from this device?"), t("Clear log"),
                                  t("Cancel")):
            return
        self.assistant.log.clear()
        self.refresh_ai_log()
        self.page.update()

    def _refresh_ai_controls(self) -> None:
        """Show the saved keys, and the models of the provider of the key in use."""
        cls = PROVIDERS.get(self.ai_settings.provider)
        models = cls.models if cls else []
        self.ai_model.options = [ft.DropdownOption(key=m, text=m) for m in models]
        self.ai_model.value = self.ai_settings.model or (cls.default_model if cls else None)
        self.ai_model.label = self.t("Model ({provider})", provider=cls.label) if cls else self.t("Model")
        self._refresh_keys()
        if hasattr(self, "mode_chip"):
            self._update_mode_status()

    async def on_ai_mode(self, e):
        """Local-only / AI-assisted; switching AI on first asks for consent with the privacy notice."""
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

    async def on_ai_model(self, e):
        """Remember the model chosen."""
        self.ai_settings.model = e.control.value
        self.store.save_ai(self.ai_settings)

    async def on_ai_tasks(self, e):
        """Remember what AI may be used for (citations, OCR words)."""
        self.ai_settings.use_for_citations = bool(self.ai_cit.value)
        self.ai_settings.use_for_ocr = bool(self.ai_ocr.value)
        self.store.save_ai(self.ai_settings)

    # ------------------------------------------------------------------ API keys
    def _add_key_box(self) -> ft.Control:
        """The "Add a key" form: a name, the provider and the key, with a connection check before adding."""
        t = self.t
        self._new_key_note()
        return ft.Row([ft.Container(ft.Column([
            self.text(t("Add a key"), 15, weight=ft.FontWeight.BOLD),
            ft.Row([self.new_key_name, self.new_key_provider, self.new_key], wrap=True),
            self.new_key_note,
            ft.Row([ft.OutlinedButton(t("Test connection"), icon=ft.Icons.WIFI_TETHERING,
                                      on_click=self.on_check_new_key),
                    ft.FilledButton(t("Add key"), icon=ft.Icons.ADD, on_click=self.on_add_key),
                    self.new_key_status], wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            self.text(t("Test sends one tiny request with the word \"test\" - never document text - and checks that "
                        "the key and model work. Tests are shown in the privacy log too."), 12,
                      color=self.pal["muted"]),
        ], spacing=10), bgcolor=self.pal["surface_low"], border=ft.Border.all(1, self.pal["outline_variant"]),
            border_radius=12, padding=14, expand=True)])

    def _new_key_note(self) -> None:
        """The cost note of the provider chosen in "Add a key"."""
        cls = PROVIDERS.get(self.new_key_provider.value)
        self.new_key_note.value = self.t(cls.note) if cls else ""

    def _active_key_id(self, entries: list) -> str:
        """The key in use; without a choice, the provider's key from an environment variable if there is one."""
        a = self.ai_settings
        if a.active_key:
            return a.active_key
        return next((e.id for e in entries if e.from_env and e.provider == a.provider), "")

    def _refresh_keys(self) -> None:
        """Rebuild the list of saved keys (name, provider, last characters, check result, Test and remove)."""
        entries = keys.entries(self.ai_settings, self.keystore)
        active = self._active_key_id(entries)
        self.key_list.value = active or None
        self.key_list.content.controls = [self._key_row(e, e.id == active) for e in entries] or [
            self.text(self.t("No keys yet. Add one below."), 13, color=self.pal["muted"])]

    def _key_row(self, e: "keys.KeyEntry", in_use: bool) -> ft.Control:
        """One saved key: pick it, see whether it works, test it, or remove it with the cross."""
        t, pal = self.t, self.pal
        cls = PROVIDERS[e.provider]
        if e.from_env:
            detail = t("{provider} · from the {var} environment variable", provider=cls.label,
                       var=ENV_VARS[e.provider])
        else:
            end = keys.tail(keys.secret(self.ai_settings, self.keystore, e.id))
            detail = t("{provider} · key ending in …{end}", provider=cls.label, end=end) if end else cls.label
        name = [self.text(e.name, 15, weight=ft.FontWeight.BOLD)]
        if in_use:
            name.append(ft.Container(self.text(t("In use"), 11, color=pal["on_primary"]), bgcolor=pal["primary"],
                                     border_radius=8, padding=ft.Padding.symmetric(vertical=2, horizontal=8)))
        actions = [ft.OutlinedButton(t("Test"), icon=ft.Icons.WIFI_TETHERING, data=e.id,
                                     on_click=self.on_check_key, disabled=self.key_checks.get(e.id) == "busy")]
        if not e.from_env:  # an environment variable is changed outside the app
            actions.append(ft.IconButton(ft.Icons.CLOSE, tooltip=t("Remove this key"), data=e.id,
                                         icon_color=pal["muted"], on_click=self.on_remove_key))
        return ft.Container(ft.Row([
            ft.Radio(value=e.id, tooltip=t("Use this key")),
            ft.Column([ft.Row(name, spacing=8, wrap=True),
                       self.text(detail, 12, color=pal["muted"]),
                       self._check_status(self.key_checks.get(e.id))], spacing=2, tight=True, expand=True),
            *actions,
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=pal["surface"], border=ft.Border.all(1, pal["primary"] if in_use else pal["outline_variant"]),
            border_radius=12, padding=ft.Padding.only(left=4, top=8, right=8, bottom=8))

    def _check_status(self, result, new: bool = False) -> ft.Control:
        """A connection check's outcome: not tested, testing, connected (and how fast) or what went wrong."""
        import time
        t, pal = self.t, self.pal
        if result == "busy":
            icon = ft.ProgressRing(width=14, height=14, stroke_width=2)
            text, colour = t("Testing..."), pal["muted"]
        elif result is None:
            if new:
                return ft.Container()
            icon = ft.Icon(ft.Icons.HELP_OUTLINE, color=pal["muted"], size=16)
            text, colour = t("Not tested yet"), pal["muted"]
        elif result.ok:
            icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color=pal["good"], size=16)
            text = (t("Works: the key is valid and the AI answered.") if new else
                    t("Connected · answered in {s} s · tested at {time}", s=f"{result.seconds:.1f}",
                      time=time.strftime("%H:%M", time.localtime(result.when))))
            colour = pal["good"]
        else:
            icon = ft.Icon(ft.Icons.ERROR, color=pal["bad"], size=16)
            text, colour = t.message(result.message), pal["bad"]
        return ft.Row([icon, self.text(text, 12, color=colour)], spacing=4, tight=True, wrap=True)

    def _key_entry(self, kid: str):
        """The listed key with this id, or None."""
        return next((e for e in keys.entries(self.ai_settings, self.keystore) if e.id == kid), None)

    async def on_use_key(self, e):
        """A radio button: send AI requests with this key (and its provider)."""
        entry = self._key_entry(e.control.value)
        if entry:
            keys.use(self.ai_settings, entry.id, entry.provider)
            self.store.save_ai(self.ai_settings)
            self._refresh_ai_controls()
            self.page.update()

    async def _check(self, provider: str, value: str):
        """Run a connection check in the background and refresh the privacy log."""
        model = self.ai_settings.model if provider == self.ai_settings.provider else ""
        result = await self.in_thread(self.assistant.check_key, provider, value, model)
        self.refresh_ai_log()
        return result

    async def on_check_key(self, e):
        """Test: check that a saved key can connect."""
        entry = self._key_entry(e.control.data)
        value = keys.secret(self.ai_settings, self.keystore, entry.id) if entry else None
        if not value:
            return
        self.key_checks[entry.id] = "busy"
        self._refresh_keys()
        self.page.update()
        self.key_checks[entry.id] = await self._check(entry.provider, value)
        self._refresh_keys()
        self.page.update()

    async def on_remove_key(self, e):
        """The cross: after asking, delete the key from this device."""
        entry = self._key_entry(e.control.data)
        if not entry:
            return
        t = self.t
        if not await self.confirm(t("Remove this key?"), t("'{name}' is deleted from this device. You can add it "
                                                            "again later.", name=entry.name), t("Remove"), t("Cancel")):
            return
        keys.remove(self.ai_settings, self.keystore, entry.id)
        self.key_checks.pop(entry.id, None)
        self.store.save_ai(self.ai_settings)
        self._refresh_ai_controls()
        self.page.update()
        self.notify(t("API key removed."))

    async def on_new_key_provider(self, e):
        """Another provider in "Add a key": show its note; an earlier check no longer applies."""
        self._new_key_note()
        await self.on_new_key_typed(e)

    async def on_new_key_typed(self, e):
        """The key being added changed: an earlier check no longer applies."""
        if self._new_check is not None:
            self._new_check = None
            self.new_key_status.content = None
            self.page.update()

    async def on_check_new_key(self, e):
        """Test connection: check the key typed in "Add a key" before saving it."""
        value = (self.new_key.value or "").strip()
        if not value:
            self.notify(self.t("Enter a key first."), error=True)
            return
        provider = self.new_key_provider.value
        self.new_key_status.content = self._check_status("busy", new=True)
        self.page.update()
        result = await self._check(provider, value)
        self._new_check = (provider, value, result)
        self.new_key_status.content = self._check_status(result, new=True)
        self.page.update()

    async def on_add_key(self, e):
        """Add key: store the key under its name on this device (the first key is the one in use)."""
        value = (self.new_key.value or "").strip()
        if not value:
            self.notify(self.t("Enter a key first."), error=True)
            return
        provider = self.new_key_provider.value
        entry = keys.add(self.ai_settings, self.keystore, self.new_key_name.value or "", provider, value)
        if self._new_check and self._new_check[:2] == (provider, value):
            self.key_checks[entry.id] = self._new_check[2]  # tested just before adding
        self._new_check = None
        self.store.save_ai(self.ai_settings)
        self.new_key.value = self.new_key_name.value = ""
        self.new_key_status.content = None
        self._refresh_ai_controls()
        self.page.update()
        self.notify(self.t("API key saved on this device."))

    async def on_clear_cache(self, e):
        """Forget the cached AI answers (they are reused so the same text is never sent twice)."""
        self.assistant.cache.clear()
        self.notify(self.t("AI cache cleared."))

    async def on_run_ai(self, e):
        """Run the AI tasks on the open document, after checking that AI is on and a key is set."""
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
                                      padding=8, border_radius=6, bgcolor=ft.Colors.SURFACE_CONTAINER_LOW))
        return ft.Container(ft.Column(lines, spacing=8, scroll=ft.ScrollMode.AUTO), width=640, height=420)

    # ---------------------------------------------------------------- settings tab
    def build_settings_tab(self) -> ft.Control:
        """The Settings tab: app language, text size, dark mode, high contrast, where data is kept and saved OCR
        results.
        """
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
            """A section heading."""
            return self.text(s, 17, weight=ft.FontWeight.BOLD)

        def card(controls: list[ft.Control]) -> ft.Control:
            """A card grouping some settings."""
            return ft.Card(content=ft.Container(ft.Column(controls, spacing=10), padding=16))

        return ft.Container(ft.Column([
            self.text(t("Settings"), 20, weight=ft.FontWeight.BOLD),
            card([heading(t("Appearance")),
                  ft.Row([app_lang, scale], wrap=True, spacing=16),
                  ft.Row([dark, contrast], wrap=True, spacing=24),
                  self._app_font_picker(),
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
            self.end_space(),
        ], scroll=ft.ScrollMode.AUTO, spacing=12, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
            padding=16, expand=True)

    def _app_font_picker(self) -> ft.Control:
        """App font: one card per font, each showing a sample in that font; the chosen one is outlined."""
        t, pal = self.t, self.pal
        chosen = self.ui.get("app_font") if self.ui.get("app_font") in APP_FONTS else "atkinson"

        scale = float(self.ui.get("text_scale", 1.0))

        def card(key: str) -> ft.Control:
            """One font to pick: a sample, its name (ticked when chosen) and a short note, all in that font. Every
            card has the same size, which grows with the app text size so nothing is cut off."""
            family, _, name, note = APP_FONTS[key]
            on = key == chosen
            title = [ft.Text(t(name), size=self.fs(14), weight=ft.FontWeight.BOLD, font_family=family,
                             max_lines=1, overflow=ft.TextOverflow.ELLIPSIS, expand=True)]
            if on:
                title.append(ft.Icon(ft.Icons.CHECK_CIRCLE, color=pal["primary"], size=self.fs(16)))
            return ft.Container(ft.Column([
                ft.Text("Aa dq pb", size=self.fs(18), font_family=family, max_lines=1),
                ft.Row(title, spacing=4),
                ft.Text(t(note), size=self.fs(11), color=pal["muted"], font_family=family, max_lines=2,
                        overflow=ft.TextOverflow.ELLIPSIS)], spacing=2, tight=True),
                width=round(180 * scale), height=round(100 * scale), padding=10, border_radius=10,
                bgcolor=pal["surface"], data=key, on_click=self.on_app_font, tooltip=t("Use this font in the app"),
                border=ft.Border.all(2 if on else 1, pal["primary"] if on else pal["outline_variant"]))

        return ft.Column([
            self.text(t("App font"), 15, weight=ft.FontWeight.BOLD),
            ft.Row([card(k) for k in APP_FONTS], wrap=True, spacing=10, run_spacing=10),
            self.text(t("Changes the font of the app's menus and buttons. The font of your converted documents is "
                        "chosen in the Convert tab."), 12)], spacing=8)

    async def on_app_font(self, e):
        """A font card: use that font in the whole app (remembered for next time)."""
        if e.control.data == self.ui.get("app_font", "atkinson"):
            return
        self.ui["app_font"] = e.control.data
        self.store.save_ui(self.ui)
        await self.rebuild(tab=self.settings_tab_index)

    async def on_app_language(self, e):
        """A different app language: rebuild the window in it."""
        self.ui["app_language"] = e.control.value
        self.store.save_ui(self.ui)
        self.t = Translator(e.control.value)
        await self.rebuild(tab=self.settings_tab_index)

    async def on_ui_scale(self, e):
        """A different text size: rebuild the window with it."""
        self.ui["text_scale"] = float(e.control.value)
        self.store.save_ui(self.ui)
        await self.rebuild(tab=self.settings_tab_index)

    async def on_contrast(self, e):
        """High-contrast colours on or off."""
        self.ui["high_contrast"] = bool(e.control.value)
        self.store.save_ui(self.ui)
        self.restyle()

    async def on_dark_mode(self, e):
        """Dark mode on or off."""
        self.ui["dark_mode"] = bool(e.control.value)
        self.store.save_ui(self.ui)
        self.restyle()

    async def on_clear_ocr_cache(self, e):
        """Delete the saved OCR results (scanned documents are then read again when opened)."""
        n = await self.in_thread(pipeline.clear_ocr_cache)
        self.notify(self.t("Saved OCR results cleared ({n} document(s)).", n=n))

    # ---------------------------------------------------------------- help tab
    def build_help_tab(self) -> ft.Control:
        """The Help tab: the four steps, then one fold-out section per part of the app (what it does, in short
        sentences), the keyboard shortcuts, what never changes, and where to get the newest version.
        """
        t, pal = self.t, self.pal
        steps = [t("Open a PDF."), t("Choose a preset and adjust it; the preview updates."),
                 t("Read it in Focus mode, or have it read aloud."), t("Export it to the format you need.")]
        start = ft.Container(ft.Column([
            self.text(t("Start here"), 18, weight=ft.FontWeight.BOLD),
            *[ft.Row([ft.Container(self.text(str(n), 13, weight=ft.FontWeight.BOLD, color=pal["on_primary"]),
                                   bgcolor=pal["primary"], border_radius=12, width=24, height=24,
                                   alignment=ft.Alignment.CENTER),
                      self.text(step, 15, expand=True)], spacing=10)
              for n, step in enumerate(steps, 1)],
            self.text(t("Open a section below to see what else the app can do."), 13, color=pal["muted"]),
        ], spacing=8), bgcolor=pal["surface_low"], border=ft.Border.all(1, pal["outline_variant"]),
            border_radius=12, padding=16)

        sections = [
            (ft.Icons.TUNE, t("Convert a PDF"), t("Presets, fonts, spacing, structure and page layout"), t("The Convert tab turns a PDF into a calmer layout: a clear font, more space between lines, words and letters, and a clean page without clutter. The words themselves stay exactly the same."), [
                (t("Open PDF:"), t("choose a file. Its text is read on this device; scanned pages are read with "
                                   "OCR.")),
                (t("Preset:"), t("start from a preset, then change the font, size, spacing, margins and page "
                                 "colour. Keep your choice with 'Save as My Settings'.")),
                (t("Bold start of words:"), t("bolds the first part of each word. It only changes how words "
                                              "look.")),
                (t("Structure:"), t("hide running headers and page numbers, move footnotes to the end, turn "
                                    "author-year citations into numbers, and rebuild tables.")),
                (t("Pages to convert:"), t("convert only part of a long PDF.")),
                (t("Document language:"), t("found automatically. If the guess is wrong, choose the language at "
                                            "the top of the Convert tab.")),
                (t("Original, Converted, Both:"), t("compare the pages side by side; both sides stay on the same "
                                                    "page.")),
            ]),
            (ft.Icons.DOWNLOAD, t("Export"), t("PDF, printable PDF, Word, EPUB, text or Markdown"), t("Save the converted document in the way that suits how you read: on a screen, on paper, or on an e-reader. You can also keep editing it in Word."), [
                (t("Export button:"), t("PDF for the screen, Printable PDF for A4 paper, Word (DOCX), EPUB for "
                                        "e-readers, plain text and Markdown.")),
                (t("Your highlights:"), t("when a document has highlights, 'Include my highlights (PDF)' in the "
                                          "Export menu puts them in the PDF, with your notes as comments.")),
                (t("Your original:"), t("the PDF you opened is never changed.")),
            ]),
            (ft.Icons.DOCUMENT_SCANNER_OUTLINED, t("Scanned documents"), t("Text recognition and checking "
                                                                             "uncertain words"), t("Scanned pages are pictures of text. The app reads them with text recognition (OCR) on this device, so they can be converted like any other PDF. It shows you the words it was not sure about."), [
                (t("Clean-up:"), t("scans are straightened, dark borders are removed, and two-page book scans "
                                   "can be split into single pages.")),
                (t("OCR review tab:"), t("check the words the app was unsure about: accept, reject, or type the "
                                         "right text. Every change can be undone.")),
                (t("My dictionary:"), t("add names and technical terms so they are not seen as mistakes.")),
                (t("Saved:"), t("a scan is read only once; the result is kept on this device.")),
            ]),
            (ft.Icons.ACCOUNT_TREE_OUTLINED, t("Document map"), t("Jump to any heading"), t("Long documents are easier to follow when you can see how they are built. The map lists the headings, so you always know where you are."), [
                (t("Headings:"), t("every heading found in the document. Select one to show it in the "
                                   "preview.")),
                (t("Contents page:"), t("switch on 'Contents page (document map)' in the Convert tab to put one at the "
                                        "start of the converted document.")),
            ]),
            (ft.Icons.VOLUME_UP_OUTLINED, t("Read aloud"), t("Hear the text, with each word highlighted"), t("Listening while you read makes long texts easier to take in. The app uses the voices installed on your computer, so the text is never sent online."), [
                (t("Read aloud button:"), t("opens the play button, voice and speed. The sentence and the word "
                                            "being read are highlighted.")),
                (t("Tap to read (hand button):"), t("off when the app starts, so clicking the text selects it. "
                                                    "Switch it on to start reading where you click.")),
            ]),
            (ft.Icons.FULLSCREEN, t("Focus mode"), t("A calm reading view of the converted pages"), t("Focus mode shows only the converted pages, in the whole window, without the settings around them. It is made for reading, and you can set it up the way that is most comfortable for you."), [
                (t("Text size and zoom:"), t("make the pages larger or smaller, fit them to the window, or pinch "
                                             "on a touch screen.")),
                (t("View:"), t("a page colour (white, cream, blue, green, grey or dark), scrolling or one page at "
                               "a time, and a quarter turn.")),
                (t("Reading ruler:"), t("a band that marks the line you are reading; move it with the arrow "
                                        "keys.")),
                (t("Hide the bars:"), t("shows only the page. Press Esc to bring the bars back.")),
            ]),
            (ft.Icons.BORDER_COLOR_OUTLINED, t("Select, highlight and take notes"), t("In Focus mode"), t("Mark what matters while you read, and write down your thoughts next to it. Highlights and notes are saved for each document and can be exported."), [
                (t("Select:"), t("drag over the text with a mouse or pen. With a finger, press and hold, then "
                                 "drag. Double-click selects one word.")),
                (t("Toolbar:"), t("copy, four highlight colours, note, read aloud, meaning (dictionary) and "
                                  "remove. The ••• button selects the whole sentence or paragraph.")),
                (t("Stop selecting:"), t("click anywhere else or press Esc.")),
                (t("Undo:"), t("after you highlight or remove something, Undo appears at the bottom.")),
                (t("Highlighter:"), t("switch it on to mark text just by dragging over it.")),
                (t("Notes:"), t("type a note or speak it (Windows voice typing). The notes button lists all "
                                "highlights and notes, and saves them as a Word document.")),
            ]),
            (ft.Icons.SMART_TOY_OUTLINED, t("AI (optional)"), t("Off unless you switch it on"), t("The app never needs AI. If you want, AI can help with the few things the app is unsure about, and make summaries. It uses your own API key, and you always see what is sent."), [
                (t("Local-only:"), t("the default. Nothing from your document leaves this device.")),
                (t("AI-assisted:"), t("AI checks uncertain citations and OCR words, and makes summaries in Focus "
                                      "mode when you ask. Summaries are marked as made by AI.")),
                (t("API keys:"), t("add a key with a name, test the connection, and remove it with the cross.")),
                (t("Privacy log:"), t("every request is listed with the exact text that was sent.")),
            ]),
            (ft.Icons.SETTINGS_OUTLINED, t("Settings"), t("How the app itself looks"), t("Change how the app itself looks, so it is comfortable for your eyes."), [
                (t("Appearance:"), t("app language, app font, dark mode, high-contrast colours and app text size. "
                                     "These only change the app, not your documents.")),
            ]),
        ]
        shortcuts = [("Ctrl+C", t("Copy the selection")), ("1 - 4", t("Highlight the selection in a colour")),
                     ("N", t("Write a note")), ("Delete", t("Remove the highlight")),
                     ("Esc", t("Stop selecting, close the toolbar, or show the bars")),
                     ((ft.Icons.ARROW_UPWARD, ft.Icons.ARROW_DOWNWARD), t("Move the reading ruler, or scroll")),
                     ((ft.Icons.ARROW_BACK, ft.Icons.ARROW_FORWARD, "Page Up/Down · " + t("Space")),
                      t("Previous or next page"))]

        def key_label(k) -> ft.Control:
            """A key's name, or arrow icons (the app's font has no arrow characters) and names."""
            parts = k if isinstance(k, tuple) else (k,)
            return ft.Row([self.text(x, 13, weight=ft.FontWeight.BOLD) if isinstance(x, str) else
                           ft.Icon(x, size=16, color=pal["text"]) for x in parts], spacing=4, tight=True)

        keys_table = ft.Column([
            ft.Row([ft.Container(key_label(k), bgcolor=pal["surface_mid"],
                                 border=ft.Border.all(1, pal["outline_variant"]), border_radius=6, width=215,
                                 padding=ft.Padding.symmetric(vertical=4, horizontal=8)),
                    self.text(v, 14, expand=True)], spacing=12)
            for k, v in shortcuts], spacing=6)
        sections.append((ft.Icons.KEYBOARD_OUTLINED, t("Keyboard shortcuts"), t("In Focus mode"),
                         t("Keys that make Focus mode quicker to use with a keyboard."), keys_table))

        def section(icon, title, summary, intro, body) -> ft.Control:
            """One fold-out section: an icon, a title and one line; opened, a short introduction to the feature,
            then short points (or a table)."""
            if isinstance(body, list):
                body = ft.Column([ft.Text(spans=[
                    ft.TextSpan(lead + " ", ft.TextStyle(weight=ft.FontWeight.BOLD)), ft.TextSpan(rest)],
                    size=self.fs(14)) for lead, rest in body], spacing=8)
            body = ft.Column([self.text(intro, 15), body], spacing=12)
            return ft.Container(ft.ExpansionTile(
                title=self.text(title, 16, weight=ft.FontWeight.BOLD), subtitle=self.text(summary, 13),
                leading=ft.Icon(icon, color=pal["primary"]),
                controls=[ft.Container(body, padding=ft.Padding.only(left=56, right=16, bottom=14))],
                expanded_alignment=ft.Alignment.CENTER_LEFT,
                expanded_cross_axis_alignment=ft.CrossAxisAlignment.START),
                bgcolor=pal["surface"], border=ft.Border.all(1, pal["outline_variant"]), border_radius=12)

        return ft.Container(ft.Column([
            start,
            *[section(*s) for s in sections],
            self.text(t("What never changes"), 16, weight=ft.FontWeight.BOLD),
            self.text(t("The author's words. The converter does not summarise, paraphrase, simplify or remove "
                        "text. Your original PDF is never modified or overwritten."), 14),
            self.text(t("With AI-assisted mode on, Focus mode can make a summary on request. It is shown next to "
                        "the text, marked as made by AI, and never replaces the author's words."), 14),
            self.text(t("About the presets and fonts"), 16, weight=ft.FontWeight.BOLD),
            self.text(t(PRESET_DISCLAIMER) + " " + t("No single font is best for every reader with dyslexia."), 14),
            self.text(t("Updates and source code"), 16, weight=ft.FontWeight.BOLD),
            self.text(t("You are using version {version}. The newest version, what changed in it, and the "
                        "source code are on GitHub.", version=__version__), 14),
            ft.Row([ft.OutlinedButton(t("Project on GitHub"), icon=ft.Icons.OPEN_IN_NEW, url=PROJECT_URL,
                                      tooltip=t("Opens GitHub in your web browser"))], wrap=True),
            self.text(PROJECT_URL, 12, selectable=True, color=ft.Colors.ON_SURFACE_VARIANT),
            self.end_space(),
        ], scroll=ft.ScrollMode.AUTO, spacing=10, expand=True), padding=16, expand=True)

    # ================================================================ dialogs
    async def confirm(self, title: str, message, yes: str, no: str) -> bool:
        """Ask a yes/no question. ``message`` is text or a control (for longer content)."""
        fut: asyncio.Future = asyncio.get_running_loop().create_future()

        def close(result: bool):
            """A button handler that closes the dialog with ``result`` as the answer."""
            def handler(e):
                """Close the dialog and give the answer."""
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
        """Show or hide the progress bar, with a status message."""
        self.progress.visible = on
        self.progress.value = None if on else 0
        if message:
            self.status.value = message
        self.page.update()

    # ================================================================ events
    async def on_open(self, e):
        """Open PDF: choose a file (in the web version it is uploaded to a private working copy) and load it."""
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
        """The page range changed: load the document again with it."""
        if self.source_path:
            await self.load_document()

    def _page_range(self) -> Optional[tuple[int, int]]:
        """The first and last page to convert as entered, or None for the whole document."""
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
        """One line about the open document: its name, what kind of PDF it is and its language."""
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
        """Read the chosen PDF (text, OCR where needed, structure) in a thread, with progress in the status bar,
        then convert and show it.
        """
        name = Path(self.source_path).name
        self.busy(True, self.t("Reading {name}...", name=name))

        def progress(msg: str, frac: float) -> None:
            """Progress from the reader: show the message and how far it is."""
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
        try:
            self.doc_key = await self.in_thread(highlights.document_key, self.source_path)
        except OSError:
            self.doc_key = None
        self.update_highlight_option()
        self.orig_count = preview.page_count(self.source_path)
        self.orig_page = (self._page_range() or (1, 1))[0] - 1
        self.conv_page = 0
        self.busy(False, self.doc_status())
        self._update_doc_language_option()
        self._notices = [("warning", w, None) for w in d.warnings]
        self.refresh_review()
        await self.rerender()

    async def on_preset(self, e):
        """A preset: use its settings."""
        name = e.control.value
        self.settings = self.store.preset(name)
        self.sync_controls()
        await self.settings_changed(recompute=True)

    def sync_controls(self) -> None:
        """Make every setting control show the current value (after a preset, a reset or a change in focus mode)."""
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
        """Save the current settings as "My Settings" (used from then on when the app starts)."""
        self.store.save_format(self.settings)
        self.notify(self.t("Saved as 'My Settings'. They will be used next time you open the app."))

    async def on_restore_defaults(self, e):
        """Go back to the Standard preset."""
        self.settings = self.store.reset_format()
        self.sync_controls()
        self.preset_dd.value = "Standard"
        await self.settings_changed(recompute=True)
        self.notify(self.t("Default settings restored."))

    def _font_note(self) -> str:
        """A note when the chosen font is not installed and a similar free font is used instead."""
        return self.t.message(get_family(self.settings.font).substitute_note)

    async def settings_changed(self, recompute: bool = False, reload: bool = False) -> None:
        """A setting changed: convert again (``reload``: read the PDF again; ``recompute``: redo the OCR
        corrections).
        """
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
        """Convert the document again with the current settings and show the result (also in focus mode)."""
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
        if self.focus.active:
            await self.focus.refresh()
            return
        await self.show_pages()

    # ---------------------------------------------------------------- read aloud
    def build_read_bar(self) -> ft.Control:
        """The read-aloud controls, in a panel that folds out under the "Read aloud" button."""
        t = self.t
        self.read_btn = ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, icon_size=28, on_click=self.on_read,
                                      tooltip=t("Read aloud"),
                                      style=ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY, color=ft.Colors.ON_PRIMARY))
        self.stop_btn = ft.IconButton(ft.Icons.STOP_ROUNDED, tooltip=t("Stop"), on_click=self.on_read_stop,
                                      disabled=True)
        self.tap_btn = ft.IconButton(ft.Icons.TOUCH_APP_OUTLINED, selected_icon=ft.Icons.TOUCH_APP,
                                     selected=bool(self.ui.get("tap_to_read", False)), on_click=self.on_tap_toggle,
                                     style=ft.ButtonStyle(bgcolor={ft.ControlState.SELECTED: ft.Colors.PRIMARY_CONTAINER}))
        self._tap_tooltip()
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
        if not voices:
            self.read_btn.disabled = True
            self.read_btn.tooltip = t("No speech voices were found on this device.") + (
                f" ({self.speaker.last_error})" if self.speaker.last_error else "")
        self.read_row = ft.Row([
            self.read_btn, self.stop_btn, self.tap_btn, ft.Container(width=6),
            self.text(t("Speed"), 13), self.speed_slider, self.speed_label, self.voice_dd, self.follow_cb,
        ], wrap=True, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.read_panel = ft.Container(self.read_row, padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                       border_radius=10, bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                                       visible=self._speech_allowed() and bool(self.ui.get("read_panel_open", False)))
        return self.read_panel

    def build_toolbar(self) -> ft.Control:
        """View switch, the "Read aloud" button that opens the read-aloud panel, and focus mode."""
        t = self.t
        self.read_toggle = ft.FilledTonalButton(t("Read aloud"), icon=ft.Icons.VOLUME_UP, on_click=self.on_read_panel,
                                                visible=self._speech_allowed(),
                                                tooltip=t("Show or hide the read-aloud controls"))
        self.focus_btn = ft.OutlinedButton(t("Focus mode"), icon=ft.Icons.FULLSCREEN, on_click=self.on_focus,
                                           tooltip=t("Read the converted document in the whole window"))
        self.hl_items = []
        self.export_menu = self.build_export_menu()
        return ft.Row([self.view_seg, self.read_toggle, ft.Container(expand=True), self.focus_btn, self.export_menu],
                      spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def build_export_menu(self, compact: bool = False) -> ft.PopupMenuButton:
        """One "Export" button; the formats (and whether to include highlights) are in its menu."""
        t = self.t
        items = [ft.PopupMenuItem(t(label), icon=EXPORT_ICONS[fmt], data=fmt, on_click=self.on_export)
                 for fmt, label, _ in EXPORTS]
        has = bool(self.doc_highlights())
        divider = ft.PopupMenuItem(visible=has)
        hl_item = ft.PopupMenuItem(t("Include my highlights (PDF)"), checked=bool(self.ui.get("export_highlights", True)),
                                   on_click=self.on_export_highlights, visible=has)
        items[0:0] = [hl_item, divider]
        self.hl_items.append((divider, hl_item))
        if compact:
            return ft.PopupMenuButton(icon=ft.Icons.DOWNLOAD, tooltip=t("Export"), items=items,
                                      menu_position=ft.PopupMenuPosition.UNDER)
        button = ft.Container(ft.Row([ft.Icon(ft.Icons.DOWNLOAD, size=18, color=ft.Colors.ON_PRIMARY),
                                      ft.Text(t("Export"), color=ft.Colors.ON_PRIMARY, weight=ft.FontWeight.W_500),
                                      ft.Icon(ft.Icons.ARROW_DROP_DOWN, size=20, color=ft.Colors.ON_PRIMARY)],
                                     spacing=6, tight=True),
                              bgcolor=ft.Colors.PRIMARY, border_radius=20,
                              padding=ft.Padding.only(left=16, right=10, top=9, bottom=9))
        return ft.PopupMenuButton(content=button, tooltip=t("Save the converted document"), items=items,
                                  menu_position=ft.PopupMenuPosition.UNDER, padding=0)

    def doc_highlights(self) -> list:
        """The highlights made in focus mode for the open document."""
        return self.hl_store.load(self.doc_key) if self.doc_key else []

    def update_highlight_option(self) -> None:
        """The "Include my highlights" menu option shows only when the document has highlights."""
        has = bool(self.doc_highlights())
        for divider, item in self.hl_items:
            divider.visible = item.visible = has

    async def on_export_highlights(self, e):
        """"Include my highlights (PDF)" in the Export menu: switch it on or off (remembered)."""
        on = not bool(self.ui.get("export_highlights", True))
        self.ui["export_highlights"] = on
        self.store.save_ui(self.ui)
        for _, item in self.hl_items:
            item.checked = on
        self.page.update()

    def _tap_tooltip(self) -> None:
        """Explain on the tap-to-read button whether clicking the page starts reading."""
        on = bool(self.ui.get("tap_to_read", False))
        self.tap_btn.tooltip = self.t("Tap to read: on - click on the page to start reading there") if on else \
            self.t("Tap to read: off - clicking on the page does not start reading")

    async def on_tap_toggle(self, e):
        """The tap-to-read button: switch it on or off."""
        self.ui["tap_to_read"] = not bool(self.ui.get("tap_to_read", False))
        self.store.save_ui(self.ui)
        self.tap_btn.selected = self.ui["tap_to_read"]
        self._tap_tooltip()
        self.page.update()

    async def on_read_panel(self, e):
        """The Read aloud button: fold the read-aloud controls out or away."""
        open_ = not bool(self.ui.get("read_panel_open", False))
        self.ui["read_panel_open"] = open_
        self.store.save_ui(self.ui)
        self.read_panel.visible = open_
        self.page.update()

    async def on_focus(self, e):
        """The Focus mode button."""
        await self.focus.open()

    def _speech_allowed(self) -> bool:
        """Speech plays on the computer running the app: in the web version that is the server, not the reader."""
        return not self.page.web

    def _update_read_buttons(self) -> None:
        """Play (triangle) when stopped or paused, pause (bars) while reading."""
        t = self.t
        if self._reading:
            self.read_btn.icon, self.read_btn.tooltip = ft.Icons.PAUSE_ROUNDED, t("Pause")
        elif self._read_pos is not None:
            self.read_btn.icon, self.read_btn.tooltip = ft.Icons.PLAY_ARROW_ROUNDED, t("Continue")
        else:
            self.read_btn.icon, self.read_btn.tooltip = ft.Icons.PLAY_ARROW_ROUNDED, t("Read aloud")
        self.read_btn.disabled = not self.speaker.voices()
        self.stop_btn.disabled = not self._reading and self._read_pos is None
        self.read_toggle.icon = ft.Icons.GRAPHIC_EQ if self._reading else ft.Icons.VOLUME_UP

    def _check_voice_language(self) -> None:
        """Say once per document when no voice for its language is installed, and how to add one."""
        if self.ui.get("read_voice", "auto") != "auto" or not self.session:
            return
        lang = self.session.document.language
        if getattr(self, "_voice_warned", None) == (self.source_path, lang) or self.speaker.voice_for(lang):
            return
        self._voice_warned = (self.source_path, lang)
        self.notify(self.t("No {language} voice is installed on this computer, so another voice reads the text. "
                           "You can add one in Windows Settings > Time & language > Speech > Add voices, then "
                           "restart the app.", language=self.lang_name(lang)), error=True)

    def _voice(self) -> Optional[str]:
        """The voice to read with: the one chosen, or the best one for the document's language."""
        v = self.ui.get("read_voice", "auto")
        if v and v != "auto":
            return v
        lang = self.session.document.language if self.session else "en"
        return self.speaker.voice_for(lang)

    async def on_read(self, e):
        """The read / pause / continue button."""
        if self._reading:
            await self.on_read_pause(e)
        else:
            await self.start_reading()

    async def _units(self) -> list:
        """The converted document as sentences with their places on the pages (worked out once per conversion)."""
        if self._read_units is None:
            skip = self._contents_pages()
            self._read_units = await self.in_thread(lambda: speech.reading_units(self.converted_pdf,
                                                                                 skip_pages=skip))
        return self._read_units

    def _contents_pages(self) -> frozenset:
        """The contents page(s) at the start of the converted document (not read aloud, no highlights)."""
        pages = sorted(self._page_map())
        return frozenset(range(pages[0])) if pages else frozenset()

    async def on_page_tap(self, e):
        """Clicking on the converted page starts reading from the sentence clicked."""
        if not self.converted_pdf or not self._speech_allowed() or not self.speaker.voices() \
                or not self.ui.get("tap_to_read", False):
            return
        size = getattr(self, "_conv_box", None)
        if not size:
            return
        page_w, page_h = await self.in_thread(preview.page_size, self.converted_pdf, self.conv_page)
        pt = preview.tap_to_page(e.local_position.x, e.local_position.y, size[0], size[1], page_w, page_h)
        if pt is None:
            return  # beside the page
        units = await self._units()
        si = speech.sentence_at(units, self.conv_page, pt[0], pt[1])
        if si is None:
            return
        if self._reading:
            self._reading = False
            self.speaker.stop()
        await self.start_reading(si)

    def on_conv_size(self, e):
        """Remember the size of the converted preview, to turn clicks into page positions."""
        self._conv_box = (e.width, e.height)

    async def start_reading(self, start: Optional[int] = None) -> None:
        """Read from sentence ``start``, or from where reading was paused / the page being looked at."""
        if not self.converted_pdf or self._reading:
            return
        units = await self._units()
        if not units:
            self.notify(self.t("There is no text to read on these pages."))
            return
        if start is None:
            start = self._read_pos
            viewed = self.focus.current if self.focus.active else self.conv_page
            if start is None or start >= len(units) or units[start].page != viewed:
                start = speech.first_sentence_on(units, viewed)  # read from the page being looked at
        self._check_voice_language()
        loop = asyncio.get_running_loop()

        def post(coro):
            """Hand work from the speech thread to the app's event loop."""
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

    def say_word(self, text: str) -> None:
        """Say one word (from the word card in focus mode); stops reading aloud first."""
        if not text or not self._speech_allowed():
            return
        if self._reading:
            self._reading = False
            self._update_read_buttons()
        self.speaker.start([speech.Sentence([speech.Word(text, 0, [])])], 0,
                           float(self.ui.get("read_speed", 1.0)), self._voice())

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
                if self.focus.active:
                    rects = [r for w in sentence.words if w.page == page for r in w.rects]
                    await self.focus.show_reading(page, rects, list(word.rects), bool(self.follow_cb.value))
                    continue
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
        """Reading aloud ended (finished, paused, or stopped by an error, which is reported)."""
        was_reading = self._reading
        self._reading = False
        if finished:
            self._read_pos = None
        elif was_reading and self.speaker.last_error:
            self.notify(self.t("Reading aloud stopped because of an error:") + " " + self.speaker.last_error,
                        error=True)
        self._update_read_buttons()
        if self.focus.active:
            if finished:
                await self.focus.reading_done()
            self.page.update()
        elif finished and was_reading:
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
        """Pause reading aloud (the play button continues from here)."""
        self._reading = False
        self.speaker.stop()
        self._update_read_buttons()
        self.page.update()

    async def on_read_stop(self, e):
        """Stop reading aloud and forget the position."""
        self._reading = False
        self.speaker.stop()
        self._read_pos = None
        self._update_read_buttons()
        if self.focus.active:
            await self.focus.reading_done()
            self.page.update()
            return
        await self.show_pages()

    async def _restart_reading(self) -> None:
        """Start the current sentence again (after the speed or voice changed while reading)."""
        if self._reading:
            await self.on_read_pause(None)
            await self.on_read(None)

    async def on_read_speed(self, e):
        """A new reading speed."""
        self.ui["read_speed"] = round(float(e.control.value), 2)
        self.speed_label.value = _speed_text(self.ui["read_speed"])
        self.store.save_ui(self.ui)
        self.page.update()
        await self._restart_reading()  # the new speed starts with the current sentence

    async def on_read_voice(self, e):
        """A different voice."""
        self.ui["read_voice"] = e.control.value
        self.store.save_ui(self.ui)
        await self._restart_reading()

    async def on_read_follow(self, e):
        """"Turn pages along" on or off."""
        self.ui["read_follow"] = bool(e.control.value)
        self.store.save_ui(self.ui)

    async def show_pages(self) -> None:
        """Render and show the current original and converted pages in the preview."""
        if self.source_path:
            self.orig_img.src = await self.in_thread(preview.render_page, self.source_path, self.orig_page, 800)
            self.orig_label.value = f"{self.t('Original')} {self.orig_page + 1} / {self.orig_count}"
        if self.converted_pdf:
            self.conv_img.src = await self.in_thread(preview.render_page, self.converted_pdf, self.conv_page, 800)
            self.conv_label.value = f"{self.t('Converted')} {self.conv_page + 1} / {self.conv_count}"
        self.page.update()

    async def page_step(self, which: str, delta: int) -> None:
        """Go ``delta`` pages in the original ("orig") or converted preview; in Both view the other side follows."""
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
        """Which converted pages show each original page (from the conversion), for keeping Both view in step."""
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
        """Original / Both / Converted."""
        mode = list(e.control.selected)[0] if e.control.selected else "side"
        self.view_mode = mode
        self.orig_panel.visible = mode in ("orig", "side")
        self.conv_panel.visible = mode in ("conv", "side")
        self.page.update()

    async def on_export(self, e):
        """Export in the format of the menu item chosen: convert, add highlights to PDFs when asked, and save
        where the user picks (never over the original).
        """
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
            marks = self.doc_highlights() if fmt in ("pdf", "printable_pdf") and \
                self.ui.get("export_highlights", True) else []
            if marks:
                skip = self._contents_pages()
                data = await self.in_thread(highlights.apply_to_pdf, data, marks, skip)
        except Exception as ex:
            self.busy(False)
            self.notify(t("Export failed:") + " " + redact(str(ex)), error=True)
            return
        self.busy(False, t("Choose where to save the file."))
        await self.save_bytes(data, f"{stem}{suffix}.{ext}", ext)

    async def save_bytes(self, data: bytes, file_name: str, ext: str) -> None:
        """Let the user choose where to save a file (never over the original PDF) and save it there."""
        t = self.t
        path = await self.file_picker.save_file(dialog_title=t("Save converted file"), file_name=file_name,
                                                allowed_extensions=[ext], file_type=ft.FilePickerFileType.CUSTOM,
                                                src_bytes=data)
        if path and not self.page.web and not self.page.platform.is_mobile():
            if self.source_path and Path(path).resolve() == Path(self.source_path).resolve():
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
        """Accept an OCR correction."""
        self.session.set_correction(e.control.data, "accepted")
        self.refresh_review()
        await self.rerender()

    async def on_reject(self, e):
        """Reject an OCR correction (the original OCR text is used)."""
        self.session.set_correction(e.control.data, "rejected")
        self.refresh_review()
        await self.rerender()

    async def on_undo_all(self, e):
        """Undo every OCR correction."""
        if self.session:
            self.session.revert_all_corrections()
            self.refresh_review()
            await self.rerender()

    async def on_add_word(self, e):
        """Add the typed word to the user's dictionary."""
        w = (self.word_field.value or "").strip()
        if w:
            await self._add_word(w)
            self.word_field.value = ""
            self.page.update()

    async def on_add_word_from_review(self, e):
        """Add a word from the review list to the user's dictionary (so it is no longer "corrected")."""
        await self._add_word(e.control.data)

    async def _add_word(self, word: str) -> None:
        """Add a word to the user's dictionary and redo the corrections with it."""
        self.custom_words.add(word)
        self.words_view.value = ", ".join(sorted(self.custom_words.words))
        if self.session and self.session.document.ocr_used:
            self.session.recompute_corrections(self.settings)
            self.refresh_review()
            await self.rerender()
        self.page.update()
        self.notify(self.t("'{word}' added to your dictionary.", word=word))


def _blank_png() -> bytes:
    """A small transparent PNG for an empty preview."""
    import io

    from PIL import Image
    # transparent, so the empty preview takes the app's background (light or dark)
    buf = io.BytesIO()
    Image.new("RGBA", (60, 85), (0, 0, 0, 0)).save(buf, "PNG")
    return buf.getvalue()


def main(page: ft.Page) -> None:
    """Flet entry point: build the app in the window Flet gives us."""
    app = ConverterApp(page)
    app.build()
    page.update()


ASSETS_DIR = str(Path(__file__).resolve().parent.parent / "assets")


def run() -> None:
    """Start the app (desktop window, or the web version when Flet is run that way)."""
    ft.run(main, assets_dir=ASSETS_DIR)
