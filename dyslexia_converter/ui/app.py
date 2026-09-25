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

from .. import pipeline
from ..ai.assistant import PRIVACY_NOTICE, AIAssistant, ConsentRequired
from ..ai.keystore import KeyStore, install_log_redaction, redact
from ..ai.providers import PROVIDERS, AIError
from ..extract.ocr import default_engine
from ..fonts import FONT_CHOICES, get_family
from ..render import preview
from ..settings import PRESET_DISCLAIMER, PRESETS, FormatSettings, SettingsStore
from ..transform.spelling import CustomWords

log = logging.getLogger("dyslexia_converter")

# settings that change how the PDF is read, not just how it is laid out
RELOAD_KEYS = {"split_spreads", "scan_text_source", "ocr_language"}

EXPORTS = [("pdf", "PDF", "pdf"), ("printable_pdf", "Printable PDF", "pdf"), ("docx", "Word (DOCX)", "docx"),
           ("txt", "Plain text", "txt"), ("md", "Markdown", "md")]


class ConverterApp:
    def __init__(self, page: ft.Page):
        self.page = page
        self.store = SettingsStore()
        self.settings: FormatSettings = self.store.load_format() if self.store.has_saved_format() \
            else PRESETS["Standard"].copy()
        self.ai_settings = self.store.load_ai()
        self.ui = {"text_scale": 1.0, "high_contrast": False, **self.store.load_ui()}
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
        self._render_task: Optional[asyncio.Task] = None
        self._controls: dict[str, ft.Control] = {}
        self.file_picker = ft.FilePicker()
        install_log_redaction()

    # ================================================================ helpers
    def fs(self, base: float = 15) -> float:
        return round(base * float(self.ui.get("text_scale", 1.0)), 1)

    def text(self, value: str, size: float = 15, **kw) -> ft.Text:
        return ft.Text(value, size=self.fs(size), **kw)

    def notify(self, message: str, error: bool = False) -> None:
        self.page.show_dialog(ft.SnackBar(ft.Text(message, size=self.fs(15)),
                                          bgcolor=ft.Colors.RED_700 if error else None,
                                          duration=ft.Duration(seconds=6 if error else 4)))

    async def in_thread(self, fn: Callable, *args):
        return await asyncio.to_thread(fn, *args)

    # ================================================================ build
    def build(self) -> None:
        p = self.page
        p.title = "Dyslexia Converter"
        p.padding = 0
        p.theme_mode = ft.ThemeMode.LIGHT
        self.apply_theme()

        self.status = self.text("Open a PDF to start. Your original file is never changed.", 14)
        self.progress = ft.ProgressBar(value=0, visible=False)
        self.mode_chip = ft.Container(content=self.text(self._mode_label(), 13, weight=ft.FontWeight.BOLD),
                                      padding=ft.Padding.symmetric(horizontal=10, vertical=4), border_radius=12,
                                      bgcolor=self._mode_color(), tooltip="Where your document content is processed")
        header = ft.Container(
            content=ft.Row([
                ft.Row([self.text("Dyslexia Converter", 22, weight=ft.FontWeight.BOLD), self.mode_chip],
                       spacing=12, wrap=True),
                ft.FilledButton("Open PDF", icon=ft.Icons.FOLDER_OPEN, on_click=self.on_open,
                                tooltip="Choose a PDF to convert"),
            ], spacing=12, wrap=True, alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10))

        narrow = (p.width or 1200) < 820
        settings_panel, preview_panel = self.build_convert_tab()
        if narrow:  # phones: settings and preview get their own tabs
            convert = [("Settings", ft.Icons.TUNE, ft.Container(settings_panel, padding=12, expand=True)),
                       ("Preview", ft.Icons.PREVIEW, ft.Container(preview_panel, padding=8, expand=True))]
        else:
            convert = [("Convert", ft.Icons.TUNE, ft.Row([
                ft.Container(settings_panel, width=400, padding=ft.Padding.only(left=12, right=4)),
                ft.VerticalDivider(width=1),
                ft.Container(preview_panel, expand=True, padding=8)], expand=True,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH))]
        self.preview_tab_index = 1 if narrow else 0
        tabs = convert + [
            ("OCR review", ft.Icons.SPELLCHECK, self.build_review_tab()),
            ("Document map", ft.Icons.ACCOUNT_TREE, self.build_map_tab()),
            ("AI settings", ft.Icons.SMART_TOY_OUTLINED, self.build_ai_tab()),
            ("Help", ft.Icons.HELP_OUTLINE, self.build_help_tab())]
        self.tabs = ft.Tabs(
            length=len(tabs), selected_index=0, animation_duration=ft.Duration(milliseconds=0), expand=True,
            content=ft.Column([
                ft.TabBar(tabs=[ft.Tab(label=t, icon=i) for t, i, _ in tabs], scrollable=True),
                ft.TabBarView(controls=[c for _, _, c in tabs], expand=True),
            ], expand=True, spacing=0))
        p.add(ft.Column([header, ft.Container(ft.Column([self.status, self.progress], spacing=4),
                                              padding=ft.Padding.symmetric(horizontal=16)),
                         self.tabs], expand=True, spacing=4))

    def apply_theme(self) -> None:
        hc = bool(self.ui.get("high_contrast"))
        # the app itself uses a bundled, highly legible font (works offline too)
        self.page.fonts = {"Atkinson": "fonts/AtkinsonHyperlegible-Regular.ttf"}
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BROWN if not hc else ft.Colors.BLACK,
                                   font_family="Atkinson")
        self.page.bgcolor = ft.Colors.WHITE if hc else "#FDFCF5"

    def _mode_label(self) -> str:
        if self.ai_settings.mode == "ai_assisted":
            return "AI-assisted"
        return "Local-only" if (self.page.width or 1200) < 820 else "Local-only: nothing leaves this device"

    def _mode_color(self) -> str:
        return "#F6E3B4" if self.ai_settings.mode == "ai_assisted" else "#DDEBD5"

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
                        options=[ft.DropdownOption(key=k, text=t) for k, t in options], on_select=changed,
                        text_size=self.fs(14))
        self._controls[key] = d
        return d

    def build_convert_tab(self) -> ft.Control:
        presets = ["Standard", "Spacious", "High Readability", "Compact print", "My Settings"]
        self.preset_dd = ft.Dropdown(label="Preset", value="", expand=True, text_size=self.fs(14),
                                     options=[ft.DropdownOption(key=p, text=p) for p in presets],
                                     on_select=self.on_preset)
        self.font_note = self.text("", 12, color=ft.Colors.BROWN_700)

        def section(title: str, controls: list[ft.Control], expanded: bool = False) -> ft.Control:
            return ft.ExpansionTile(title=self.text(title, 16, weight=ft.FontWeight.BOLD), expanded=expanded,
                                    controls=[ft.Container(ft.Column(controls, spacing=10),
                                                           padding=ft.Padding.only(left=8, right=8, top=8, bottom=10))],
                                    maintain_state=True)

        settings_col = ft.Column([
            ft.Row([self.preset_dd]),
            self.text(PRESET_DISCLAIMER, 12, italic=True),
            section("Text", [
                ft.Row([self.dropdown("font", "Font", [(f, f) for f in FONT_CHOICES])]),
                self.font_note,
                self.slider("font_size", "Font size", 9, 24, 0.5, "pt"),
                self.slider("line_spacing", "Line spacing", 1.0, 3.0, 0.1, "×"),
                self.slider("paragraph_spacing", "Paragraph spacing", 0, 36, 1, "pt"),
                self.slider("letter_spacing", "Letter spacing", 0, 3, 0.1, "pt"),
                self.slider("word_spacing", "Word spacing", 0, 10, 0.5, "pt"),
                ft.Row([self.dropdown("alignment", "Alignment",
                                      [("left", "Left (recommended)"), ("center", "Centre"),
                                       ("justify", "Justified")])]),
            ], expanded=True),
            section("Page", [
                self.slider("reading_width", "Reading width", 8, 17, 0.5, "cm"),
                self.slider("margin_top", "Top margin", 0.5, 5, 0.1, "cm"),
                self.slider("margin_bottom", "Bottom margin", 0.5, 5, 0.1, "cm"),
                self.slider("margin_left", "Left margin", 0.5, 5, 0.1, "cm"),
                self.slider("margin_right", "Right margin", 0.5, 5, 0.1, "cm"),
                ft.Row([self.dropdown("page_tint", "Page colour (screen PDF)",
                                      [("cream", "Cream"), ("blue", "Light blue"), ("none", "White")])]),
                self.switch("boxed_sections", "Boxes for abstract & quotes, lines under headings"),
                self.switch("ink_saving", "Ink-saving mode (no backgrounds or decorations)"),
                self.switch("page_numbers", "Page numbers"),
                self.switch("include_contents", "Contents page (document map)"),
            ]),
            section("Bold start of words", [
                self.switch("bold_word_start", "Bold the first part of each word",
                            "Changes only how words look, never the text"),
                ft.Row([self.dropdown("bold_amount", "How much",
                                      [("first_letter", "First letter"), ("25", "First 25%"),
                                       ("40", "First 40%"), ("auto", "Automatic")])]),
                self.switch("bold_in_references", "Also in references and citations"),
            ]),
            section("Structure", [
                self.switch("move_footnotes", "Move footnotes to the end"),
                self.switch("move_citations", "Move author-year citations to numbers [1]",
                            "Automated citation detection can make mistakes. Original citation text is kept."),
                self.text("Automated citation detection can make mistakes; the original citation text is "
                          "always kept in the list.", 12, italic=True),
                self.switch("remove_headers_footers", "Hide running headers, footers and page numbers"),
                self.switch("show_decorative_images", "Show logos and decorative images"),
                ft.Row([self.dropdown("table_mode", "Tables",
                                      [("auto", "Rebuild as tables when reliable"),
                                       ("image", "Always keep as picture")])]),
                self.switch("about_note", "Add an 'About this version' note at the end"),
            ]),
            section("Scanned documents (OCR)", [
                ft.Row([self.dropdown("ocr_language", "Document language",
                                      [("auto", "Detect automatically"), ("en", "English"), ("nl", "Dutch"),
                                       ("de", "German"), ("fr", "French"), ("es", "Spanish")])]),
                ft.Row([self.dropdown("ocr_correction", "OCR correction",
                                      [("review", "Review uncertain corrections"),
                                       ("automatic", "Automatic (high confidence only)"),
                                       ("disabled", "Off")])]),
                self.switch("split_spreads", "Split two-page book scans into single pages"),
                ft.Row([self.dropdown("scan_text_source", "Text of scanned pages",
                                      [("auto", "Clean up and read the scan (best quality)"),
                                       ("text_layer", "Use the scanner's own text layer (faster)")])]),
                self.text("Scans are straightened, gutter shadows and dark borders are removed, and two-page "
                          "spreads are split before the text is read.", 12),
                self.text("OCR: " + ("Tesseract found" if default_engine() else
                                     "not available - install Tesseract to convert scanned PDFs. Scans that "
                                     "already contain a text layer can still be converted."), 12),
            ]),
            section("Pages to convert", [
                ft.Row([
                    tf_first := ft.TextField(label="From page", value="", width=120,
                                             keyboard_type=ft.KeyboardType.NUMBER),
                    tf_last := ft.TextField(label="To page", value="", width=120,
                                            keyboard_type=ft.KeyboardType.NUMBER),
                    ft.OutlinedButton("Apply", on_click=self.on_page_range),
                ], wrap=True),
                self.text("Leave empty to convert all pages. Useful when a PDF starts with the end of "
                          "another article.", 12),
            ]),
            ft.Row([
                ft.FilledButton("Save as My Settings", icon=ft.Icons.SAVE, on_click=self.on_save_settings),
                ft.OutlinedButton("Restore defaults", icon=ft.Icons.RESTORE, on_click=self.on_restore_defaults),
            ], wrap=True),
        ], scroll=ft.ScrollMode.AUTO, spacing=8, expand=True)
        self.tf_first, self.tf_last = tf_first, tf_last

        # preview
        self.orig_img = ft.Image(src=_blank_png(), fit=ft.BoxFit.CONTAIN, expand=True,
                                 semantics_label="Original page")
        self.conv_img = ft.Image(src=_blank_png(), fit=ft.BoxFit.CONTAIN, expand=True,
                                 semantics_label="Converted page")
        self.orig_label = self.text("Original", 13)
        self.conv_label = self.text("Converted", 13)
        self.view_seg = ft.SegmentedButton(
            segments=[ft.Segment(value="orig", label=ft.Text("Original")),
                      ft.Segment(value="side", label=ft.Text("Both")),
                      ft.Segment(value="conv", label=ft.Text("Converted"))],
            selected=["side"], on_change=self.on_view_mode)

        def nav(which: str, label: ft.Text) -> ft.Row:
            async def prev(e):
                await self.page_step(which, -1)

            async def nxt(e):
                await self.page_step(which, 1)

            return ft.Row([
                ft.IconButton(ft.Icons.CHEVRON_LEFT, tooltip="Previous page", on_click=prev),
                label,
                ft.IconButton(ft.Icons.CHEVRON_RIGHT, tooltip="Next page", on_click=nxt),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=2)

        self.orig_panel = ft.Column([nav("orig", self.orig_label),
                                     ft.Container(self.orig_img, expand=True, border=ft.Border.all(1, "#33000000"))],
                                    expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.conv_panel = ft.Column([nav("conv", self.conv_label),
                                     ft.Container(self.conv_img, expand=True, border=ft.Border.all(1, "#33000000"))],
                                    expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        export_buttons = [ft.OutlinedButton(label, icon=ft.Icons.DOWNLOAD, data=fmt, on_click=self.on_export,
                                            tooltip=f"Save as {label}") for fmt, label, _ in EXPORTS]
        preview_col = ft.Column([
            ft.Row([self.view_seg], wrap=True),
            ft.Row([self.orig_panel, self.conv_panel], expand=True, vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Row([self.text("Export:", 14, weight=ft.FontWeight.BOLD)] + export_buttons, wrap=True),
        ], expand=True)

        return settings_col, preview_col

    # ---------------------------------------------------------------- review tab
    def build_review_tab(self) -> ft.Control:
        self.review_summary = self.text("No scanned document loaded.", 14)
        self.review_list = ft.ListView(expand=True, spacing=8, padding=8)
        self.word_field = ft.TextField(label="Add a word to your dictionary", width=280,
                                       on_submit=self.on_add_word)
        self.words_view = self.text(", ".join(sorted(self.custom_words.words)) or "(none yet)", 13)
        return ft.Container(ft.Column([
            self.text("OCR corrections", 18, weight=ft.FontWeight.BOLD),
            self.text("Corrections use a local dictionary. The original OCR text is kept, so every "
                      "correction can be undone.", 13),
            self.review_summary,
            ft.Row([ft.OutlinedButton("Undo all corrections", icon=ft.Icons.UNDO, on_click=self.on_undo_all)]),
            self.review_list,
            ft.Divider(),
            self.text("My dictionary (names, technical terms, abbreviations)", 15, weight=ft.FontWeight.BOLD),
            ft.Row([self.word_field, ft.OutlinedButton("Add", on_click=self.on_add_word)], wrap=True),
            self.words_view,
        ], expand=True), padding=16, expand=True)

    def refresh_review(self) -> None:
        self.review_list.controls.clear()
        if not self.session or not self.session.document.ocr_used:
            self.review_summary.value = "No OCR was needed for this document." if self.session else \
                "No scanned document loaded."
            return
        corr = self.session.document.corrections
        pending = [c for c in corr if c.status == "pending"]
        done = [c for c in corr if c.status in ("auto", "accepted")]
        self.review_summary.value = (f"{len(done)} correction(s) applied, {len(pending)} waiting for your review. "
                                     f"Mode: {self.settings.ocr_correction}.")
        for c in pending + done + [c for c in corr if c.status == "rejected"]:
            before, after = self.session.correction_context(c)
            status = {"pending": "Waiting for review", "auto": "Applied automatically",
                      "accepted": "Accepted", "rejected": "Rejected (original kept)"}[c.status]
            actions = []
            if c.status in ("pending", "rejected"):
                actions.append(ft.FilledButton("Accept", data=c.id, on_click=self.on_accept))
            if c.status in ("pending", "auto", "accepted"):
                actions.append(ft.OutlinedButton("Reject" if c.status == "pending" else "Undo", data=c.id,
                                                 on_click=self.on_reject))
            actions.append(ft.TextButton(f"'{c.original}' is correct - add to dictionary", data=c.original,
                                         on_click=self.on_add_word_from_review))
            self.review_list.controls.append(ft.Card(content=ft.Container(ft.Column([
                ft.Row([self.text(f"{c.original} → {c.replacement}", 16, weight=ft.FontWeight.BOLD),
                        self.text(f"Confidence {round(c.confidence * 100)}%  ·  {status}  ·  {c.source}",
                                  12)], wrap=True),
                self.text("Original: " + before, 13),
                self.text("Suggested: " + after, 13),
                ft.Row(actions, wrap=True),
            ], spacing=4), padding=12)))

    # ---------------------------------------------------------------- map tab
    def build_map_tab(self) -> ft.Control:
        self.map_list = ft.ListView(expand=True, spacing=2, padding=8)
        return ft.Container(ft.Column([
            self.text("Document map", 18, weight=ft.FontWeight.BOLD),
            self.text("Headings found in the document. Select one to show it in the preview. "
                      "Nothing here is invented: only headings present in the original are listed.", 13),
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
                trailing=self.text(f"page {pg}", 12), data=pg - 1, on_click=self.on_map_click,
                content_padding=ft.Padding.only(left=12 + 24 * (level - 1))))
        if not toc:
            self.map_list.controls.append(self.text("No headings were detected.", 14))

    async def on_map_click(self, e):
        self.conv_page = int(e.control.data)
        self.tabs.selected_index = self.preview_tab_index
        self.page.update()
        await self.show_pages()

    # ---------------------------------------------------------------- AI tab
    def build_ai_tab(self) -> ft.Control:
        a = self.ai_settings
        self.ai_mode = ft.RadioGroup(value=a.mode, on_change=self.on_ai_mode, content=ft.Column([
            ft.Radio(value="local_only", label="Local-only - no document content leaves this device"),
            ft.Radio(value="ai_assisted", label="AI-assisted - selected snippets may be sent to your AI provider"),
        ]))
        self.ai_provider = ft.Dropdown(label="Provider", value=a.provider, width=260, text_size=self.fs(14),
                                       options=[ft.DropdownOption(key=k, text=v.label) for k, v in PROVIDERS.items()],
                                       on_select=self.on_ai_provider)
        self.ai_model = ft.Dropdown(label="Model", width=260, text_size=self.fs(14), on_select=self.on_ai_model)
        self.ai_key = ft.TextField(label="API key", password=True, can_reveal_password=True, width=380)
        self.ai_key_status = self.text("", 13)
        self.ai_note = self.text("", 13, italic=True)
        self.ai_usage = self.text("No AI requests made in this session.", 13)
        self.ai_cit = ft.Checkbox(label="Uncertain citations", value=a.use_for_citations,
                                  on_change=self.on_ai_tasks)
        self.ai_ocr = ft.Checkbox(label="Uncertain OCR words", value=a.use_for_ocr, on_change=self.on_ai_tasks)
        self._refresh_ai_controls()
        return ft.Container(ft.Column([
            self.text("AI assistance (optional)", 18, weight=ft.FontWeight.BOLD),
            self.text("The converter works fully without AI. AI is only asked about items local rules are "
                      "unsure about, in small snippets, and answers are cached so nothing is sent twice.", 13),
            self.ai_mode,
            ft.Row([self.ai_provider, self.ai_model], wrap=True),
            self.ai_note,
            ft.Row([self.ai_key, ft.FilledButton("Save key", on_click=self.on_save_key),
                    ft.OutlinedButton("Remove key", on_click=self.on_remove_key)], wrap=True),
            self.ai_key_status,
            self.text("Your AI provider may charge you for API usage.", 13, weight=ft.FontWeight.BOLD),
            self.text("Use AI for:", 14), ft.Row([self.ai_cit, self.ai_ocr], wrap=True),
            ft.Row([ft.FilledButton("Ask AI about uncertain items now", icon=ft.Icons.SMART_TOY,
                                    on_click=self.on_run_ai),
                    ft.OutlinedButton("Clear AI cache", on_click=self.on_clear_cache)], wrap=True),
            self.ai_usage,
        ], scroll=ft.ScrollMode.AUTO, spacing=10, expand=True), padding=16, expand=True)

    def _refresh_ai_controls(self) -> None:
        cls = PROVIDERS.get(self.ai_settings.provider)
        models = cls.models if cls else []
        self.ai_model.options = [ft.DropdownOption(key=m, text=m) for m in models]
        self.ai_model.value = self.ai_settings.model or (cls.default_model if cls else None)
        self.ai_note.value = cls.note if cls else ""
        has = bool(self.keystore.get(self.ai_settings.provider))
        self.ai_key_status.value = (f"A key is saved ({self.keystore.backend})." if has
                                    else "No key saved for this provider.")
        self.mode_chip.content.value = self._mode_label() if hasattr(self, "mode_chip") else ""
        if hasattr(self, "mode_chip"):
            self.mode_chip.bgcolor = self._mode_color()

    async def on_ai_mode(self, e):
        mode = e.control.value
        if mode == "ai_assisted" and not self.ai_settings.consent_given:
            ok = await self.confirm("Before using AI", PRIVACY_NOTICE, "I understand, enable AI", "Stay local-only")
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
            self.notify("Enter a key first.", error=True)
            return
        self.keystore.set(self.ai_settings.provider, key)
        self.ai_key.value = ""
        self._refresh_ai_controls()
        self.page.update()
        self.notify("API key saved on this device.")

    async def on_remove_key(self, e):
        self.keystore.remove(self.ai_settings.provider)
        self._refresh_ai_controls()
        self.page.update()
        self.notify("API key removed.")

    async def on_clear_cache(self, e):
        self.assistant.cache.clear()
        self.notify("AI cache cleared.")

    async def on_run_ai(self, e):
        if not self.session:
            self.notify("Open a PDF first.", error=True)
            return
        if self.ai_settings.mode != "ai_assisted":
            self.notify("AI is off. Choose 'AI-assisted' above to use it.", error=True)
            return
        self.busy(True, "Sending uncertain snippets to the AI provider...")
        try:
            summary = await self.in_thread(self.session.run_ai, self.assistant, self.settings)
            chars = sum(u.chars_sent for u in self.assistant.usage)
            cached = sum(1 for u in self.assistant.usage if u.cached)
            self.ai_usage.value = (f"{summary}. Requests this session: {len(self.assistant.usage)} "
                                   f"({cached} answered from cache), about {chars} characters sent.")
            self.notify(summary)
        except ConsentRequired as ex:
            self.notify(str(ex).split("\n")[0], error=True)
        except AIError as ex:
            self.notify(f"{ex} The local result was kept.", error=True)
        except Exception as ex:
            log.error("AI failed: %s", redact(str(ex)))
            self.notify("The AI request failed; the local result was kept.", error=True)
        finally:
            self.busy(False)
        self.refresh_review()
        await self.rerender()

    # ---------------------------------------------------------------- help tab
    def build_help_tab(self) -> ft.Control:
        scale = ft.Dropdown(label="App text size", value=str(self.ui.get("text_scale", 1.0)), width=220,
                            options=[ft.DropdownOption(key=str(v), text=t) for v, t in
                                     [(1.0, "Normal"), (1.15, "Large"), (1.3, "Larger"), (1.5, "Largest")]],
                            on_select=self.on_ui_scale)
        contrast = ft.Switch(label="High-contrast app colours", value=bool(self.ui.get("high_contrast")),
                             on_change=self.on_contrast)
        return ft.Container(ft.Column([
            self.text("How it works", 18, weight=ft.FontWeight.BOLD),
            self.text("1. Open a PDF. Text is extracted locally; scanned pages are read with OCR.\n"
                      "2. Headings, lists, tables, figures, footnotes and references are detected with "
                      "simple rules - no AI needed.\n"
                      "3. Adjust the settings; the preview updates.\n"
                      "4. Export to PDF, printable PDF, Word, text or Markdown.", 14),
            self.text("What never changes", 16, weight=ft.FontWeight.BOLD),
            self.text("The author's words. The converter does not summarise, paraphrase, simplify or remove "
                      "text. Your original PDF is never modified or overwritten.", 14),
            self.text("About the presets and fonts", 16, weight=ft.FontWeight.BOLD),
            self.text(PRESET_DISCLAIMER + " No single font is best for every reader with dyslexia.", 14),
            self.text("App display", 16, weight=ft.FontWeight.BOLD),
            ft.Row([scale, contrast], wrap=True),
            self.text("The app text size and colours apply after restarting the app.", 12, italic=True),
        ], scroll=ft.ScrollMode.AUTO, spacing=10, expand=True), padding=16, expand=True)

    async def on_ui_scale(self, e):
        self.ui["text_scale"] = float(e.control.value)
        self.store.save_ui(self.ui)
        self.notify("Saved. Restart the app to apply the new text size.")

    async def on_contrast(self, e):
        self.ui["high_contrast"] = bool(e.control.value)
        self.store.save_ui(self.ui)
        self.apply_theme()
        self.page.update()

    # ================================================================ dialogs
    async def confirm(self, title: str, message: str, yes: str, no: str) -> bool:
        fut: asyncio.Future = asyncio.get_running_loop().create_future()

        def close(result: bool):
            def handler(e):
                self.page.pop_dialog()
                if not fut.done():
                    fut.set_result(result)
            return handler

        dlg = ft.AlertDialog(modal=True, title=self.text(title, 18, weight=ft.FontWeight.BOLD),
                             content=self.text(message, 14),
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
        files = await self.file_picker.pick_files(dialog_title="Choose a PDF", allowed_extensions=["pdf"],
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
            self.notify("Page numbers must be whole numbers.", error=True)
            return None
        if a is None and b is None:
            return None
        return (a or 1, b or 10 ** 6)

    async def load_document(self) -> None:
        name = Path(self.source_path).name
        self.busy(True, f"Reading {name}...")

        def progress(msg: str, frac: float) -> None:
            self.status.value = msg
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
            self.busy(False, f"Could not read {name}.")
            self.notify(f"Could not read this PDF: {redact(str(ex))}", error=True)
            return
        d = self.session.document
        self.orig_count = preview.page_count(self.source_path)
        self.orig_page = (self._page_range() or (1, 1))[0] - 1
        self.conv_page = 0
        kind = {"text": "selectable text", "scanned": "scanned pages (OCR used)",
                "mixed": "a mix of text and scanned pages (OCR used where needed)"}[d.pdf_type]
        msg = f"{name}: {kind}. Language: {d.language}."
        if d.warnings:
            msg += " " + " ".join(d.warnings)
        self.busy(False, msg)
        self.refresh_review()
        await self.rerender()
        pending = len(self.session.pending_corrections())
        if pending:
            self.notify(f"{pending} uncertain OCR correction(s) are waiting in 'OCR review'.")

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
        self.notify("Saved as 'My Settings'. They will be used next time you open the app.")

    async def on_restore_defaults(self, e):
        self.settings = self.store.reset_format()
        self.sync_controls()
        self.preset_dd.value = "Standard"
        await self.settings_changed(recompute=True)
        self.notify("Default settings restored.")

    async def settings_changed(self, recompute: bool = False, reload: bool = False) -> None:
        if reload and self.source_path:
            self.font_note.value = get_family(self.settings.font).substitute_note
            await self.load_document()
            return
        self.font_note.value = get_family(self.settings.font).substitute_note
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
        self.busy(True, self.status.value)
        try:
            self.converted_pdf = await self.in_thread(self.session.export, "pdf", self.settings)
            self.conv_count = preview.page_count(self.converted_pdf)
            self.conv_page = min(self.conv_page, self.conv_count - 1)
        except Exception as ex:
            log.exception("render failed")
            self.notify(f"Could not build the preview: {redact(str(ex))}", error=True)
        finally:
            self.busy(False)
        self.refresh_map()
        await self.show_pages()

    async def show_pages(self) -> None:
        if self.source_path:
            self.orig_img.src = await self.in_thread(preview.render_page, self.source_path, self.orig_page, 800)
            self.orig_label.value = f"Original {self.orig_page + 1} / {self.orig_count}"
        if self.converted_pdf:
            self.conv_img.src = await self.in_thread(preview.render_page, self.converted_pdf, self.conv_page, 800)
            self.conv_label.value = f"Converted {self.conv_page + 1} / {self.conv_count}"
        self.page.update()

    async def page_step(self, which: str, delta: int) -> None:
        if which == "orig":
            self.orig_page = max(0, min(self.orig_count - 1, self.orig_page + delta))
        else:
            self.conv_page = max(0, min(self.conv_count - 1, self.conv_page + delta))
        await self.show_pages()

    async def on_view_mode(self, e):
        mode = list(e.control.selected)[0] if e.control.selected else "side"
        self.orig_panel.visible = mode in ("orig", "side")
        self.conv_panel.visible = mode in ("conv", "side")
        self.page.update()

    async def on_export(self, e):
        if not self.session:
            self.notify("Open a PDF first.", error=True)
            return
        fmt = e.control.data
        ext = next(x for f, _, x in EXPORTS if f == fmt)
        stem = Path(self.source_path).stem
        suffix = "_printable" if fmt == "printable_pdf" else "_readable"
        self.busy(True, "Preparing export...")
        try:
            data = await self.in_thread(self.session.export, fmt, self.settings)
        except Exception as ex:
            self.busy(False)
            self.notify(f"Export failed: {redact(str(ex))}", error=True)
            return
        self.busy(False, "Choose where to save the file.")
        path = await self.file_picker.save_file(dialog_title="Save converted file", file_name=f"{stem}{suffix}.{ext}",
                                                allowed_extensions=[ext], file_type=ft.FilePickerFileType.CUSTOM,
                                                src_bytes=data)
        if path and not self.page.web and not self.page.platform.is_mobile():
            if Path(path).resolve() == Path(self.source_path).resolve():
                self.notify("That is the original PDF - choose a different name so it is not overwritten.",
                            error=True)
                return
            if not Path(path).exists() or Path(path).stat().st_size != len(data):
                Path(path).write_bytes(data)
        if path or self.page.web:
            self.status.value = f"Saved {Path(path).name if path else 'file'}."
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
        self.notify(f"'{word}' added to your dictionary.")


def _blank_png() -> bytes:
    import pymupdf
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 60, 85), 0)
    pix.clear_with(0xFA)
    return pix.tobytes("png")


def main(page: ft.Page) -> None:
    app = ConverterApp(page)
    app.build()
    page.update()


ASSETS_DIR = str(Path(__file__).resolve().parent.parent / "assets")


def run() -> None:
    ft.run(main, assets_dir=ASSETS_DIR)
