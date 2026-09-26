"""Focus mode: the converted document as a reader, filling the window.

All pages in one scroll (like a PDF reader, also on a tablet), with a thin bar on top. The read-aloud
controls and the reading settings fold out below the bar and fold away again, so only the text is left.
A highlighter marks words in four colours (with an eraser); highlights are kept per document and follow
their words when the layout changes.
"""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Optional

import flet as ft

from .. import highlights as hl
from ..fonts import FONT_CHOICES
from ..render import preview
from ..speech import sentence_at

if TYPE_CHECKING:  # pragma: no cover
    from .app import ConverterApp

SWATCHES = {"yellow": "#FFD600", "green": "#50C878", "blue": "#50A0FF", "pink": "#FF78B4"}


class FocusMode:
    BASE_W = 820  # page width at 100 %
    GAP = 18
    PAD = 20

    def __init__(self, app: "ConverterApp"):
        self.app = app
        self.active = False
        self.zoom = float(app.ui.get("focus_zoom", 1.0))
        self.tool: Optional[str] = None  # None, "mark" or "erase"
        self.colour = app.ui.get("focus_colour", "yellow")
        self.images: list[ft.Image] = []
        self.frames: list[ft.Container] = []
        self.detectors: list[ft.GestureDetector] = []
        self.sizes: list[tuple[float, float]] = []
        self.boxes: dict[int, tuple[float, float]] = {}
        self.current = 0
        self.words: list = []
        self.highlights: list[hl.Highlight] = []
        self.store = hl.HighlightStore()
        self.doc_key: Optional[str] = None
        self._render_task: Optional[asyncio.Task] = None
        self._reading_page: Optional[int] = None
        self._drag: Optional[tuple[int, int, int]] = None  # page, first word, last word
        self._saved: list = []

    # ------------------------------------------------------------------ open / close
    async def open(self) -> None:
        app, t = self.app, self.app.t
        if not app.converted_pdf:
            app.notify(t("Open a PDF first."), error=True)
            return
        self.active = True
        self.current = app.conv_page
        if app.source_path:
            try:
                self.doc_key = await app.in_thread(hl.document_key, app.source_path)
            except OSError:
                self.doc_key = None
        self.highlights = self.store.load(self.doc_key) if self.doc_key else []

        self.page_label = app.text("", 14)
        self.read_toggle = ft.IconButton(ft.Icons.VOLUME_UP, tooltip=t("Read aloud"), on_click=self.on_read_panel,
                                         selected=bool(app.ui.get("read_panel_open", False)),
                                         style=self._toggle_style(), visible=app._speech_allowed())
        self.settings_toggle = ft.IconButton(ft.Icons.TEXT_FIELDS, tooltip=t("Reading settings"),
                                             on_click=self.on_settings_panel,
                                             selected=bool(app.ui.get("focus_settings_open", False)),
                                             style=self._toggle_style())
        self.mark_toggle = ft.IconButton(ft.Icons.BORDER_COLOR, tooltip=t("Highlighter"), on_click=self.on_marker,
                                         style=self._toggle_style())
        self.swatches = ft.Row([self._swatch(name) for name in SWATCHES] + [
            ft.IconButton(ft.Icons.AUTO_FIX_NORMAL, tooltip=t("Eraser"), data="erase", on_click=self.on_eraser,
                          style=self._toggle_style())], spacing=4, visible=False)
        top = ft.Container(ft.Row([
            ft.IconButton(ft.Icons.CLOSE, tooltip=t("Leave focus mode"), on_click=self.on_close),
            ft.Container(width=4),
            self.read_toggle, self.settings_toggle, self.mark_toggle, self.swatches,
            ft.Container(expand=True),
            self.page_label,
            ft.IconButton(ft.Icons.ZOOM_OUT, tooltip=t("Smaller"), on_click=lambda e: self._zoom_by(-0.1)),
            ft.IconButton(ft.Icons.ZOOM_IN, tooltip=t("Larger"), on_click=lambda e: self._zoom_by(0.1)),
        ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=8, vertical=2), bgcolor=ft.Colors.SURFACE_CONTAINER_LOW)

        # the read-aloud controls move here from the main view while focus mode is open
        app.read_panel.content = None
        self.read_panel = ft.Container(app.read_row, visible=bool(app.ui.get("read_panel_open", False)),
                                       padding=ft.Padding.symmetric(horizontal=12, vertical=4),
                                       bgcolor=ft.Colors.SURFACE_CONTAINER_LOW)
        self.settings_panel = ft.Container(self._settings_row(), visible=bool(app.ui.get("focus_settings_open")),
                                           padding=ft.Padding.symmetric(horizontal=12, vertical=4),
                                           bgcolor=ft.Colors.SURFACE_CONTAINER_LOW)
        self.list = ft.ListView(expand=True, spacing=self.GAP, on_scroll=self.on_scroll,
                                padding=ft.Padding.symmetric(vertical=self.PAD))
        self._saved = list(app.page.controls)
        app.page.controls.clear()
        app.page.add(ft.Column([top, self.read_panel, self.settings_panel, ft.Divider(height=1), self.list],
                               expand=True, spacing=0, horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
        await self._build_pages()
        app.page.update()
        await self.scroll_to(self.current, animate=False)
        self._start_rendering()

    async def close(self) -> None:
        app = self.app
        if not self.active:
            return
        self.active = False
        if self._render_task:
            self._render_task.cancel()
        self.read_panel.content = None
        app.read_panel.content = app.read_row  # the read-aloud controls go back to the main view
        app.read_panel.visible = bool(app.ui.get("read_panel_open", False))
        app.page.controls.clear()
        app.page.controls.extend(self._saved)
        app.conv_page = min(self.current, max(0, app.conv_count - 1))
        if app.view_mode == "side":
            app._original_follows(1)
        app.sync_controls()  # settings changed in focus mode show in the Convert tab too
        app.page.update()
        await app.show_pages()

    async def on_close(self, e):
        await self.close()

    # ------------------------------------------------------------------ pages
    def _page_w(self) -> float:
        avail = (self.app.page.width or 1200) - 40
        return max(240.0, min(self.BASE_W * self.zoom, avail))

    async def _build_pages(self) -> None:
        app = self.app
        pdf = app.converted_pdf
        n = preview.page_count(pdf)
        self.sizes = [await app.in_thread(preview.page_size, pdf, i) for i in range(n)]
        units = await app._units()
        self.words = hl.document_words(units)
        w = self._page_w()
        self.images, self.frames, self.detectors = [], [], []
        rows = []
        for i, (pw, ph) in enumerate(self.sizes):
            img = ft.Image(src=_blank(), fit=ft.BoxFit.FILL, gapless_playback=True, expand=True)
            det = ft.GestureDetector(content=img, data=i, on_tap_down=self.on_tap,
                                     on_size_change=self.on_size, mouse_cursor=ft.MouseCursor.CLICK, expand=True)
            frame = ft.Container(det, width=w, height=w * ph / pw, bgcolor="#FFFFFF",
                                 shadow=ft.BoxShadow(blur_radius=10, color="#33000000"))
            self.images.append(img)
            self.detectors.append(det)
            self.frames.append(frame)
            rows.append(ft.Row([frame], alignment=ft.MainAxisAlignment.CENTER))
        self.list.controls = rows
        self.current = min(self.current, n - 1)
        self._set_tool_gestures()
        self._update_label()

    def _offset(self, i: int) -> float:
        w = self._page_w()
        return self.PAD + sum(w * ph / pw + self.GAP for pw, ph in self.sizes[:i])

    async def scroll_to(self, i: int, animate: bool = True) -> None:
        try:
            await self.list.scroll_to(offset=self._offset(i), duration=250 if animate else 0)
        except Exception:
            pass
        self.current = i
        self._update_label()

    def on_scroll(self, e: ft.OnScrollEvent) -> None:
        if not self.sizes:
            return
        middle = e.pixels + (e.viewport_dimension or 0) / 3
        i = 0
        while i + 1 < len(self.sizes) and self._offset(i + 1) <= middle:
            i += 1
        if i != self.current:
            self.current = i
            self._update_label()
            self.page_label.update()

    def _update_label(self) -> None:
        self.page_label.value = self.app.t("Page {n} / {total}", n=self.current + 1, total=len(self.sizes))

    def _render(self, i: int, reading: tuple = ((), ())) -> bytes:
        width = int(max(1000, self._page_w() * 1.3))
        marks = hl.page_marks(self.highlights, self.words, i)
        return preview.render_highlight(self.app.converted_pdf, i, width, list(reading[0]), list(reading[1]),
                                        bool(self.app.ui.get("dark_mode")), marks)

    def _start_rendering(self) -> None:
        if self._render_task:
            self._render_task.cancel()
        self._render_task = asyncio.get_running_loop().create_task(self._render_all())

    async def _render_all(self) -> None:
        """Pages near the one being read first, then the rest, so the view fills quickly."""
        order = sorted(range(len(self.images)), key=lambda i: abs(i - self.current))
        for n, i in enumerate(order):
            if not self.active:
                return
            self.images[i].src = await self.app.in_thread(self._render, i)
            if n < 3 or n % 4 == 3 or n == len(order) - 1:
                self.app.page.update()

    async def redraw(self, i: int, reading: tuple = ((), ())) -> None:
        if 0 <= i < len(self.images):
            self.images[i].src = await self.app.in_thread(self._render, i, reading)
            self.images[i].update()

    async def refresh(self) -> None:
        """The document was converted again (a setting changed): show the new pages."""
        if not self.active:
            return
        old = max(1, len(self.sizes))
        await self._build_pages()
        self.current = min(len(self.sizes) - 1, round(self.current * len(self.sizes) / old))
        self.app.page.update()
        await self.scroll_to(self.current, animate=False)
        self._start_rendering()

    def _zoom_by(self, d: float) -> None:
        self.zoom = round(max(0.6, min(1.8, self.zoom + d)), 2)
        self.app.ui["focus_zoom"] = self.zoom
        self.app.store.save_ui(self.app.ui)
        w = self._page_w()
        for frame, (pw, ph) in zip(self.frames, self.sizes):
            frame.width, frame.height = w, w * ph / pw
        self.app.page.update()
        self.app.page.run_task(self.scroll_to, self.current, False)
        self._start_rendering()

    def on_size(self, e) -> None:
        self.boxes[e.control.data] = (e.width, e.height)

    def _point(self, i: int, x: float, y: float) -> Optional[tuple[float, float]]:
        box = self.boxes.get(i)
        if not box or i >= len(self.sizes):
            return None
        return preview.tap_to_page(x, y, box[0], box[1], *self.sizes[i])

    # ------------------------------------------------------------------ reading aloud
    async def show_reading(self, page: int, sentence: list, word: list, follow: bool) -> None:
        if follow and page != self.current:
            await self.scroll_to(page)
        if self._reading_page is not None and self._reading_page != page:
            await self.redraw(self._reading_page)  # take the reading highlight off the previous page
        self._reading_page = page
        await self.redraw(page, (sentence, word))

    async def reading_done(self) -> None:
        if self._reading_page is not None:
            page, self._reading_page = self._reading_page, None
            await self.redraw(page)

    async def on_tap(self, e) -> None:
        i = e.control.data
        pt = self._point(i, e.local_position.x, e.local_position.y)
        if pt is None:
            return
        if self.tool:  # a tap with the highlighter marks (or erases) one word
            n = hl.word_at(hl.words_on_page(self.words, i), *pt)
            if n is not None:
                await self._apply(i, n, n)
            return
        app = self.app
        if not app.ui.get("tap_to_read", True) or not app._speech_allowed() or not app.speaker.voices():
            return
        si = sentence_at(await app._units(), i, *pt)
        if si is None:
            return
        if app._reading:
            app._reading = False
            app.speaker.stop()
        self.current = i
        await app.start_reading(si)

    # ------------------------------------------------------------------ highlighter
    def _toggle_style(self) -> ft.ButtonStyle:
        return ft.ButtonStyle(bgcolor={ft.ControlState.SELECTED: ft.Colors.PRIMARY_CONTAINER})

    def _swatch(self, name: str) -> ft.Control:
        chosen = name == self.colour
        return ft.Container(width=28, height=28, border_radius=14, bgcolor=SWATCHES[name], data=name,
                            border=ft.Border.all(3 if chosen else 1,
                                                 ft.Colors.PRIMARY if chosen else ft.Colors.OUTLINE),
                            on_click=self.on_colour, tooltip=self.app.t(name.capitalize()))

    def _refresh_swatches(self) -> None:
        for c in self.swatches.controls:
            if isinstance(c, ft.Container):
                chosen = self.tool == "mark" and c.data == self.colour
                c.border = ft.Border.all(3 if chosen else 1, ft.Colors.PRIMARY if chosen else ft.Colors.OUTLINE)
            else:
                c.selected = self.tool == "erase"
        self.mark_toggle.selected = self.tool is not None
        self.swatches.visible = self.tool is not None

    def _set_tool_gestures(self) -> None:
        """Dragging marks text while the highlighter is on; otherwise it scrolls the pages."""
        on = self.tool is not None
        for det in self.detectors:
            det.on_pan_start = self.on_pan_start if on else None
            det.on_pan_update = self.on_pan_update if on else None
            det.on_pan_end = self.on_pan_end if on else None
            det.mouse_cursor = ft.MouseCursor.TEXT if on else ft.MouseCursor.CLICK

    def on_marker(self, e) -> None:
        self.tool = None if self.tool else "mark"
        self._refresh_swatches()
        self._set_tool_gestures()
        self.app.page.update()

    def on_colour(self, e) -> None:
        self.colour = e.control.data
        self.tool = "mark"
        self.app.ui["focus_colour"] = self.colour
        self.app.store.save_ui(self.app.ui)
        self._refresh_swatches()
        self.app.page.update()

    def on_eraser(self, e) -> None:
        self.tool = None if self.tool == "erase" else "erase"
        self._refresh_swatches()
        self._set_tool_gestures()
        self.app.page.update()

    def on_pan_start(self, e) -> None:
        i = e.control.data
        pt = self._point(i, e.local_position.x, e.local_position.y)
        n = hl.word_at(hl.words_on_page(self.words, i), *pt) if pt else None
        self._drag = (i, n, n) if n is not None else None

    async def on_pan_update(self, e) -> None:
        if not self._drag:
            return
        i, first, last = self._drag
        pt = self._point(i, e.local_position.x, e.local_position.y)
        n = hl.word_at(hl.words_on_page(self.words, i), *pt) if pt else None
        if n is None or n == last:
            return
        self._drag = (i, first, n)
        # show the stroke while dragging
        a, b = min(first, n), max(first, n)
        preview_hl = (hl.erase if self.tool == "erase" else
                      lambda hs, a, b, w: hl.add(hs, a, b, self.colour, w))(self.highlights, a, b, self.words)
        keep, self.highlights = self.highlights, preview_hl
        try:
            await self.redraw(i)
        finally:
            self.highlights = keep

    async def on_pan_end(self, e) -> None:
        if self._drag:
            i, first, last = self._drag
            self._drag = None
            await self._apply(i, first, last)

    async def _apply(self, page: int, a: int, b: int) -> None:
        if self.tool == "erase":
            self.highlights = hl.erase(self.highlights, a, b, self.words)
        else:
            self.highlights = hl.add(self.highlights, a, b, self.colour, self.words)
        if self.doc_key:
            self.store.save(self.doc_key, self.highlights)
        await self.redraw(page)

    # ------------------------------------------------------------------ fold-out panels
    def on_read_panel(self, e) -> None:
        self.read_panel.visible = not self.read_panel.visible
        self.read_toggle.selected = self.read_panel.visible
        self.app.ui["read_panel_open"] = self.read_panel.visible
        self.app.store.save_ui(self.app.ui)
        self.app.page.update()

    def on_settings_panel(self, e) -> None:
        self.settings_panel.visible = not self.settings_panel.visible
        self.settings_toggle.selected = self.settings_panel.visible
        self.app.ui["focus_settings_open"] = self.settings_panel.visible
        self.app.store.save_ui(self.app.ui)
        self.app.page.update()

    def _settings_row(self) -> ft.Control:
        """The settings that change how the text reads; the document is converted again in place."""
        app, t = self.app, self.app.t

        async def set_value(key, value):
            setattr(app.settings, key, value)
            await app.settings_changed()

        def slider(key, label, lo, hi, step, unit):
            value_text = app.text(f"{getattr(app.settings, key):g} {unit}", 13)

            def moving(e):
                value_text.value = f"{round(float(e.control.value) / step) * step:g} {unit}"
                value_text.update()

            async def done(e):
                await set_value(key, round(round(float(e.control.value) / step) * step, 2))

            return ft.Container(ft.Column([ft.Row([app.text(label, 13), value_text], spacing=6),
                                           ft.Slider(value=getattr(app.settings, key), min=lo, max=hi,
                                                     divisions=int(round((hi - lo) / step)), on_change=moving,
                                                     on_change_end=done)], spacing=0, tight=True),
                                width=200)  # a fixed width, so the settings flow across the panel

        async def font_changed(e):
            await set_value("font", e.control.value)

        async def align_changed(e):
            await set_value("alignment", e.control.value)

        async def bold_changed(e):
            await set_value("bold_word_start", bool(e.control.value))

        return ft.Row([
            ft.Dropdown(label=t("Font"), value=app.settings.font, width=210, dense=True, text_size=app.fs(13),
                        options=[ft.DropdownOption(key=f, text=f) for f in FONT_CHOICES], on_select=font_changed),
            slider("font_size", t("Font size"), 9, 24, 0.5, "pt"),
            slider("line_spacing", t("Line spacing"), 1.0, 3.0, 0.1, "×"),
            slider("letter_spacing", t("Letter spacing"), 0, 3, 0.1, "pt"),
            slider("word_spacing", t("Word spacing"), 0, 10, 0.5, "pt"),
            slider("paragraph_spacing", t("Paragraph spacing"), 0, 36, 1, "pt"),
            ft.Dropdown(label=t("Alignment"), value=app.settings.alignment, width=210, dense=True,
                        text_size=app.fs(13), on_select=align_changed,
                        options=[ft.DropdownOption(key="left", text=t("Left (recommended)")),
                                 ft.DropdownOption(key="center", text=t("Centre")),
                                 ft.DropdownOption(key="justify", text=t("Justified"))]),
            ft.Switch(label=t("Bold the first part of each word"), value=app.settings.bold_word_start,
                      on_change=bold_changed, label_text_style=ft.TextStyle(size=app.fs(13))),
        ], wrap=True, spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER)


def _blank() -> bytes:
    from .app import _blank_png

    return _blank_png()
