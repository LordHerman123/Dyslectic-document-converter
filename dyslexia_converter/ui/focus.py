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
from typing import TYPE_CHECKING, Optional

import flet as ft

from .. import dictionary
from .. import highlights as hl
from ..fonts import FONT_CHOICES
from ..render import preview
from ..speech import sentence_at

if TYPE_CHECKING:  # pragma: no cover
    from .app import ConverterApp

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
        self.page_zoom = 1.0
        del app.hl_items[1:]  # forget the menu of an earlier focus mode

        self.page_label = app.text("", 14)
        self.read_toggle = ft.IconButton(ft.Icons.VOLUME_UP, tooltip=t("Read aloud"), on_click=self.on_read_panel,
                                         selected=bool(app.ui.get("read_panel_open", False)),
                                         style=self._toggle_style(), visible=app._speech_allowed())
        self.settings_toggle = ft.IconButton(ft.Icons.TEXT_FIELDS, tooltip=t("Reading settings"),
                                             on_click=self.on_settings_panel,
                                             selected=bool(app.ui.get("focus_settings_open", False)),
                                             style=self._toggle_style())
        self.view_toggle = ft.IconButton(ft.Icons.PALETTE_OUTLINED, tooltip=t("View: page colour, pages, rotation"),
                                         on_click=self.on_view_panel,
                                         selected=bool(app.ui.get("focus_view_open", False)),
                                         style=self._toggle_style())
        self.mark_toggle = ft.IconButton(ft.Icons.BORDER_COLOR, tooltip=t("Highlighter"), on_click=self.on_marker,
                                         style=self._toggle_style())
        self.swatches = ft.Row([self._swatch(name) for name in SWATCHES] + [
            ft.IconButton(ft.Icons.AUTO_FIX_NORMAL, tooltip=t("Eraser"), data="erase", on_click=self.on_eraser,
                          style=self._toggle_style())], spacing=4, visible=False)
        self.ruler_toggle = ft.IconButton(ft.Icons.STRAIGHTEN, tooltip=t("Reading ruler (move it with the arrow "
                                                                         "keys or by tapping a line)"),
                                          on_click=self.on_ruler, style=self._toggle_style())
        self.top = ft.Container(ft.Row([
            ft.IconButton(ft.Icons.CLOSE, tooltip=t("Leave focus mode"), on_click=self.on_close),
            ft.Container(width=4),
            self.read_toggle, self.settings_toggle, self.view_toggle, self.mark_toggle, self.swatches,
            self.ruler_toggle,
            ft.Container(expand=True),
            self.page_label,
            app.build_export_menu(compact=True),
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
        self.settings_panel = self._panel(self._settings_row(), "focus_settings_open")
        self.view_panel = self._panel(self._view_row(), "focus_view_open")
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
                                 on_size_change=self.on_body_size, key="focus-body")
        self.card_layer = ft.Container(left=0, right=0, bottom=12, visible=False,
                                       alignment=ft.Alignment.BOTTOM_CENTER)
        self.show_bars = ft.Container(ft.IconButton(ft.Icons.FULLSCREEN_EXIT, tooltip=t("Show the bars"),
                                                    on_click=self.on_show_bars, icon_color="#FFFFFF"),
                                      bgcolor="#66000000", border_radius=24, right=10, top=10, visible=False)
        self.counter = ft.Container(ft.Text("", color="#FFFFFF", size=13), bgcolor="#88000000", border_radius=14,
                                    padding=ft.Padding.symmetric(horizontal=12, vertical=4), visible=False)
        self.column = ft.Column([self.top, self.read_panel, self.settings_panel, self.view_panel, self.divider,
                                 self.body],
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
        self._lines = {}
        page_bg = TINT_COLOURS.get(self.tint, TINT_COLOURS["white"])[0]
        self.images, self.frames, self.detectors = [], [], []
        for i, (pw, ph) in enumerate(self.sizes):
            img = ft.Image(src=_blank(), fit=ft.BoxFit.FILL, gapless_playback=True, expand=True)
            det = ft.GestureDetector(content=img, data=i, on_tap_down=self.on_tap,
                                     on_long_press_start=self.on_word_card, on_secondary_tap_down=self.on_word_card,
                                     on_size_change=self.on_size, mouse_cursor=ft.MouseCursor.CLICK, expand=True)
            w = self._page_w(i)
            frame = ft.Container(det, width=w, height=w * ph / pw, bgcolor=page_bg,
                                 shadow=ft.BoxShadow(blur_radius=10, color="#33000000"))
            self.images.append(img)
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
        picked = ()
        if self.card_word and self.card_word[0] == i and 0 <= self.card_word[1] < len(self.words):
            picked = self.words[self.card_word[1]][2]
        return preview.render_highlight(self.app.converted_pdf, i, width, list(sentence), list(word),
                                        marks=marks, tint=self.tint, ruler=ruler,
                                        notes=hl.note_marks(self.highlights, self.words, i), picked=list(picked))

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
        self.card_word = None
        self.card_layer.visible = False
        await self._build_pages()
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

        Esc closes the word card or brings hidden bars back; up/down move the reading ruler (or scroll);
        right, left, Page Up/Down and space turn pages. Keys are ignored while a note is being typed.
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

        With the highlighter on it marks (or erases) one word; on a note sign it opens the note; with the
        ruler on it moves the ruler to that line; and with *tap to read* on, reading aloud starts at the
        sentence tapped.
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
        for x, y in hl.note_marks(self.highlights, self.words, i):  # the note sign opens the note
            if abs(pt[0] - (x + 3)) < 12 and abs(pt[1] - (y - 5)) < 12:
                k = next(k for k, h in enumerate(self.highlights)
                         if h.note and hl.note_marks([h], self.words, i) == [(x, y)])
                where = hl.resolve(self.highlights[k], self.words)
                await self.open_card(i, where[0], edit_note=True)
                return
        if self.ruler:
            line = self._line_at(i, pt[1])
            if line is not None:
                await self._set_ruler(i, line)
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

    # ------------------------------------------------------------------ word card: meaning, sound, notes
    async def on_word_card(self, e) -> None:
        """Press-and-hold or right-click on a page: open the word card for the word there."""
        if self.tool:
            return
        i = e.control.data
        pos = e.local_position
        pt = self._point(i, pos.x, pos.y) if pos else None
        n = hl.word_at(hl.words_on_page(self.words, i), *pt) if pt else None
        if n is not None:
            await self.open_card(i, n)

    async def open_card(self, page: int, n: int, edit_note: bool = False) -> None:
        """Show the word card for word ``n`` on ``page`` (looked up in the dictionary; ``edit_note`` opens the
        note).
        """
        app = self.app
        old = self.card_word
        self.card_word = (page, n)
        if old and old[0] != page:
            await self.redraw(old[0])
        text = self.words[n][1]
        language = app.session.document.language if app.session else "en"
        entry = await app.in_thread(dictionary.lookup, text, language)
        k = hl.at(self.highlights, n, self.words)
        self.card_layer.content = self._card(page, n, entry, language, k, edit_note)
        self.card_layer.visible = True
        await self.redraw(page)
        app.page.update()

    async def close_card(self, e=None) -> None:
        """Close the word card and take the outline off its word."""
        self._typing = False
        self.card_layer.visible = False
        self.card_layer.content = None
        old, self.card_word = self.card_word, None
        self.app.page.update()
        if old:
            await self.redraw(old[0])

    def _card(self, page: int, n: int, entry, language: str, k: Optional[int], edit_note: bool) -> ft.Control:
        """The word card: the word and its base form, syllables, say button, meanings, online look-up, highlight
        colours and the note (``k`` is the highlight the word is in, if any).
        """
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
        # highlight and note
        h = self.highlights[k] if k is not None else None
        dots = [ft.Container(width=28, height=28, border_radius=14, bgcolor=SWATCHES[name], data=name,
                             tooltip=t(name.capitalize()),
                             border=ft.Border.all(3, ft.Colors.PRIMARY) if h and h.colour == name else None,
                             on_click=lambda e: app.page.run_task(self.card_colour, page, n, e.control.data))
                for name in SWATCHES]
        width = min(480.0, self._avail()[0] - 24)
        note_field = ft.TextField(value=h.note if h else "", multiline=True, min_lines=2, max_lines=5, width=width - 32,
                                  label=t("Note"), text_size=app.fs(14), autofocus=edit_note,
                                  visible=edit_note or bool(h and h.note),
                                  on_focus=lambda e: setattr(self, "_typing", True),
                                  on_blur=lambda e: setattr(self, "_typing", False))
        save = ft.FilledButton(t("Save note"), visible=note_field.visible,
                               on_click=lambda e: app.page.run_task(self.card_note, page, n, note_field.value))

        async def show_note(e):
            """"Add note": show the note field and put the cursor in it."""
            note_field.visible = save.visible = True
            add_note.visible = False
            app.page.update()
            try:
                await note_field.focus()
            except Exception:
                pass

        add_note = ft.TextButton(t("Add note"), icon=ft.Icons.STICKY_NOTE_2_OUTLINED, visible=not note_field.visible,
                                 on_click=show_note)
        remove = ft.TextButton(t("Remove highlight"), icon=ft.Icons.DELETE_OUTLINE, visible=h is not None,
                               on_click=lambda e: app.page.run_task(self.card_remove, page, n))
        rows += [ft.Divider(height=8),
                 ft.Row([app.text(t("Highlight"), 13), *dots, ft.Container(expand=True), add_note], spacing=8),
                 note_field,
                 ft.Row([remove, ft.Container(expand=True), save])]
        return ft.Card(content=ft.Container(ft.Column(rows, spacing=6, tight=True), padding=16, width=width),
                       elevation=8)

    async def _changed(self, page: int, n: int) -> None:
        """Highlights changed from the word card: save them and show the card again with the new state."""
        if self.app.doc_key:
            self.app.hl_store.save(self.app.doc_key, self.highlights)
        self.app.update_highlight_option()
        await self.open_card(page, n)

    async def card_colour(self, page: int, n: int, colour: str) -> None:
        """A colour on the word card: highlight the word, or change the colour of the highlight it is in."""
        k = hl.at(self.highlights, n, self.words)
        if k is None:
            self.highlights = hl.add(self.highlights, n, n, colour, self.words)
        else:
            self.highlights = hl.recolour(self.highlights, k, colour)
        await self._changed(page, n)

    async def card_note(self, page: int, n: int, note: str) -> None:
        """Save the note (a word without a highlight is highlighted in the current colour first)."""
        k = hl.at(self.highlights, n, self.words)
        if k is None:  # a note on a word that is not highlighted yet: highlight it in the current colour
            self.highlights = hl.add(self.highlights, n, n, self.colour, self.words, note.strip())
        else:
            self.highlights = hl.set_note(self.highlights, k, note)
        self._typing = False
        await self._changed(page, n)

    async def card_remove(self, page: int, n: int) -> None:
        """Remove the whole highlight the word is in (with its note)."""
        k = hl.at(self.highlights, n, self.words)
        if k is not None:
            where = hl.resolve(self.highlights[k], self.words)
            self.highlights = hl.erase(self.highlights, where[0], where[1], self.words)
            # erase keeps untouched parts; the whole highlight goes
        await self._changed(page, n)

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
        await self.redraw(page)

    # ------------------------------------------------------------------ fold-out panels
    def on_read_panel(self, e) -> None:
        """The read-aloud button: fold the read-aloud controls out or away."""
        self._fold(self.read_panel, not self._is_open(self.read_panel))
        self.read_toggle.selected = self._is_open(self.read_panel)
        self.app.ui["read_panel_open"] = self.read_toggle.selected
        self.app.store.save_ui(self.app.ui)
        self.app.page.update()

    def on_view_panel(self, e) -> None:
        """The view button: fold the view options (page colour, layout, fit width, rotate) out or away."""
        self._fold(self.view_panel, not self._is_open(self.view_panel))
        self.view_toggle.selected = self._is_open(self.view_panel)
        self._save("focus_view_open", self.view_toggle.selected)
        self.app.page.update()

    # ------------------------------------------------------------------ view: page colour, layout, rotation
    def _view_row(self) -> ft.Control:
        """The view options: page colours, Scroll / Pages, Fit width and Rotate."""
        t = self.app.t
        self.tint_row = ft.Row([self._tint_swatch(name) for name in TINT_COLOURS], spacing=8, tight=True)
        self.layout_seg = ft.SegmentedButton(
            segments=[ft.Segment("scroll", label=ft.Text(t("Scroll")), icon=ft.Icon(ft.Icons.SWAP_VERT)),
                      ft.Segment("pages", label=ft.Text(t("Pages")), icon=ft.Icon(ft.Icons.SWAP_HORIZ))],
            selected=[self.layout], on_change=self.on_layout)
        self.fit_btn = ft.OutlinedButton(t("Fit width"), icon=ft.Icons.FIT_SCREEN, on_click=self.on_fit,
                                         tooltip=t("Make the pages as wide as the window"))
        self.rotate_btn = ft.OutlinedButton(t("Rotate"), icon=ft.Icons.ROTATE_90_DEGREES_CW, on_click=self.on_rotate,
                                            tooltip=t("Turn the reading view a quarter turn"))
        self._refresh_view_row()
        return ft.Row([self.app.text(t("Page colour"), 13, weight=ft.FontWeight.W_500), self.tint_row,
                       ft.Container(width=12), self.layout_seg, self.fit_btn, self.rotate_btn],
                      spacing=12, wrap=True, vertical_alignment=ft.CrossAxisAlignment.CENTER)

    def _tint_swatch(self, name: str) -> ft.Control:
        """A round page colour button with its name under it."""
        return ft.Column([ft.Container(width=32, height=32, border_radius=16, bgcolor=TINT_COLOURS[name][0],
                                       data=name, on_click=self.on_tint, tooltip=self.app.t(name.capitalize())),
                          self.app.text(self.app.t(name.capitalize()), 11)],
                         spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER, tight=True)

    def _refresh_view_row(self) -> None:
        """Show the chosen page colour, layout, fit width and rotation on the view panel's buttons."""
        if not hasattr(self, "tint_row"):
            return
        for col in self.tint_row.controls:
            dot = col.controls[0]
            chosen = dot.data == self.tint
            dot.border = ft.Border.all(3 if chosen else 1, ft.Colors.PRIMARY if chosen else ft.Colors.OUTLINE)
        on = ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY_CONTAINER)
        self.fit_btn.style = on if self.fit else None
        self.fit_btn.disabled = self.layout == "pages"
        self.rotate_btn.content = self.app.t("Rotate") + (f" ({self.turns * 90}°)" if self.turns else "")
        self.layout_seg.selected = [self.layout]

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
        """Scroll / Pages: switch between one scrolling column and one page at a time."""
        sel = e.control.selected
        layout = (list(sel)[0] if sel else "scroll")
        self._save("focus_layout", layout)
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
        self._open_panels = [p for p in (self.read_panel, self.settings_panel, self.view_panel) if self._is_open(p)]
        for panel in (self.read_panel, self.settings_panel, self.view_panel):
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
