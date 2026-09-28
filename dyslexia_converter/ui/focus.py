"""Focus mode: the converted document as a reader, filling the window.

All pages in one scroll, or page by page (like a PDF reader, also on a tablet), with a thin bar on top that
can be hidden. The read-aloud controls, the reading settings and the view options (page colour, scroll or
pages, fit width, rotation) fold out below the bar and fold away again, so only the text is left.
A highlighter marks words in four colours (with an eraser); highlights can carry a note, are kept per
document and follow their words when the layout changes. Pressing and holding a word (or right-clicking
it) opens a card with its syllables, its meaning and a way to hear it; a reading ruler keeps one line clear.
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional

import flet as ft

from .. import dictionary
from .. import highlights as hl
from ..fonts import FONT_CHOICES
from ..ai.providers import PROVIDERS
from ..render import preview
from ..speech import sentence_at

if TYPE_CHECKING:  # pragma: no cover
    from .app import ConverterApp

def _patch_long_press_move() -> None:
    """Flet 1.0.1 cannot read its own long-press move events: two offsets the event class requires are not sent
    by the app. Only the pointer positions are used here, so the offsets get a default of None."""
    cls = getattr(ft, "LongPressMoveUpdateEvent", None)
    init = getattr(cls, "__init__", None)
    if cls is None or getattr(init, "_patched", False):
        return

    def patched(self, *args, **kw):
        """The original constructor, with the missing offsets filled in."""
        kw.setdefault("offset_from_origin", None)
        kw.setdefault("local_offset_from_origin", None)
        init(self, *args, **kw)

    patched._patched = True
    cls.__init__ = patched


_patch_long_press_move()

SWATCHES = {"yellow": "#FFD600", "green": "#50C878", "blue": "#50A0FF", "pink": "#FF78B4"}
# page colour -> (page, background around the pages)
TINT_COLOURS = {"white": ("#FFFFFF", None), "cream": ("#FAF1D6", "#E9DFC4"), "blue": ("#D6E6F8", "#C3D3E6"),
                "green": ("#D8F0DC", "#C4DCC8"), "grey": ("#E2E2E2", "#CDCDCD"), "dark": ("#202024", "#101012")}


class FocusMode:
    """Focus mode: replaces the app's window content with a reader for the converted document.

    Created once by the app (``app.focus``); :meth:`open` builds the view and :meth:`close` puts the normal app
    back. Reader choices (zoom, page colour, layout, rotation, open panels) are kept in the app's UI settings, so
    focus mode opens the way it was left. The pages are PNG pictures rendered by :mod:`..render.preview`;
    highlights, the reading ruler, the word being read and the word on the word card are drawn into those
    pictures.
    """
    BASE_W = 820  # page width at 100 %
    GAP = 18
    PAD = 20

    def __init__(self, app: "ConverterApp"):
        """Set up the state; nothing is shown until :meth:`open`."""
        self.app = app
        self.active = False
        ui = app.ui
        self.zoom = float(ui.get("focus_zoom", 1.0))
        self.page_zoom = 1.0  # page by page: 1 = the whole page fits
        self.tool: Optional[str] = None  # None, "mark" or "erase"
        self.colour = ui.get("focus_colour", "yellow")
        self.images: list[ft.Image] = []
        self.frames: list[ft.Container] = []
        self.detectors: list[ft.GestureDetector] = []
        self.sizes: list[tuple[float, float]] = []
        self.boxes: dict[int, tuple[float, float]] = {}
        self.body_size: tuple[float, float] = (0.0, 0.0)
        self.current = 0
        self.words: list = []
        self.highlights: list[hl.Highlight] = []
        self._lines: dict[int, list] = {}
        self.ruler: Optional[tuple[int, int]] = None  # page, line
        self.card_word: Optional[tuple[int, int]] = None  # page, word number shown on the word card
        self.card_mode: Optional[str] = None  # "drag", "word", "selection", "note" or "bubble"
        self.sel: Optional[tuple[int, int]] = None  # first and last word number of the selected text
        self.sel_unit: Optional[str] = None  # "word", "sentence" or "paragraph" when selected as a whole
        self._anchor = 0  # the word first held
        self._drag_page = 0
        self._drag_to: Optional[int] = None
        self._drawing = False
        self._sentences: list[tuple[int, int]] = []
        self._paragraphs: list[tuple[int, int]] = []
        self._more = False  # the selection toolbar shows Select and Start / End
        self._pen_drag = False  # a selection being made with a mouse or pen
        self._ai_scope = "page"  # what the AI summary is of: page, section, selection or document
        self._ai_result = None  # (summary, first word, last word)
        self._ai_busy = False
        self._ai_error = ""
        self._last_sel: Optional[tuple[int, int]] = None
        self._toc_starts: list[int] = []  # first word of every heading in the converted document
        self._notes_only = False
        self._colour_filter: set[str] = set()
        self.bars_hidden = False
        self._typing = False
        self._scroll_px = 0.0
        self._render_task: Optional[asyncio.Task] = None
        self._reading: Optional[tuple[int, list, list]] = None  # page, sentence, word being read aloud
        self._drag: Optional[tuple[int, int, int]] = None  # page, first word, last word
        self._pinch: dict = {}
        self._settle: Optional[int] = None
        self._saved: list = []
        self._prev_keys = None

    # ------------------------------------------------------------------ settings kept between sessions
    @property
    def tint(self) -> str:
        """The page colour (white, cream, blue, green, grey or dark); dark by default in the app's dark mode."""
        default = "dark" if self.app.ui.get("dark_mode") else "white"
        return self.app.ui.get("focus_tint", default)

    @property
    def layout(self) -> str:
        """"scroll" (all pages in one scrolling column) or "pages" (one page at a time)."""
        return self.app.ui.get("focus_layout", "scroll")

    @property
    def fit(self) -> bool:
        """Whether the pages are as wide as the window (scrolling layout only)."""
        return bool(self.app.ui.get("focus_fit", False))

    @property
    def turns(self) -> int:
        """How many quarter turns the reading view is rotated (0-3)."""
        return int(self.app.ui.get("focus_rotation", 0)) % 4

    def _save(self, key: str, value) -> None:
        """Remember a reader choice in the app's UI settings (saved to disk at once)."""
        self.app.ui[key] = value
        self.app.store.save_ui(self.app.ui)

    # ------------------------------------------------------------------ open / close
    async def open(self) -> None:
        """Show focus mode for the converted document, starting at the page the Convert tab shows.

        Builds the top bar, the fold-out panels (read aloud, reading settings, view), the page list or single
        page view, the word card layer and the button that brings hidden bars back, all inside a RotatedBox so
        the whole view can be turned. The keyboard handler is replaced for arrow keys and Esc until
        :meth:`close`.
        """
        app, t = self.app, self.app.t
        if not app.converted_pdf:
            app.notify(t("Open a PDF first."), error=True)
            return
        self.active = True
        self.current = app.conv_page
        self.highlights = app.doc_highlights()
        self.ruler, self.card_word, self._reading, self.bars_hidden = None, None, None, False
        self.sel, self.card_mode = None, None
        self.page_zoom = 1.0
        del app.hl_items[1:]  # forget the menu of an earlier focus mode

        self.page_label = app.text("", 14)
        self.read_toggle = ft.IconButton(ft.Icons.VOLUME_UP, tooltip=t("Read aloud"), on_click=self.on_read_panel,
                                         selected=bool(app.ui.get("read_panel_open", False)),
                                         style=self._toggle_style(), visible=app._speech_allowed())
        self.settings_toggle = ft.IconButton(ft.Icons.TEXT_FIELDS, tooltip=t("Reading settings: text, spacing and "
                                                                           "page colour"),
                                             on_click=self.on_settings_panel,
                                             selected=bool(app.ui.get("focus_settings_open", False)),
                                             style=self._toggle_style())
        self.mark_toggle = ft.IconButton(ft.Icons.BORDER_COLOR, tooltip=t("Highlighter"), on_click=self.on_marker,
                                         style=self._toggle_style())
        self.swatches = ft.Row([self._swatch(name) for name in SWATCHES] + [
            ft.IconButton(ft.Icons.AUTO_FIX_NORMAL, tooltip=t("Eraser"), data="erase", on_click=self.on_eraser,
                          style=self._toggle_style())], spacing=4, visible=False)
        self.notes_toggle = ft.IconButton(ft.Icons.STICKY_NOTE_2_OUTLINED, tooltip=t("Notes and highlights"),
                                          on_click=self.on_notes_panel, style=self._toggle_style())
        self.ruler_toggle = ft.IconButton(ft.Icons.STRAIGHTEN, tooltip=t("Reading ruler (move it with the arrow "
                                                                         "keys or by tapping a line)"),
                                          on_click=self.on_ruler, style=self._toggle_style())
        self.top = ft.Container(ft.Row([
            ft.IconButton(ft.Icons.CLOSE, tooltip=t("Leave focus mode"), on_click=self.on_close),
            ft.Container(width=4),
            self.read_toggle, self.settings_toggle, self.mark_toggle, self.swatches,
            self.ruler_toggle, self.notes_toggle, self._ai_button(),
            ft.Container(expand=True),
            self.page_label,
            app.build_export_menu(compact=True),
            *self._page_buttons(),
            ft.IconButton(ft.Icons.ZOOM_OUT, tooltip=t("Smaller"), on_click=lambda e: self._zoom_by(1 / 1.1)),
            ft.IconButton(ft.Icons.ZOOM_IN, tooltip=t("Larger"), on_click=lambda e: self._zoom_by(1.1)),
            ft.IconButton(ft.Icons.FULLSCREEN, tooltip=t("Hide the bars (Esc brings them back)"),
                          on_click=self.on_hide_bars),
        ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=8, vertical=2), bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
            clip_behavior=ft.ClipBehavior.HARD_EDGE)

        # the read-aloud controls move here from the main view while focus mode is open
        app.read_panel.content = None
        self.read_panel = self._panel(app.read_row, "read_panel_open")
        # one panel for how the text and page look (read aloud keeps its own)
        self.settings_panel = self._panel(self._settings_row(), "focus_settings_open")
        self.divider = ft.Divider(height=1)
        self.list = ft.ListView(expand=True, spacing=self.GAP, on_scroll=self.on_scroll,
                                padding=ft.Padding.symmetric(vertical=self.PAD))
        self.pager_row = ft.Row([], alignment=ft.MainAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO)
        self.pager = ft.Stack([
            ft.Column([self.pager_row], alignment=ft.MainAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO,
                      horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
            ft.Container(ft.IconButton(ft.Icons.CHEVRON_LEFT, icon_size=36, tooltip=t("Previous page"),
                                       on_click=lambda e: self.app.page.run_task(self.turn, -1)),
                         left=4, top=0, bottom=0, alignment=ft.Alignment.CENTER_LEFT),
            ft.Container(ft.IconButton(ft.Icons.CHEVRON_RIGHT, icon_size=36, tooltip=t("Next page"),
                                       on_click=lambda e: self.app.page.run_task(self.turn, 1)),
                         right=4, top=0, bottom=0, alignment=ft.Alignment.CENTER_RIGHT),
        ], expand=True)
        # the list is on the page from the start: a list added later ignores the first scroll
        # a key keeps the scroll position when a panel above folds out or away
        self.body = ft.Container(self.list if self.layout == "scroll" else self.pager, expand=True,
                                 on_size_change=self.on_body_size, key="focus-body",
                                 on_click=self.on_background_click)
        # the notes list: beside the pages, no width while closed (a control taken out of the row would make
        # the page list forget how far it was scrolled)
        self.side = ft.Container(width=0, bgcolor=ft.Colors.SURFACE, border=ft.Border.only(
            left=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)))
        self.card_layer = ft.Container(left=0, right=0, bottom=12, visible=False,
                                       alignment=ft.Alignment.BOTTOM_CENTER)
        self.show_bars = ft.Container(ft.IconButton(ft.Icons.FULLSCREEN_EXIT, tooltip=t("Show the bars"),
                                                    on_click=self.on_show_bars, icon_color="#FFFFFF"),
                                      bgcolor="#66000000", border_radius=24, right=10, top=10, visible=False)
        self.counter = ft.Container(ft.Text("", color="#FFFFFF", size=13), bgcolor="#88000000", border_radius=14,
                                    padding=ft.Padding.symmetric(horizontal=12, vertical=4), visible=False)
        self.column = ft.Column([self.top, self.read_panel, self.settings_panel, self.divider,
                                 ft.Row([self.body, self.side], expand=True, spacing=0,
                                        vertical_alignment=ft.CrossAxisAlignment.STRETCH)],
                                expand=True, spacing=0, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.root = ft.RotatedBox(content=ft.Stack([self.column, ft.Row([self.counter], left=0, right=0, bottom=10,
                                                                 alignment=ft.MainAxisAlignment.CENTER),
                                            self.card_layer, self.show_bars], expand=True),
                                  quarter_turns=self.turns, expand=True)
        self._saved = list(app.page.controls)
        app.page.controls.clear()
        app.page.add(self.root)
        self._prev_keys = app.page.on_keyboard_event
        app.page.on_keyboard_event = self.on_key
        self._apply_tint()
        await self._build_pages()
        app.page.update()
        await self._show_layout()
        self._start_rendering()

    async def on_background_click(self, e) -> None:
        """A click beside the pages clears the selection and closes the card."""
        if self.card_layer.visible or self.sel:
            await self.close_card()

    def _panel(self, content: ft.Control, key: str) -> ft.Container:
        """A panel that folds out below the top bar, open or folded as it was left (``key`` in the UI settings)."""
        panel = ft.Container(data=content, bgcolor=ft.Colors.SURFACE_CONTAINER_LOW)
        self._fold(panel, bool(self.app.ui.get(key, False)))
        return panel

    @staticmethod
    def _fold(panel: ft.Container, open_: bool) -> None:
        """Show or hide a panel above the pages. It stays in place with no height when folded away:
        taking it out of the column would make the page list forget how far it was scrolled."""
        panel.content = panel.data if open_ else None
        panel.padding = ft.Padding.symmetric(horizontal=12, vertical=4) if open_ else 0

    @staticmethod
    def _is_open(panel: ft.Container) -> bool:
        """Whether a fold-out panel is showing (see :meth:`_fold`)."""
        return panel.content is not None

    async def close(self) -> None:
        """Leave focus mode: give the app back its own view, the read-aloud controls and keyboard handler."""
        app = self.app
        if not self.active:
            return
        self.active = False
        if self._render_task:
            self._render_task.cancel()
        if self.bars_hidden:
            self._full_screen(False)
        app.page.on_keyboard_event = self._prev_keys
        self.read_panel.content = self.read_panel.data = None
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
        """The close (X) button."""
        await self.close()

    # ------------------------------------------------------------------ pages
    def on_body_size(self, e) -> None:
        """The area for the pages changed size (window resized, panel opened, rotated): refit the pages."""
        old = self.body_size
        self.body_size = (e.width, e.height)
        # page by page the page fits the height too; a scrolling list only follows the width
        changed = abs(old[0] - e.width) > 2 or (self.layout == "pages" and abs(old[1] - e.height) > 2)
        if self.active and self.sizes and changed:
            self._resize()

    def _avail(self) -> tuple[float, float]:
        """Width and height available for the pages, in the rotated view's own directions."""
        w, h = self.body_size
        if not w or not h:
            pw, ph = self.app.page.width or 1200, (self.app.page.height or 800) - 60
            w, h = (ph, pw) if self.turns % 2 else (pw, ph)
        return w, h

    def _page_w(self, i: Optional[int] = None) -> float:
        """How wide page ``i`` is shown, in pixels.

        Page by page it fits the available area (times the page zoom); scrolling, it is the zoomed page width,
        or the window width with *Fit width*.
        """
        w, h = self._avail()
        if self.layout == "pages":
            pw, ph = self.sizes[i if i is not None else self.current] if self.sizes else (595, 842)
            fit = min((w - 110) / pw, (h - 24) / ph) * pw
            return max(200.0, fit * self.page_zoom)
        if self.fit:
            return max(240.0, w - 40)
        return max(240.0, min(self.BASE_W * self.zoom, w - 40))

    async def _build_pages(self) -> None:
        """Create one frame per page of the converted document (blank until rendered) and read its words."""
        app = self.app
        pdf = app.converted_pdf
        n = preview.page_count(pdf)
        self.sizes = [await app.in_thread(preview.page_size, pdf, i) for i in range(n)]
        units = await app._units()
        self.words = hl.document_words(units)
        self._sentences = hl.sentence_spans(self.words)
        self._paragraphs = hl.paragraph_spans(self.words)
        self._toc_starts = await app.in_thread(self._heading_starts)
        self._lines = {}
        page_bg = TINT_COLOURS.get(self.tint, TINT_COLOURS["white"])[0]
        self.images, self.frames, self.detectors, self.overlays = [], [], [], []
        for i, (pw, ph) in enumerate(self.sizes):
            img = ft.Image(src=_blank(), fit=ft.BoxFit.FILL, gapless_playback=True, expand=True)
            # the selection and the picked word are drawn as a few shapes over the picture: moving them while
            # dragging is instant, where drawing them into the picture meant rendering the whole page again
            overlay = ft.Stack([])
            # a mouse or pen selects by dragging; a finger scrolls (and selects with press-and-hold)
            pen = ft.GestureDetector(content=ft.Stack([img, overlay], fit=ft.StackFit.EXPAND), data=i,
                                     allowed_devices=[
                ft.PointerDeviceType.MOUSE, ft.PointerDeviceType.STYLUS, ft.PointerDeviceType.INVERTED_STYLUS],
                on_pan_start=self.on_pen_start, on_pan_update=self.on_pen_move, on_pan_end=self.on_pen_end)
            det = ft.GestureDetector(content=pen, data=i, on_double_tap_down=self.on_double_tap, on_tap_up=self.on_tap,  # up: holding is not a tap
                                     on_long_press_start=self.on_select_start,
                                     on_long_press_move_update=self.on_select_move,
                                     on_long_press_end=self.on_select_end, on_secondary_tap_down=self.on_word_card,
                                     on_size_change=self.on_size, mouse_cursor=ft.MouseCursor.CLICK, expand=True)
            w = self._page_w(i)
            frame = ft.Container(det, width=w, height=w * ph / pw, bgcolor=page_bg,
                                 shadow=ft.BoxShadow(blur_radius=10, color="#33000000"))
            self.images.append(img)
            self.overlays.append(overlay)
            self.detectors.append(det)
            self.frames.append(frame)
        self.current = min(self.current, n - 1)
        if self.ruler and self.ruler[0] >= n:
            self.ruler = None
        self._set_tool_gestures()
        self._update_label()

    async def _show_layout(self) -> None:
        """Put the pages in one scroll, or show the current page on its own."""
        if self.layout == "pages":
            self.list.controls = []
            self.pager_row.controls = [self.frames[self.current]] if self.frames else []
            self.body.content = self.pager
        else:
            self.pager_row.controls = []
            self.list.controls = [ft.Row([f], alignment=ft.MainAxisAlignment.CENTER) for f in self.frames]
            self.body.content = self.list
        self._resize(update=False)
        self._update_label()
        self.app.page.update()
        if self.layout == "scroll":
            self._settle = self.current  # a new list only scrolls once laid out: done again after drawing
            await self.scroll_to(self.current, animate=False)

    def _resize(self, update: bool = True) -> None:
        """Give every page frame its size for the current zoom, layout and window."""
        for i, (frame, (pw, ph)) in enumerate(zip(self.frames, self.sizes)):
            w = self._page_w(i)
            frame.width, frame.height = w, w * ph / pw
        for i in self._marked_pages():  # the selection's shapes are in pixels: place them for the new size
            if 0 <= i < len(self.overlays):
                self.overlays[i].controls = self._selection_shapes(i)
        if update:
            self.app.page.update()

    def _offset(self, i: int) -> float:
        """Scroll position (pixels) of the top of page ``i`` in the scrolling layout."""
        return self.PAD + sum(self._page_w(k) * ph / pw + self.GAP for k, (pw, ph) in enumerate(self.sizes[:i]))

    async def scroll_to(self, i: int, animate: bool = True, within: float = 0.0) -> None:
        """Show page ``i`` (``within``: points from its top that should come into view)."""
        i = max(0, min(i, len(self.sizes) - 1))
        if self.layout == "pages":
            if i != self.current or not self.pager_row.controls:
                self.current = i
                self.pager_row.controls = [self.frames[i]]
                self.page_zoom = 1.0
                self._resize(update=False)
                self._update_label()
                self.app.page.update()
            return
        pw, ph = self.sizes[i]
        target = self._offset(i) + max(0.0, within * self._page_w(i) / pw - self._avail()[1] / 3)
        try:
            await self.list.scroll_to(offset=target, duration=250 if animate else 0)
        except Exception:
            pass
        self.current = i
        self._update_label()
        self.page_label.update()

    async def turn(self, step: int) -> None:
        """Go ``step`` pages forward (1) or back (-1)."""
        await self.scroll_to(self.current + step)

    def on_scroll(self, e: ft.OnScrollEvent) -> None:
        """Follow scrolling: the page a third of the way down the view is the current page."""
        if not self.sizes or self.layout == "pages":
            return
        self._scroll_px = e.pixels
        if e.pixels > 0:
            self._settle = None
        middle = e.pixels + (e.viewport_dimension or 0) / 3
        i = 0
        while i + 1 < len(self.sizes) and self._offset(i + 1) <= middle:
            i += 1
        if i != self.current:
            self.current = i
            self._update_label()
            self.page_label.update()

    def _update_label(self) -> None:
        """Show the current page number in the top bar and in the counter over the pages."""
        text = self.app.t("Page {n} / {total}", n=self.current + 1, total=len(self.sizes))
        self.page_label.value = text
        self.counter.content.value = f"{self.current + 1} / {len(self.sizes)}"
        self.counter.visible = self.bars_hidden or self.layout == "pages"

    def _lines_of(self, i: int) -> list:
        """The lines of text on page ``i`` (for the reading ruler), worked out once and kept."""
        if i not in self._lines:
            self._lines[i] = hl.lines_on_page(self.words, i)
        return self._lines[i]

    def _render(self, i: int) -> bytes:
        """PNG of page ``i`` with everything drawn on it: highlights, note signs, the sentence and word being
        read, the reading ruler, the word on the word card, in the page colour.
        """
        width = int(max(1000, self._page_w(i) * 1.3))
        marks = hl.page_marks(self.highlights, self.words, i)
        sentence, word = (self._reading[1], self._reading[2]) if self._reading and self._reading[0] == i else ((), ())
        ruler = ()
        if self.ruler and self.ruler[0] == i:
            lines = self._lines_of(i)
            if lines:
                ruler = lines[min(self.ruler[1], len(lines) - 1)]
        # (the selection and the picked word are shapes over the picture: see _paint_selection)
        return preview.render_highlight(self.app.converted_pdf, i, width, list(sentence), list(word),
                                        marks=marks, tint=self.tint, ruler=ruler,
                                        notes=hl.note_marks(self.highlights, self.words, i))

    def _start_rendering(self) -> None:
        """(Re)start rendering all pages in the background (after a zoom, colour or layout change)."""
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
            if n == 2 and self._settle is not None and self.layout == "scroll":
                page, self._settle = self._settle, None
                await self.scroll_to(page, animate=False)

    async def redraw(self, i: int) -> None:
        """Render page ``i`` again and show it (after a highlight, ruler or reading change)."""
        if 0 <= i < len(self.images):
            self.images[i].src = await self.app.in_thread(self._render, i)
            try:
                self.images[i].update()
            except Exception:  # not on screen (page by page)
                pass

    async def refresh(self) -> None:
        """The document was converted again (a setting changed): show the new pages."""
        if not self.active:
            return
        old = max(1, len(self.sizes))
        self.card_word, self.sel, self.card_mode = None, None, None
        self.card_layer.visible = False
        await self._build_pages()
        self._refresh_notes()
        self.current = min(len(self.sizes) - 1, round(self.current * len(self.sizes) / old))
        await self._show_layout()
        self._start_rendering()

    def _zoom_by(self, factor: float) -> None:
        """Make the pages ``factor`` times larger (or smaller); page by page this zooms into the page."""
        if self.layout == "pages":
            self.page_zoom = round(max(1.0, min(3.0, self.page_zoom * factor)), 3)
        else:
            base = self._page_w() / self.BASE_W if self.fit else self.zoom
            self.zoom = round(max(0.5, min(2.5, base * factor)), 3)
            self._save("focus_zoom", self.zoom)
            self._save("focus_fit", False)
            self._refresh_view_row()
        self._resize()
        if self.layout == "scroll":
            self.app.page.run_task(self.scroll_to, self.current, False)
        self._start_rendering()

    def on_size(self, e) -> None:
        """Remember how large each page picture is on screen, to turn taps into page positions."""
        self.boxes[e.control.data] = (e.width, e.height)

    def _point(self, i: int, x: float, y: float) -> Optional[tuple[float, float]]:
        """Where a tap at (x, y) on page picture ``i`` lands on the page, in PDF points (None beside it)."""
        box = self.boxes.get(i)
        if not box or i >= len(self.sizes):
            return None
        return preview.tap_to_page(x, y, box[0], box[1], *self.sizes[i])

    # ------------------------------------------------------------------ touch: pinch to zoom, swipe to turn
    def on_scale_start(self, e) -> None:
        """Start of a touch gesture on a page: two fingers zoom, one finger (page by page) swipes."""
        self._pinch = {"scale": 1.0, "dx": 0.0, "fingers": 1}

    def on_scale_update(self, e) -> None:
        """Track the gesture: how far two fingers spread, or how far one finger moved sideways."""
        p = self._pinch
        p["fingers"] = max(p.get("fingers", 1), e.pointer_count or 1)
        if (e.pointer_count or 1) >= 2:
            p["scale"] = e.scale
        else:
            p["dx"] = p.get("dx", 0.0) + (e.focal_point_delta.x if e.focal_point_delta else 0.0)

    async def on_scale_end(self, e) -> None:
        """End of the gesture: zoom by the pinch, or turn the page after a swipe of 60 pixels or more."""
        p, self._pinch = self._pinch, {}
        if not p:
            return
        if p.get("fingers", 1) >= 2 and abs(p.get("scale", 1.0) - 1) > 0.05:
            self._zoom_by(p["scale"])
        elif self.layout == "pages" and abs(p.get("dx", 0.0)) > 60:
            await self.turn(1 if p["dx"] < 0 else -1)

    # ------------------------------------------------------------------ keyboard
    async def on_key(self, e) -> None:
        """Keys while focus mode is open.

        Esc closes the card or toolbar (clearing the selection) or brings hidden bars back. With text
        selected: Ctrl+C copies, 1-4 highlight in a colour, N opens the note, Delete removes the highlight.
        Up/down move the reading ruler (or scroll); right, left, Page Up/Down and space turn pages. Keys are
        ignored while a note is being typed.
        """
        if not self.active:
            return
        key = e.key
        if key == "Escape":
            if self.card_layer.visible:
                await self.close_card()
            elif self.bars_hidden:
                self.on_show_bars(None)
            return
        if self._typing:  # writing a note
            return
        if self.sel and self.card_mode == "selection":
            a, b = self.sel
            if key.upper() == "C" and (e.ctrl or e.meta):
                await self.copy(a, b)
                return
            if key in ("1", "2", "3", "4"):
                await self.mark(a, b, list(SWATCHES)[int(key) - 1])
                return
            if key.upper() == "N":
                await self.open_note(a, b)
                return
            if key in ("Delete", "Backspace") and self._exact(a, b) is not None:
                await self.unmark(a, b)
                return
        if key in ("Arrow Down", "Arrow Up"):
            step = 1 if key == "Arrow Down" else -1
            if self.ruler:
                await self.move_ruler(step)
            elif self.layout == "scroll":
                try:
                    await self.list.scroll_to(offset=max(0.0, self._scroll_px + 120 * step), duration=120)
                except Exception:
                    pass
        elif key in ("Arrow Right", "Page Down", " "):
            await self.turn(1)
        elif key in ("Arrow Left", "Page Up"):
            await self.turn(-1)

    # ------------------------------------------------------------------ reading aloud
    async def show_reading(self, page: int, sentence: list, word: list, follow: bool) -> None:
        """Show the sentence and word being read aloud on ``page`` (the ruler follows, the view too when
        ``follow``).
        """
        previous = self._reading[0] if self._reading else None
        self._reading = (page, sentence, word)
        if self.ruler and word:  # the ruler follows the voice
            line = self._line_at(page, (word[0][1] + word[0][3]) / 2)
            if line is not None and (page, line) != self.ruler:
                old = self.ruler[0]
                self.ruler = (page, line)
                if old != page:
                    await self.redraw(old)
        if follow and page != self.current:
            await self.scroll_to(page)
        if previous is not None and previous != page:
            await self.redraw(previous)  # take the reading highlight off the previous page
        await self.redraw(page)

    async def reading_done(self) -> None:
        """Reading aloud stopped: take the reading highlight off the page."""
        if self._reading is not None:
            page, self._reading = self._reading[0], None
            await self.redraw(page)

    async def on_tap(self, e) -> None:
        """A tap on a page.

        With the highlighter on it marks (or erases) one word; with text selected or a card open it clears the
        selection and closes the card; on a note sign it opens the note; on a highlight it opens the
        highlight's toolbar; with the ruler on it moves the ruler to that line; and with *tap to read* on,
        reading aloud starts at the sentence tapped.
        """
        i = e.control.data
        pt = self._point(i, e.local_position.x, e.local_position.y)
        if pt is None:
            return
        if self.tool:  # a tap with the highlighter marks (or erases) one word
            n = hl.word_at(hl.words_on_page(self.words, i), *pt)
            if n is not None:
                await self._apply(i, n, n)
            return
        if self.card_layer.visible or self.sel:  # a tap anywhere else clears the selection and closes the card
            await self.close_card()
            return
        for x, y in hl.note_marks(self.highlights, self.words, i):  # the note sign opens the note
            half = hl.NOTE_SIGN / 2
            if abs(pt[0] - (x + half)) < half + 6 and abs(pt[1] - (y + half)) < half + 6:
                k = next(k for k, h in enumerate(self.highlights)
                         if h.note and hl.note_marks([h], self.words, i) == [(x, y)])
                await self.open_bubble(k)
                return
        n = hl.word_at(hl.words_on_page(self.words, i), *pt)
        k = hl.at(self.highlights, n, self.words) if n is not None else None
        if k is not None:  # a tap on a highlight: its toolbar (colour, note, copy, read, remove)
            self._anchor, self.sel_unit = n, None
            await self.open_selection(*hl.resolve(self.highlights[k], self.words))
            return
        if self.ruler:
            line = self._line_at(i, pt[1])
            if line is not None:
                await self._set_ruler(i, line)
        app = self.app
        if not app.ui.get("tap_to_read", False) or not app._speech_allowed() or not app.speaker.voices():
            return
        si = sentence_at(await app._units(), i, *pt)
        if si is None:
            return
        if app._reading:
            app._reading = False
            app.speaker.stop()
        self.current = i
        await app.start_reading(si)

    # ------------------------------------------------------------------ reading ruler
    def _line_at(self, i: int, y: float) -> Optional[int]:
        """The line of page ``i`` nearest to height ``y`` (points), or None on a page without text."""
        lines = self._lines_of(i)
        if not lines:
            return None
        return min(range(len(lines)), key=lambda k: abs((lines[k][0] + lines[k][1]) / 2 - y))

    async def on_ruler(self, e) -> None:
        """The ruler button: switch the reading ruler on (at the first line of the current page) or off."""
        if self.ruler:
            page, self.ruler = self.ruler[0], None
            self.ruler_toggle.selected = False
            self.ruler_toggle.update()
            await self.redraw(page)
            return
        i = self.current
        while i < len(self.sizes) - 1 and not self._lines_of(i):
            i += 1
        if not self._lines_of(i):
            return
        self.ruler_toggle.selected = True
        self.ruler_toggle.update()
        await self._set_ruler(i, 0)

    async def _set_ruler(self, page: int, line: int) -> None:
        """Put the ruler on a line and redraw the page(s) involved."""
        old = self.ruler
        self.ruler = (page, line)
        if old and old[0] != page:
            await self.redraw(old[0])
        await self.redraw(page)

    async def move_ruler(self, step: int) -> None:
        """Move the ruler ``step`` lines down (1) or up (-1), on to the next or previous page when needed."""
        page, line = self.ruler
        line += step
        while not (0 <= line < len(self._lines_of(page))):
            page += 1 if step > 0 else -1
            if not (0 <= page < len(self.sizes)):
                return
            line = 0 if step > 0 else len(self._lines_of(page)) - 1
        await self._set_ruler(page, line)
        top = self._lines_of(page)[line][0]
        if self.layout == "pages":
            if page != self.current:
                await self.scroll_to(page)
        else:
            await self.scroll_to(page, within=top)

    # ------------------------------------------------------------------ selecting text
    def _word_near(self, i: int, x: float, y: float, clamp: bool = False) -> Optional[int]:
        """The word nearest to a point on page picture ``i`` (``clamp``: a point beside the page counts as its
        edge, so dragging past the text still selects up to the last word)."""
        box = self.boxes.get(i)
        if clamp and box:
            x, y = max(0.0, min(box[0], x)), max(0.0, min(box[1], y))
        pt = self._point(i, x, y)
        return hl.word_at(hl.words_on_page(self.words, i), *pt) if pt else None

    def _pages_of(self, span: Optional[tuple[int, int]]) -> set[int]:
        """The pages a range of words is on."""
        if not span:
            return set()
        return {self.words[k][0] for k in range(span[0], span[1] + 1) if 0 <= k < len(self.words)}

    async def _show_selection(self, span: Optional[tuple[int, int]]) -> None:
        """Select words a..b (or nothing) and show it on the pages involved."""
        old = self._pages_of(self.sel)
        self.sel = (min(span), max(span)) if span else None
        self._paint_selection(old | self._pages_of(self.sel))

    def _marked_pages(self) -> set[int]:
        """The pages with a selection or a picked word on them now."""
        return self._pages_of(self.sel) | ({self.card_word[0]} if self.card_word else set())

    def _paint_selection(self, pages: Iterable[int]) -> None:
        """Draw the selection (light blue bands with a handle at each end) and the word on the word card (an
        outline) over these pages: a few shapes, so it keeps up with the pointer."""
        for i in pages:
            if 0 <= i < len(self.overlays):
                self.overlays[i].controls = self._selection_shapes(i)
                try:
                    self.overlays[i].update()
                except Exception:  # not on screen (page by page)
                    pass

    def _selection_shapes(self, i: int) -> list[ft.Control]:
        """The shapes for page ``i``: the selected bands and handles, and the picked word's outline, placed in
        screen pixels for the page's current size."""
        if i >= len(self.sizes):
            return []
        s = self._page_w(i) / self.sizes[i][0]  # screen pixels per PDF point
        edge = "#E66E82" if self.tint == "dark" else "#7A2E3A"
        shapes: list[ft.Control] = []
        if self.card_mode == "word" and self.card_word and self.card_word[0] == i \
                and 0 <= self.card_word[1] < len(self.words):
            for x0, y0, x1, y1 in self.words[self.card_word[1]][2]:
                shapes.append(ft.Container(left=x0 * s - 4, top=y0 * s - 3, width=(x1 - x0) * s + 8,
                                           height=(y1 - y0) * s + 6, border_radius=5,
                                           border=ft.Border.all(2.5, edge)))
        # a highlight tapped keeps its own colour (its toolbar shows it is chosen)
        if self.sel and self.card_mode in ("drag", "selection", "note") and self._exact(*self.sel) is None:
            bands = hl.bands([r for p, _, rs in self.words[self.sel[0]:self.sel[1] + 1] if p == i for r in rs])
            for x0, y0, x1, y1 in bands:
                shapes.append(ft.Container(left=x0 * s - 2, top=y0 * s - 1, width=(x1 - x0) * s + 4,
                                           height=(y1 - y0) * s + 3, bgcolor="#5A5096FF"))
            if bands:
                blue, r = "#1565C0", 5 * s
                (sx, sy0, _, sy1), (_, ey0, ex, ey1) = bands[0], bands[-1]
                shapes += [  # the start handle: a bar with a dot on top; the end handle: a dot below
                    ft.Container(left=sx * s - 4, top=sy0 * s - 2, width=2, height=(sy1 - sy0) * s + 4, bgcolor=blue),
                    ft.Container(left=sx * s - 3 - r, top=sy0 * s - 2 - 2 * r, width=2 * r, height=2 * r,
                                 border_radius=r, bgcolor=blue),
                    ft.Container(left=ex * s + 2, top=ey0 * s - 2, width=2, height=(ey1 - ey0) * s + 4, bgcolor=blue),
                    ft.Container(left=ex * s + 3 - r, top=ey1 * s + 2, width=2 * r, height=2 * r,
                                 border_radius=r, bgcolor=blue)]
        return shapes

    async def _start_selection(self, i: int, x: float, y: float) -> None:
        """Start selecting at the word under (x, y) on page picture ``i``."""
        n = self._word_near(i, x, y)
        if n is None:
            return
        self.card_mode = "drag"
        self.card_layer.visible = False
        self.card_layer.content = None
        self._anchor, self._drag_page, self.sel_unit = n, i, None
        self.app.page.update()
        await self._show_selection((n, n))

    async def _extend_selection(self, i: int, x: float, y: float) -> None:
        """While dragging: the selection runs from the first word to the word under the pointer."""
        if self.card_mode != "drag" or self._drag_page != i:
            return
        n = self._word_near(i, x, y, clamp=True)
        if n is None:
            return
        self._drag_to = n
        if self._drawing:  # a redraw is running: it picks up the newest word when it is done
            return
        self._drawing = True
        try:
            while self._drag_to is not None and (self.sel is None or
                                                 (min(self._anchor, self._drag_to), max(self._anchor, self._drag_to))
                                                 != self.sel):
                await self._show_selection((self._anchor, self._drag_to))
        finally:
            self._drawing = False

    async def on_select_start(self, e) -> None:
        """Press and hold (finger): select the word; keep holding and drag to select more."""
        if not self.tool and e.local_position:
            await self._start_selection(e.control.data, e.local_position.x, e.local_position.y)

    async def on_select_move(self, e) -> None:
        """Holding and dragging a finger: extend the selection."""
        await self._extend_selection(e.control.data, e.local_position.x, e.local_position.y)

    async def on_select_end(self, e) -> None:
        """Letting go after holding: the word card for one word (with its meaning), the toolbar for more."""
        if self.card_mode != "drag" or not self.sel:
            return
        self._drag_to = None
        a, b = self.sel
        if a == b:
            await self.open_card(self._drag_page, a)
        else:
            await self.open_selection(a, b)

    async def on_pen_start(self, e) -> None:
        """Mouse or pen drag: selects text straight away (with the highlighter on, it marks instead)."""
        if self.tool:
            self.on_pan_start(e)
            return
        self._pen_drag = True
        await self._start_selection(e.control.data, e.local_position.x, e.local_position.y)

    async def on_pen_move(self, e) -> None:
        """Mouse or pen drag: extend the selection (or the highlighter stroke)."""
        if self.tool:
            await self.on_pan_update(e)
            return
        await self._extend_selection(e.control.data, e.local_position.x, e.local_position.y)

    async def on_pen_end(self, e) -> None:
        """Mouse or pen let go: show the toolbar for the selected text."""
        if self.tool:
            await self.on_pan_end(e)
            return
        self._pen_drag = False
        if self.card_mode == "drag" and self.sel:
            self._drag_to = None
            await self.open_selection(*self.sel)

    async def on_double_tap(self, e) -> None:
        """Double-click or double-tap a word: select it and show the toolbar."""
        if self.tool or not e.local_position:
            return
        n = self._word_near(e.control.data, e.local_position.x, e.local_position.y)
        if n is not None:
            self._anchor, self.sel_unit = n, "word"
            await self.open_selection(n, n)

    async def on_word_card(self, e) -> None:
        """Right-click on a page: open the word card for the word there."""
        if self.tool:
            return
        i = e.control.data
        n = self._word_near(i, e.local_position.x, e.local_position.y) if e.local_position else None
        if n is not None:
            await self.open_card(i, n)

    def _exact(self, a: int, b: int) -> Optional[int]:
        """The highlight covering exactly words a..b, if there is one."""
        for k, h in enumerate(self.highlights):
            if hl.resolve(h, self.words) == (a, b):
                return k
        return None

    def _target(self, n: int) -> tuple[int, int, Optional[int]]:
        """What the colour and note buttons act on for a single word: the highlight it is in, or the word."""
        k = hl.at(self.highlights, n, self.words)
        if k is not None:
            a, b = hl.resolve(self.highlights[k], self.words)
            return a, b, k
        return n, n, None

    # ------------------------------------------------------------------ cards: word, selection, note
    def _show_card(self, content: ft.Control, mode: str) -> None:
        """Show a card (word, selection, note editor or note) at the bottom of the view."""
        self.card_mode = mode
        self.card_layer.content = content
        self.card_layer.visible = True
        self.app.page.update()

    async def open_card(self, page: int, n: int, edit_note: bool = False) -> None:
        """Show the word card for word ``n`` on ``page`` (looked up in the dictionary; ``edit_note`` goes
        straight to the note of the highlight the word is in)."""
        app = self.app
        self._anchor = n
        self.sel_unit = "word"
        if edit_note:
            a, b, k = self._target(n)
            await self.open_note(a, b)
            return
        old = self._marked_pages()
        self.sel, self.card_word = None, (page, n)
        language = app.session.document.language if app.session else "en"
        entry = await app.in_thread(dictionary.lookup, self.words[n][1], language)
        self._show_card(self._word_card(n, entry, language), "word")
        self._paint_selection(old | {page})

    async def open_selection(self, a: int, b: int) -> None:
        """Show the card for the words a..b (selected by dragging, by sentence or paragraph, or from the notes
        list)."""
        old = self._marked_pages()
        self.card_word, self.card_mode, self.sel = None, "selection", (a, b)
        self._paint_selection(old | self._pages_of(self.sel))
        self._show_card(self._selection_card(a, b), "selection")

    async def close_card(self, e=None) -> None:
        """Close the card and take the outline or selection off the page."""
        self._typing = False
        self.card_layer.visible = False
        self.card_layer.content = None
        self.card_mode = None
        pages = self._marked_pages()
        self.sel, self.card_word = None, None
        self._paint_selection(pages)
        self.app.page.update()

    def _card_box(self, rows: list[ft.Control], bgcolor=None) -> ft.Control:
        """A card of these rows, as wide as fits (at most 480 pixels)."""
        width = min(480.0, self._avail()[0] - 24)
        return ft.Card(content=ft.Container(ft.Column(rows, spacing=6, tight=True), padding=16, width=width,
                                            bgcolor=bgcolor, border_radius=12), elevation=8)

    def _unit_row(self) -> ft.Control:
        """Select: Word / Sentence / Paragraph - grow the selection from the word held to a whole unit."""
        t = self.app.t
        return ft.Row([self.app.text(t("Select"), 13), ft.SegmentedButton(
            segments=[ft.Segment("word", label=ft.Text(t("Word"))),
                      ft.Segment("sentence", label=ft.Text(t("Sentence"))),
                      ft.Segment("paragraph", label=ft.Text(t("Paragraph")))],
            selected=[self.sel_unit] if self.sel_unit else [], allow_empty_selection=True,
            on_change=self.on_unit)], spacing=10)

    async def on_unit(self, e) -> None:
        """Word / Sentence / Paragraph: select that unit around the word first held."""
        unit = (list(e.control.selected) or ["word"])[0]
        n = self._anchor
        if unit == "word":
            self.sel_unit = "word"
            await self.open_card(self.words[n][0], n)
            return
        spans = self._sentences if unit == "sentence" else self._paragraphs
        a, b = hl.span_at(spans, n)
        self.sel_unit = unit
        await self.open_selection(a, b)

    def _mark_rows(self, a: int, b: int, k: Optional[int]) -> list[ft.Control]:
        """Highlight colours, Add/Edit note and Remove for words a..b (``k``: their highlight, if any)."""
        app, t = self.app, self.app.t
        h = self.highlights[k] if k is not None else None
        dots = [ft.Container(width=28, height=28, border_radius=14, bgcolor=SWATCHES[name], data=name,
                             tooltip=t(name.capitalize()),
                             border=ft.Border.all(3, ft.Colors.PRIMARY) if h and h.colour == name else None,
                             on_click=lambda e: app.page.run_task(self.mark, a, b, e.control.data))
                for name in SWATCHES]
        note_btn = ft.FilledButton(t("Edit note") if h and h.note else t("Add note"),
                                   icon=ft.Icons.STICKY_NOTE_2_OUTLINED,
                                   on_click=lambda e: app.page.run_task(self.open_note, a, b))
        rows = [ft.Divider(height=8),
                ft.Row([app.text(t("Highlight"), 13), *dots, ft.Container(expand=True), note_btn], spacing=8)]
        if h is not None:
            rows.append(ft.Row([ft.TextButton(t("Remove highlight"), icon=ft.Icons.DELETE_OUTLINE,
                                              on_click=lambda e: app.page.run_task(self.unmark, a, b))]))
        return rows

    def _word_card(self, n: int, entry, language: str) -> ft.Control:
        """The word card: the word and its base form, syllables, say button, meanings, online look-up, Select
        (word, sentence, paragraph), and highlight and note."""
        app, t = self.app, self.app.t
        title = entry.word if not entry.base or entry.base.lower() == entry.word.lower() else \
            f"{entry.word}  →  {entry.base}"
        say = ft.IconButton(ft.Icons.VOLUME_UP, tooltip=t("Say the word"), visible=app._speech_allowed(),
                            on_click=lambda e: app.say_word(entry.word))
        rows: list[ft.Control] = [
            ft.Row([ft.Text(title, size=app.fs(22), weight=ft.FontWeight.BOLD, expand=True, selectable=True),
                    say, ft.IconButton(ft.Icons.CLOSE, tooltip=t("Close"), on_click=self.close_card)]),
            ft.Text("  •  ".join(entry.syllables), size=app.fs(18), color=ft.Colors.PRIMARY),
        ]
        if entry.senses:
            rows.append(ft.Divider(height=8))
            last_pos, number = "", 0
            for sense in entry.senses[:4]:
                if sense.pos != last_pos:
                    rows.append(ft.Text(t(sense.pos), size=app.fs(12), italic=True,
                                        color=ft.Colors.ON_SURFACE_VARIANT))
                    last_pos, number = sense.pos, 0
                number += 1
                rows.append(ft.Text(f"{number}. {sense.meaning}", size=app.fs(15), selectable=True))
                if sense.example:
                    rows.append(ft.Text(f"“{sense.example}”", size=app.fs(13), italic=True,
                                        color=ft.Colors.ON_SURFACE_VARIANT))
            rows.append(ft.Text(t("{source} - on this device", source=entry.source), size=app.fs(11),
                                color=ft.Colors.ON_SURFACE_VARIANT))
        elif entry.word:
            msg = t("This word is not in the dictionary on this device.") if language == "en" else \
                t("There is no dictionary on this device for {language} yet.", language=app.lang_name(language))
            rows.append(ft.Text(msg, size=app.fs(13), color=ft.Colors.ON_SURFACE_VARIANT))
        if entry.word:
            rows.append(ft.Row([ft.TextButton(t("Look up online"), icon=ft.Icons.OPEN_IN_NEW,
                                              url=dictionary.online_url(entry.word, language),
                                              tooltip=t("Opens Wiktionary in your browser"))]))
        rows.append(self._unit_row())
        a, b, k = self._target(n)
        return self._card_box(rows + self._mark_rows(a, b, k))

    def _selection_card(self, a: int, b: int) -> ft.Control:
        """The toolbar for selected words (or a highlight): Copy, the colours, Note, Read, Meaning (one word),
        Remove (a highlight), More (select sentence or paragraph, move the start or end) and Close. Slim, at
        the bottom, so the text stays in view."""
        app, t = self.app, self.app.t
        k = self._exact(a, b)
        h = self.highlights[k] if k is not None else None
        text = hl.text_of(self.words, a, b)

        def btn(icon, label, handler, visible=True, tip=None):
            """A compact text button with an icon for the toolbar."""
            return ft.TextButton(label, icon=icon, on_click=handler, visible=visible, tooltip=tip,
                                 style=ft.ButtonStyle(padding=ft.Padding.symmetric(horizontal=8)))

        dots = [ft.Container(width=26, height=26, border_radius=13, bgcolor=SWATCHES[name], data=name,
                             tooltip=f"{t(name.capitalize())} ({n})",
                             border=ft.Border.all(3, ft.Colors.PRIMARY) if h and h.colour == name else None,
                             on_click=lambda e: app.page.run_task(self.mark, a, b, e.control.data))
                for n, name in enumerate(SWATCHES, 1)]
        label = t("Highlight") if h else (t("1 word") if a == b else t("{n} words", n=b - a + 1))
        bar = ft.Container(ft.Row([
            app.text(label, 13, weight=ft.FontWeight.BOLD),
            btn(ft.Icons.CONTENT_COPY, t("Copy"), lambda e: app.page.run_task(self.copy, a, b), tip="Ctrl+C"),
            *dots,
            btn(ft.Icons.STICKY_NOTE_2_OUTLINED, t("Note"), lambda e: app.page.run_task(self.open_note, a, b),
                tip=t("Add or edit a note (N)")),
            btn(ft.Icons.VOLUME_UP, t("Read"), lambda e: app.say_word(text), visible=app._speech_allowed()),
            btn(ft.Icons.SMART_TOY_OUTLINED, t("Summarise"), lambda e: app.page.run_task(self.summarise_selection, a, b),
                visible=self._ai_on() and b - a >= 15, tip=t("AI summary of the selection")),
            btn(ft.Icons.MENU_BOOK_OUTLINED, t("Meaning"), lambda e: app.page.run_task(
                self.open_card, self.words[a][0], a), visible=a == b),
            btn(ft.Icons.DELETE_OUTLINE, t("Remove"), lambda e: app.page.run_task(self.unmark, a, b),
                visible=h is not None, tip=t("Remove the highlight (Delete)")),
            ft.IconButton(ft.Icons.MORE_HORIZ, tooltip=t("More: select the sentence or paragraph, adjust"),
                          on_click=self.on_more, selected=self._more, style=self._toggle_style()),
            ft.IconButton(ft.Icons.CLOSE, tooltip=t("Close (Esc)"), on_click=self.close_card),
        ], spacing=4, tight=True, wrap=True, alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH, border_radius=28,
            padding=ft.Padding.symmetric(horizontal=14, vertical=4),
            shadow=ft.BoxShadow(blur_radius=12, color="#40000000"))
        parts: list[ft.Control] = []
        if self._more:
            nudge = lambda icon, tip, end, step: ft.IconButton(  # noqa: E731
                icon, tooltip=tip, on_click=lambda e: app.page.run_task(self.nudge, end, step))
            parts.append(ft.Container(ft.Column([
                self._unit_row(),
                ft.Row([app.text(t("Start"), 13),
                        nudge(ft.Icons.CHEVRON_LEFT, t("One word earlier"), 0, -1),
                        nudge(ft.Icons.CHEVRON_RIGHT, t("One word later"), 0, 1), ft.Container(width=12),
                        app.text(t("End"), 13),
                        nudge(ft.Icons.CHEVRON_LEFT, t("One word earlier"), 1, -1),
                        nudge(ft.Icons.CHEVRON_RIGHT, t("One word later"), 1, 1)], spacing=0),
            ], spacing=4, tight=True), bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH, border_radius=16, padding=12,
                shadow=ft.BoxShadow(blur_radius=12, color="#40000000")))
        parts.append(bar)
        return ft.Column(parts, spacing=8, tight=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    async def on_more(self, e) -> None:
        """•••: show or hide Select (word, sentence, paragraph) and moving the start and end."""
        self._more = not self._more
        if self.sel:
            await self.open_selection(*self.sel)

    async def copy(self, a: int, b: int) -> None:
        """Copy words a..b to the clipboard."""
        await self.app.clipboard.set(hl.text_of(self.words, a, b))
        self._toast(self.app.t("Copied."))

    async def nudge(self, end: int, step: int) -> None:
        """Move the start (``end`` 0) or the end (1) of the selection by one word."""
        if not self.sel:
            return
        a, b = self.sel
        if end == 0:
            a = max(0, min(b, a + step))
        else:
            b = min(len(self.words) - 1, max(a, b + step))
        self.sel_unit = None
        await self.open_selection(a, b)

    async def open_note(self, a: int, b: int) -> None:
        """The note editor for words a..b: the words quoted, colour, the note (typed or dictated), Save."""
        app, t = self.app, self.app.t
        k = self._exact(a, b)
        h = self.highlights[k] if k is not None else None
        chosen = {"colour": h.colour if h else self.colour}
        if self.sel != (a, b):
            await self._show_selection((a, b))
        bar = ft.Container(ft.Text(f"“{hl.text_of(self.words, a, b)}”", size=app.fs(13), italic=True,
                                   max_lines=6, overflow=ft.TextOverflow.ELLIPSIS),
                           border=ft.Border.only(left=ft.BorderSide(4, SWATCHES[chosen["colour"]])),
                           padding=ft.Padding.only(left=10, top=2, bottom=2))
        dots: list[ft.Container] = []

        def pick(e):
            """A colour dot: use it for the highlight (shown on the quote's bar and the dots)."""
            chosen["colour"] = e.control.data
            bar.border = ft.Border.only(left=ft.BorderSide(4, SWATCHES[chosen["colour"]]))
            for d in dots:
                d.border = ft.Border.all(3, ft.Colors.PRIMARY) if d.data == chosen["colour"] else None
            app.page.update()

        dots += [ft.Container(width=24, height=24, border_radius=12, bgcolor=SWATCHES[name], data=name,
                              tooltip=t(name.capitalize()), on_click=pick,
                              border=ft.Border.all(3, ft.Colors.PRIMARY) if name == chosen["colour"] else None)
                 for name in SWATCHES]
        width = min(480.0, self._avail()[0] - 24)
        field = ft.TextField(value=h.note if h else "", multiline=True, min_lines=3, max_lines=8, width=width - 32,
                             label=t("Your note"), text_size=app.fs(14), autofocus=True,
                             on_focus=lambda e: setattr(self, "_typing", True),
                             on_blur=lambda e: setattr(self, "_typing", False))
        dictate = sys.platform == "win32" and not app.page.web
        rows = [
            ft.Row([ft.Icon(ft.Icons.STICKY_NOTE_2_OUTLINED, color=ft.Colors.PRIMARY),
                    ft.Text(t("Note"), size=app.fs(16), weight=ft.FontWeight.BOLD), ft.Container(expand=True),
                    *dots, ft.IconButton(ft.Icons.CLOSE, tooltip=t("Close"), on_click=self.close_card)]),
            bar, field,
            ft.Row([ft.IconButton(ft.Icons.MIC_NONE, tooltip=t("Speak your note (Windows voice typing)"),
                                  visible=dictate, on_click=lambda e: app.page.run_task(self._dictate, field)),
                    app.text(t("Tip: press the microphone to speak your note"), 11, visible=dictate,
                             color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.Container(expand=True),
                    ft.FilledButton(t("Save note"), on_click=lambda e: app.page.run_task(
                        self.save_note, a, b, field.value or "", chosen["colour"]))]),
        ]
        self._show_card(self._card_box(rows), "note")

    async def _dictate(self, field: ft.TextField) -> None:
        """Start Windows voice typing (Win + H) in the note field: what is said is typed into it."""
        try:
            await field.focus()
            await asyncio.sleep(0.2)
            import ctypes

            press = ctypes.windll.user32.keybd_event  # type: ignore[attr-defined]
            press(0x5B, 0, 0, 0)  # Windows key down
            press(0x48, 0, 0, 0)  # H
            press(0x48, 0, 2, 0)
            press(0x5B, 0, 2, 0)  # Windows key up
        except Exception:
            self.app.notify(self.app.t("Voice typing could not be started. Press Windows + H to start it."))

    async def open_bubble(self, k: int) -> None:
        """The note of highlight ``k``, shown on a yellow note card with Edit and Read aloud."""
        app, t = self.app, self.app.t
        h = self.highlights[k]
        a, b = hl.resolve(h, self.words)
        rows = [
            ft.Row([ft.Icon(ft.Icons.STICKY_NOTE_2, color="#B8860B"), ft.Container(expand=True),
                    ft.IconButton(ft.Icons.CLOSE, tooltip=t("Close"), on_click=self.close_card,
                                  icon_color="#5A4A1A")]),
            ft.Text(h.note, size=app.fs(15), selectable=True, color="#2A2410"),
            ft.Row([ft.TextButton(t("Edit"), icon=ft.Icons.EDIT_OUTLINED,
                                  on_click=lambda e: app.page.run_task(self.open_note, a, b)),
                    ft.TextButton(t("Read aloud"), icon=ft.Icons.VOLUME_UP, visible=app._speech_allowed(),
                                  on_click=lambda e: app.say_word(h.note))], spacing=0),
        ]
        await self._show_selection((a, b))
        self._show_card(self._card_box(rows, bgcolor="#FFF6D5"), "bubble")

    async def _changed(self) -> None:
        """Highlights changed: save them, refresh the Export menu option and the notes list."""
        if self.app.doc_key:
            self.app.hl_store.save(self.app.doc_key, self.highlights)
        self.app.update_highlight_option()
        self._refresh_notes()

    async def mark(self, a: int, b: int, colour: str) -> None:
        """A colour: highlight words a..b (or recolour their highlight), close the toolbar, and offer Undo."""
        before = list(self.highlights)
        k = self._exact(a, b)
        if k is None:
            self.highlights = hl.add(self.highlights, a, b, colour, self.words)
        else:
            self.highlights = hl.recolour(self.highlights, k, colour)
        self.colour = colour
        await self._changed()
        await self.close_card()
        self._offer_undo(self.app.t("Highlighted in {colour}", colour=self.app.t(colour.capitalize()).lower()), before)

    def _offer_undo(self, message: str, before: list) -> None:
        """A short message with Undo, which puts the highlights back as they were."""

        async def undo(e):
            """Put the highlights back as they were before the change."""
            pages = self._pages_of(self.sel)
            self.highlights = before
            await self._changed()
            for p in sorted(pages | {w[0] for h in before for w in self.words[h.start:h.end + 1][:1]}
                            | {self.current}):
                await self.redraw(p)

        self._toast(message, undo)

    def _toast(self, message: str, undo=None) -> None:
        """A short message floating above the toolbar's place (so the toolbar stays usable), with Undo when
        ``undo`` is given."""
        app = self.app
        app.page.show_dialog(ft.SnackBar(ft.Text(message, size=app.fs(14)), action=app.t("Undo") if undo else None,
                                         on_action=undo, duration=ft.Duration(seconds=6 if undo else 2),
                                         behavior=ft.SnackBarBehavior.FLOATING,
                                         margin=ft.Margin.only(left=24, right=24, bottom=96)))

    async def save_note(self, a: int, b: int, note: str, colour: str) -> None:
        """Save the note on words a..b (they are highlighted in ``colour`` when they were not yet)."""
        k = self._exact(a, b)
        if k is None:
            self.highlights = hl.add(self.highlights, a, b, colour, self.words, note.strip())
        else:
            self.highlights = hl.recolour(hl.set_note(self.highlights, k, note), k, colour)
        self._typing = False
        await self._changed()
        await self.close_card()

    async def unmark(self, a: int, b: int) -> None:
        """Remove the highlight on words a..b (with its note), with Undo."""
        before = list(self.highlights)
        self.highlights = hl.erase(self.highlights, a, b, self.words)
        await self._changed()
        await self.close_card()
        self._offer_undo(self.app.t("Highlight removed"), before)

    # ------------------------------------------------------------------ AI summary (only when AI is on)
    def _ai_on(self) -> bool:
        """Whether AI summaries can be made: AI-assisted mode, the privacy notice accepted, and a key."""
        s = self.app.ai_settings
        return s.mode == "ai_assisted" and s.consent_given and self.app.assistant.has_key

    def _ai_button(self) -> ft.IconButton:
        """The robot button (the icon of the AI settings tab): the summary panel, or greyed out while AI is off."""
        t = self.app.t
        on = self._ai_on()
        self.ai_toggle = ft.IconButton(ft.Icons.SMART_TOY_OUTLINED, on_click=self.on_ai_button,
                                       tooltip=t("AI summary") if on else t("AI summary (AI is off)"),
                                       icon_color=None if on else "#9E9E9E", style=self._toggle_style())
        return self.ai_toggle

    async def on_ai_button(self, e) -> None:
        """The robot button: open or close the summary panel, or explain how to switch AI on."""
        if not self._ai_on():
            self._ai_off_dialog()
            return
        if self.sel:
            self._last_sel = self.sel
        self._open_side("ai" if self._side_mode != "ai" else None)

    def _ai_off_dialog(self) -> None:
        """AI is off: say what AI summaries need, with a way to the AI settings."""
        app, t = self.app, self.app.t

        async def open_settings(e):
            """Leave focus mode and show the AI settings tab."""
            app.page.pop_dialog()
            await self.close()
            app.tabs.selected_index = app.ai_tab_index
            app.page.update()

        app.page.show_dialog(ft.AlertDialog(
            title=ft.Row([ft.Icon(ft.Icons.SMART_TOY_OUTLINED, color="#9E9E9E"),
                          ft.Text(t("AI summaries are off"), size=app.fs(18))], spacing=10),
            content=ft.Text(t("To get a summary of a page, section or selection, switch on AI-assisted mode in AI "
                              "settings. Nothing is sent to an AI provider until you do."), size=app.fs(14),
                            width=380),
            actions=[ft.TextButton(t("Not now"), on_click=lambda e: app.page.pop_dialog()),
                     ft.FilledButton(t("Open AI settings"), icon=ft.Icons.SETTINGS, on_click=open_settings)]))

    def _heading_starts(self) -> list[int]:
        """The first word of every heading in the converted document (from its bookmarks), for "this section"."""
        import pymupdf

        try:
            with pymupdf.open(stream=self.app.converted_pdf, filetype="pdf") as d:
                toc = d.get_toc()
        except Exception:
            return []
        starts = []
        for _, title, page in toc:
            target = [w.lower() for w in title.split()[:3]]
            if not target:
                continue
            for n, (p, text, _) in enumerate(self.words):
                if p == page - 1 and [x[1].lower() for x in self.words[n:n + len(target)]] == target:
                    starts.append(n)
                    break
        return sorted(set(starts))

    def _scope_span(self, scope: str) -> Optional[tuple[int, int]]:
        """The words the summary is of: the current page, the section around it, the selection, or everything."""
        if not self.words:
            return None
        on_page = [n for n, w in enumerate(self.words) if w[0] == self.current]
        if scope == "document":
            return 0, len(self.words) - 1
        if scope == "selection":
            return self.sel or self._last_sel
        if scope == "section":
            here = on_page[0] if on_page else 0
            start = max([s for s in self._toc_starts if s <= here], default=0)
            end = min([s for s in self._toc_starts if s > here], default=len(self.words)) - 1
            return start, end
        return (on_page[0], on_page[-1]) if on_page else None

    def _ai_panel(self) -> ft.Control:
        """The summary panel: what to summarise, length, plain language, what will be sent, and the summary."""
        app, t = self.app, self.app.t
        ui = app.ui
        chips = [ft.Chip(label=ft.Text(t(label)), data=key, selected=self._ai_scope == key,
                         on_select=self.on_ai_scope,
                         disabled=key == "selection" and not (self.sel or self._last_sel))
                 for key, label in (("page", "This page"), ("section", "This section"),
                                    ("selection", "Selection"), ("document", "Whole document"))]
        rows: list[ft.Control] = [
            ft.Row([ft.Icon(ft.Icons.SMART_TOY_OUTLINED, color=ft.Colors.PRIMARY),
                    ft.Text(t("AI summary"), size=app.fs(16), weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(ft.Icons.CLOSE, tooltip=t("Close"), on_click=lambda e: self._open_side(None))]),
            app.text(t("Summarise"), 12, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Row(chips, wrap=True, spacing=6),
            ft.Row([app.text(t("Length"), 12, color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.SegmentedButton(segments=[ft.Segment("short", label=ft.Text(t("Short"))),
                                                 ft.Segment("detailed", label=ft.Text(t("Detailed")))],
                                       selected=["detailed" if ui.get("ai_summary_detailed") else "short"],
                                       on_change=self.on_ai_length)], spacing=10),
            ft.Switch(label=t("Plain language (short sentences, easy words)"),
                      value=bool(ui.get("ai_summary_plain", True)), on_change=self.on_ai_plain,
                      label_text_style=ft.TextStyle(size=app.fs(13))),
        ]
        span = self._scope_span(self._ai_scope)
        words = (span[1] - span[0] + 1) if span else 0
        provider = PROVIDERS.get(app.ai_settings.provider)
        where = f"{provider.label if provider else app.ai_settings.provider}"
        model = app.ai_settings.model or (provider.default_model if provider else "")
        rows.append(ft.Container(ft.Row([
            ft.Icon(ft.Icons.CLOUD_UPLOAD_OUTLINED, size=18, color="#8A5A00"),
            ft.Text(t("About {n} words will be sent to {provider} ({model}). Every request is recorded in the "
                      "privacy log.", n=words, provider=where, model=model), size=app.fs(12), expand=True,
                    color="#4A3A10")], vertical_alignment=ft.CrossAxisAlignment.START),
            bgcolor="#FFF3D6", border_radius=8, padding=10))
        busy = ft.Row([ft.ProgressRing(width=18, height=18, stroke_width=2), app.text(t("Summarising..."), 13)],
                      visible=self._ai_busy)
        rows += [ft.FilledButton(t("Summarise"), icon=ft.Icons.SMART_TOY_OUTLINED, on_click=self.run_summary,
                                 disabled=self._ai_busy or not words), busy]
        if self._ai_error:
            rows.append(ft.Text(self._ai_error, size=app.fs(13), color=ft.Colors.ERROR))
        if self._ai_result:
            summary, a, b = self._ai_result
            rows += [ft.Divider(height=10), self._ai_warning()]
            if summary.title:
                rows.append(ft.Text(summary.title, size=app.fs(15), weight=ft.FontWeight.BOLD, selectable=True))
            rows += [ft.Row([ft.Text("•", size=app.fs(15)), ft.Text(p, size=app.fs(14), expand=True,
                                                                        selectable=True)],
                            vertical_alignment=ft.CrossAxisAlignment.START) for p in summary.points]
            text = self._summary_text(summary)
            rows.append(ft.Row([
                ft.TextButton(t("Copy"), icon=ft.Icons.CONTENT_COPY,
                              on_click=lambda e: app.page.run_task(self._copy_text, text)),
                ft.TextButton(t("Read aloud"), icon=ft.Icons.VOLUME_UP, visible=app._speech_allowed(),
                              on_click=lambda e: app.say_word(text)),
                ft.TextButton(t("Save as note"), icon=ft.Icons.STICKY_NOTE_2_OUTLINED,
                              on_click=lambda e: app.page.run_task(self.save_summary_note))], spacing=0, wrap=True))
        return ft.Column(rows, spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

    def _ai_warning(self) -> ft.Control:
        """The notice on every summary that AI can make mistakes: amber card with an accent bar and an icon."""
        app, t = self.app, self.app.t
        return ft.Container(ft.Row([
            ft.Container(width=4, height=40, bgcolor="#E0A100", border_radius=2),
            ft.Icon(ft.Icons.WARNING_AMBER_ROUNDED, color="#B77900", size=22),
            ft.Column([ft.Text(t("Made by AI"), size=app.fs(13), weight=ft.FontWeight.BOLD, color="#5C4200"),
                       ft.Text(t("AI can make mistakes. Check the summary against the text before you use it."),
                               size=app.fs(12), color="#5C4200")], spacing=2, tight=True, expand=True),
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor="#FFF4D6", border=ft.Border.all(1, "#F1D48A"), border_radius=10,
            padding=ft.Padding.only(left=0, right=12, top=10, bottom=10), clip_behavior=ft.ClipBehavior.HARD_EDGE)

    @staticmethod
    def _summary_text(summary) -> str:
        """A summary as plain text (title, then one point per line)."""
        lines = [summary.title] if summary.title else []
        return "\n".join(lines + [f"- {p}" for p in summary.points])

    def on_ai_scope(self, e) -> None:
        """A scope chip: summarise this page, this section, the selection or the whole document."""
        self._ai_scope = e.control.data
        self._open_side("ai")

    def on_ai_length(self, e) -> None:
        """Short or Detailed (remembered)."""
        self._save("ai_summary_detailed", "detailed" in (e.control.selected or []))

    def on_ai_plain(self, e) -> None:
        """Plain language on or off (remembered)."""
        self._save("ai_summary_plain", bool(e.control.value))

    async def summarise_selection(self, a: int, b: int) -> None:
        """"Summarise" on the selection toolbar: open the summary panel for the selection."""
        self._last_sel = (a, b)
        self._ai_scope = "selection"
        await self.close_card()
        self._open_side("ai")

    async def run_summary(self, e=None) -> None:
        """Send the chosen text for a summary (in a thread) and show it."""
        from ..ai.assistant import ConsentRequired
        from ..ai.providers import AIError

        app, t = self.app, self.app.t
        span = self._scope_span(self._ai_scope)
        if not span:
            return
        a, b = span
        language = app.session.document.language if app.session else "en"
        self._ai_busy, self._ai_error = True, ""
        self._open_side("ai")
        try:
            summary = await app.in_thread(app.assistant.summarise, hl.text_of(self.words, a, b), language,
                                          bool(app.ui.get("ai_summary_detailed")),
                                          bool(app.ui.get("ai_summary_plain", True)))
            self._ai_result = (summary, a, b)
        except ConsentRequired:
            self._ai_error = t("AI is off. Choose 'AI-assisted' in AI settings to use it.")
        except AIError as ex:
            self._ai_error = t.message(str(ex))
        except Exception as ex:  # a network problem: say so, the document is unchanged
            self._ai_error = t("The summary could not be made:") + " " + type(ex).__name__
        finally:
            self._ai_busy = False
        if self._side_mode == "ai":
            self._open_side("ai")
        app.refresh_ai_log()

    async def _copy_text(self, text: str) -> None:
        """Copy some text (the summary) to the clipboard."""
        await self.app.clipboard.set(text)
        self._toast(self.app.t("Copied."))

    async def save_summary_note(self) -> None:
        """Keep the summary as a note on the first sentence of the part summarised (it shows in the notes list)."""
        if not self._ai_result:
            return
        summary, a, _ = self._ai_result
        s0, s1 = hl.span_at(self._sentences, a)
        note = self.app.t("AI summary (check it against the text):") + "\n" + self._summary_text(summary)
        k = self._exact(s0, s1)
        if k is None:
            self.highlights = hl.add(self.highlights, s0, s1, "blue", self.words, note)
        else:
            self.highlights = hl.set_note(self.highlights, k, note)
        await self._changed()
        for p in self._pages_of((s0, s1)):
            await self.redraw(p)
        self._toast(self.app.t("Saved as a note."))

    # ------------------------------------------------------------------ notes and highlights panel
    def on_notes_panel(self, e) -> None:
        """The notes button: show or hide the list of highlights and notes beside the pages."""
        self._open_side("notes" if self._side_mode != "notes" else None)

    @property
    def _side_mode(self) -> Optional[str]:
        """What the side panel shows now: "notes", "ai", or None when it is folded away."""
        return self.side.data if self.side.content is not None else None

    def _open_side(self, mode: Optional[str]) -> None:
        """Show the notes list or the AI summary beside the pages (or neither)."""
        self.notes_toggle.selected = mode == "notes"
        self.ai_toggle.selected = mode == "ai"
        self.side.data = mode
        self.side.width = min(380.0, max(260.0, self._avail()[0] * 0.35)) if mode else 0
        self.side.content = (self._notes_panel() if mode == "notes" else self._ai_panel()) if mode else None
        self.side.padding = 12 if mode else 0
        self.app.page.update()
        if mode == "notes":
            self._refresh_notes()

    def _notes_panel(self) -> ft.Control:
        """The panel: filters (all / with notes / colour), the list, and export."""
        app, t = self.app, self.app.t
        self.notes_list = ft.ListView(spacing=8, expand=True)
        self.filter_notes = ft.Chip(label=ft.Text(t("With notes")), selected=self._notes_only,
                                    on_select=self.on_notes_filter)
        colour_dots = [ft.Container(width=18, height=18, border_radius=9, bgcolor=SWATCHES[name], data=name,
                                    tooltip=t(name.capitalize()), on_click=self.on_colour_filter,
                                    border=ft.Border.all(3, ft.Colors.PRIMARY) if name in self._colour_filter
                                    else None)
                       for name in SWATCHES]
        return ft.Column([
            ft.Row([ft.Text(t("Notes and highlights"), size=app.fs(16), weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(ft.Icons.CLOSE, tooltip=t("Close"), on_click=self.on_notes_panel)]),
            ft.Row([self.filter_notes, *colour_dots], spacing=6, wrap=True),
            self.notes_list,
            ft.OutlinedButton(t("Export notes as a list"), icon=ft.Icons.DOWNLOAD, on_click=self.on_export_notes,
                              tooltip=t("Save your highlights and notes as a Word document")),
        ], spacing=10, expand=True)

    def _note_entries(self) -> list[tuple[int, int, int, hl.Highlight]]:
        """(first word, last word, page, highlight) of every highlight that can be placed, in reading order."""
        out = []
        for h in self.highlights:
            where = hl.resolve(h, self.words)
            if where:
                out.append((where[0], where[1], self.words[where[0]][0], h))
        return sorted(out, key=lambda x: x[0])

    def _refresh_notes(self) -> None:
        """Fill the notes list with the highlights that pass the filters."""
        if self._side_mode != "notes":
            return
        app, t = self.app, self.app.t
        items = []
        for a, b, page, h in self._note_entries():
            if (self._notes_only and not h.note) or (self._colour_filter and h.colour not in self._colour_filter):
                continue
            quote = hl.text_of(self.words, a, b)
            body = [ft.Row([ft.Container(width=10, height=10, border_radius=5, bgcolor=SWATCHES.get(h.colour)),
                            app.text(t("Page {n}", n=page + 1), 11, color=ft.Colors.ON_SURFACE_VARIANT)],
                           spacing=6),
                    ft.Text(f"“{quote}”", size=app.fs(12), italic=True, max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS)]
            if h.note:
                body.append(ft.Text(h.note, size=app.fs(13)))
            items.append(ft.Container(ft.Column(body, spacing=3, tight=True), padding=10, border_radius=8,
                                      bgcolor=ft.Colors.SURFACE_CONTAINER_LOW, data=(a, b, page),
                                      on_click=self.on_note_entry, ink=True))
        if not items:
            items = [app.text(t("Nothing highlighted yet. Hold a word and drag to select text."), 13,
                              color=ft.Colors.ON_SURFACE_VARIANT)]
        self.notes_list.controls = items
        self.app.page.update()

    def on_notes_filter(self, e) -> None:
        """"With notes": show only highlights that have a note."""
        self._notes_only = bool(e.control.selected)
        self._refresh_notes()

    def on_colour_filter(self, e) -> None:
        """A colour dot: show only highlights in the chosen colour(s) (tap again to show all)."""
        name = e.control.data
        self._colour_filter ^= {name}
        e.control.border = ft.Border.all(3, ft.Colors.PRIMARY) if name in self._colour_filter else None
        self._refresh_notes()

    async def on_note_entry(self, e) -> None:
        """An entry in the list: go to its page and open its card."""
        a, b, page = e.control.data
        rects = self.words[a][2]
        await self.scroll_to(page, within=rects[0][1] if rects else 0.0)
        await self.open_selection(a, b)

    async def on_export_notes(self, e) -> None:
        """Save the highlights and notes (with the filters applied) as a Word document."""
        app, t = self.app, self.app.t
        entries = [(page + 1, h.colour, hl.text_of(self.words, a, b), h.note)
                   for a, b, page, h in self._note_entries()
                   if not (self._notes_only and not h.note)
                   and not (self._colour_filter and h.colour not in self._colour_filter)]
        if not entries:
            app.notify(t("Nothing highlighted yet. Hold a word and drag to select text."))
            return
        stem = Path(app.source_path).stem if app.source_path else "document"
        data = await app.in_thread(hl.notes_docx, t("Notes on {name}", name=stem), entries)
        await app.save_bytes(data, f"{stem}_notes.docx", "docx")

    # ------------------------------------------------------------------ highlighter
    def _toggle_style(self) -> ft.ButtonStyle:
        """Buttons that stay pressed while their panel or tool is on get a tinted background."""
        return ft.ButtonStyle(bgcolor={ft.ControlState.SELECTED: ft.Colors.PRIMARY_CONTAINER})

    def _swatch(self, name: str) -> ft.Control:
        """A round colour button for the highlighter."""
        chosen = name == self.colour
        return ft.Container(width=28, height=28, border_radius=14, bgcolor=SWATCHES[name], data=name,
                            border=ft.Border.all(3 if chosen else 1,
                                                 ft.Colors.PRIMARY if chosen else ft.Colors.OUTLINE),
                            on_click=self.on_colour, tooltip=self.app.t(name.capitalize()))

    def _refresh_swatches(self) -> None:
        """Show which highlighter colour or the eraser is chosen; the colours show only while a tool is on."""
        for c in self.swatches.controls:
            if isinstance(c, ft.Container):
                chosen = self.tool == "mark" and c.data == self.colour
                c.border = ft.Border.all(3 if chosen else 1, ft.Colors.PRIMARY if chosen else ft.Colors.OUTLINE)
            else:
                c.selected = self.tool == "erase"
        self.mark_toggle.selected = self.tool is not None
        self.swatches.visible = self.tool is not None

    def _set_tool_gestures(self) -> None:
        """Dragging marks text while the highlighter is on; otherwise it scrolls the pages, two fingers
        zoom, and page by page a swipe turns the page."""
        on = self.tool is not None
        for det in self.detectors:
            det.on_pan_start = self.on_pan_start if on else None
            det.on_pan_update = self.on_pan_update if on else None
            det.on_pan_end = self.on_pan_end if on else None
            det.on_scale_start = None if on else self.on_scale_start
            det.on_scale_update = None if on else self.on_scale_update
            det.on_scale_end = None if on else self.on_scale_end
            det.mouse_cursor = ft.MouseCursor.TEXT if on else ft.MouseCursor.CLICK

    def on_marker(self, e) -> None:
        """The highlighter button: switch the highlighter on or off."""
        self.tool = None if self.tool else "mark"
        self._refresh_swatches()
        self._set_tool_gestures()
        self.app.page.update()

    def on_colour(self, e) -> None:
        """A highlighter colour: choose it (and switch the highlighter on)."""
        self.colour = e.control.data
        self.tool = "mark"
        self.app.ui["focus_colour"] = self.colour
        self.app.store.save_ui(self.app.ui)
        self._refresh_swatches()
        self.app.page.update()

    def on_eraser(self, e) -> None:
        """The eraser: switch it on or off."""
        self.tool = None if self.tool == "erase" else "erase"
        self._refresh_swatches()
        self._set_tool_gestures()
        self.app.page.update()

    def on_pan_start(self, e) -> None:
        """Start of a drag with the highlighter or eraser: remember the first word."""
        i = e.control.data
        pt = self._point(i, e.local_position.x, e.local_position.y)
        n = hl.word_at(hl.words_on_page(self.words, i), *pt) if pt else None
        self._drag = (i, n, n) if n is not None else None

    async def on_pan_update(self, e) -> None:
        """While dragging, show the stroke as it would be (not saved until the drag ends)."""
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
        """End of the drag: mark or erase the words dragged over."""
        if self._drag:
            i, first, last = self._drag
            self._drag = None
            await self._apply(i, first, last)

    async def _apply(self, page: int, a: int, b: int) -> None:
        """Mark words a..b in the chosen colour (or erase them), save, and redraw the page."""
        if self.tool == "erase":
            self.highlights = hl.erase(self.highlights, a, b, self.words)
        else:
            self.highlights = hl.add(self.highlights, a, b, self.colour, self.words)
        if self.app.doc_key:
            self.app.hl_store.save(self.app.doc_key, self.highlights)
        self.app.update_highlight_option()
        self._refresh_notes()
        await self.redraw(page)

    # ------------------------------------------------------------------ fold-out panels
    def on_read_panel(self, e) -> None:
        """The read-aloud button: fold the read-aloud controls out or away."""
        self._fold(self.read_panel, not self._is_open(self.read_panel))
        self.read_toggle.selected = self._is_open(self.read_panel)
        self.app.ui["read_panel_open"] = self.read_toggle.selected
        self.app.store.save_ui(self.app.ui)
        self.app.page.update()

    # ------------------------------------------------------------------ view: page colour, layout, rotation
    def _page_buttons(self) -> list[ft.Control]:
        """The page buttons that are always in the top bar: one page at a time or scrolling, fit width, and
        rotate (with the angle beside it once turned)."""
        t = self.app.t
        self.layout_btn = ft.IconButton(ft.Icons.SWAP_VERT, selected_icon=ft.Icons.SWAP_HORIZ,
                                        on_click=self.on_layout, style=self._toggle_style())
        self.fit_btn = ft.IconButton(ft.Icons.FIT_SCREEN, tooltip=t("Make the pages as wide as the window"),
                                     on_click=self.on_fit, style=self._toggle_style())
        self.rotate_btn = ft.IconButton(ft.Icons.ROTATE_90_DEGREES_CW, on_click=self.on_rotate,
                                        tooltip=t("Turn the reading view a quarter turn"), style=self._toggle_style())
        self.rotate_label = self.app.text("", 12)
        return [ft.Container(width=6), self.layout_btn, self.fit_btn,
                ft.Row([self.rotate_btn, self.rotate_label], spacing=0, tight=True), ft.Container(width=6)]

    def _tint_picker(self) -> ft.Control:
        """The page colours as a compact row of dots (their names are in the tooltips), for the reading settings
        panel; the page buttons (layout, fit width, rotate) are always in the top bar."""
        self.tint_row = ft.Row([self._tint_swatch(name) for name in TINT_COLOURS], spacing=6, tight=True)
        self._refresh_view_row()
        return ft.Column([self.app.text(self.app.t("Page colour"), 13), self.tint_row], spacing=4, tight=True)

    def _tint_swatch(self, name: str) -> ft.Control:
        """A round page colour button (its name in the tooltip)."""
        return ft.Container(width=26, height=26, border_radius=13, bgcolor=TINT_COLOURS[name][0], data=name,
                            on_click=self.on_tint, tooltip=self.app.t(name.capitalize()))

    def _refresh_view_row(self) -> None:
        """Show the chosen page colour (view panel) and layout, fit width and rotation (top bar buttons)."""
        if not hasattr(self, "tint_row"):
            return
        for dot in self.tint_row.controls:
            chosen = dot.data == self.tint
            dot.border = ft.Border.all(3 if chosen else 1, ft.Colors.PRIMARY if chosen else ft.Colors.OUTLINE)
        t = self.app.t
        self.fit_btn.selected = self.fit
        self.fit_btn.disabled = self.layout == "pages"
        self.rotate_btn.selected = bool(self.turns)
        self.rotate_label.value = f"{self.turns * 90}°" if self.turns else ""
        self.layout_btn.selected = self.layout == "pages"
        self.layout_btn.tooltip = t("One page at a time (click to scroll instead)") if self.layout == "pages" \
            else t("Scrolling pages (click for one page at a time)")

    def _apply_tint(self) -> None:
        """Colour the page frames and the area around them in the chosen page colour."""
        page_bg, around = TINT_COLOURS.get(self.tint, TINT_COLOURS["white"])
        self.body.bgcolor = around
        for frame in self.frames:
            frame.bgcolor = page_bg

    def on_tint(self, e) -> None:
        """A page colour button: use it for all pages."""
        self._save("focus_tint", e.control.data)
        self._apply_tint()
        self._refresh_view_row()
        self.app.page.update()
        self._start_rendering()

    async def on_layout(self, e) -> None:
        """The layout button: switch between one scrolling column and one page at a time."""
        self._save("focus_layout", "scroll" if self.layout == "pages" else "pages")
        self.page_zoom = 1.0
        self._refresh_view_row()
        await self._show_layout()
        self._start_rendering()

    def on_fit(self, e) -> None:
        """Fit width: make the pages as wide as the window, or go back to the zoom level."""
        self._save("focus_fit", not self.fit)
        self._refresh_view_row()
        self._resize()
        self.app.page.run_task(self.scroll_to, self.current, False)
        self._start_rendering()

    def on_rotate(self, e) -> None:
        """Rotate: turn the reading view a quarter turn clockwise (four taps go round)."""
        self._save("focus_rotation", (self.turns + 1) % 4)
        self.root.quarter_turns = self.turns
        self.body_size = (0.0, 0.0)  # measured again after the turn
        self._refresh_view_row()
        self._resize()
        self.app.page.run_task(self.scroll_to, self.current, False)
        self._start_rendering()

    def _full_screen(self, on: bool) -> None:
        """Make the app's window full screen or not (desktop app only)."""
        page = self.app.page
        if page.web or page.platform.is_mobile():
            return
        try:
            page.window.full_screen = on
        except Exception:
            pass

    def on_hide_bars(self, e) -> None:
        """Hide the top bar and panels to read without distractions (Esc or the small button brings them back)."""
        self.bars_hidden = True
        self._open_panels = [p for p in (self.read_panel, self.settings_panel) if self._is_open(p)]
        for panel in (self.read_panel, self.settings_panel):
            self._fold(panel, False)
        self.top.height = 0
        self.top.padding = 0
        self.divider.height = 0
        self.divider.thickness = 0
        self.show_bars.visible = True
        self._update_label()
        self._full_screen(True)
        self.app.page.update()

    def on_show_bars(self, e) -> None:
        """Bring the top bar back, with the panels that were open."""
        self.bars_hidden = False
        for panel in getattr(self, "_open_panels", []):
            self._fold(panel, True)
        self.top.height = None
        self.top.padding = ft.Padding.symmetric(horizontal=8, vertical=2)
        self.divider.height = 1
        self.divider.thickness = None
        self.show_bars.visible = False
        self._update_label()
        self._full_screen(False)
        self.app.page.update()

    def on_settings_panel(self, e) -> None:
        """The reading settings button: fold the settings out or away."""
        self._fold(self.settings_panel, not self._is_open(self.settings_panel))
        self.settings_toggle.selected = self._is_open(self.settings_panel)
        self.app.ui["focus_settings_open"] = self.settings_toggle.selected
        self.app.store.save_ui(self.app.ui)
        self.app.page.update()

    def _settings_row(self) -> ft.Control:
        """The settings that change how the text reads; the document is converted again in place."""
        app, t = self.app, self.app.t

        async def set_value(key, value):
            """Change one setting and convert the document again with it."""
            setattr(app.settings, key, value)
            await app.settings_changed()

        def slider(key, label, lo, hi, step, unit):
            """A labelled slider for one setting; the document is converted again when it is let go."""
            value_text = app.text(f"{getattr(app.settings, key):g} {unit}", 13)

            def moving(e):
                """Show the value while the slider moves (without converting yet)."""
                value_text.value = f"{round(float(e.control.value) / step) * step:g} {unit}"
                value_text.update()

            async def done(e):
                """The slider was let go: use the value (rounded to the slider's step)."""
                await set_value(key, round(round(float(e.control.value) / step) * step, 2))

            return ft.Container(ft.Column([ft.Row([app.text(label, 13), value_text], spacing=6),
                                           ft.Slider(value=getattr(app.settings, key), min=lo, max=hi,
                                                     divisions=int(round((hi - lo) / step)), on_change=moving,
                                                     on_change_end=done)], spacing=0, tight=True),
                                width=200)  # a fixed width, so the settings flow across the panel

        async def font_changed(e):
            """A font was chosen."""
            await set_value("font", e.control.value)

        async def align_changed(e):
            """An alignment was chosen."""
            await set_value("alignment", e.control.value)

        async def bold_changed(e):
            """Bold word starts switched on or off."""
            await set_value("bold_word_start", bool(e.control.value))

        return ft.Row([
            self._tint_picker(),
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
    """A tiny transparent PNG shown until a page has been rendered."""
    from .app import _blank_png

    return _blank_png()
