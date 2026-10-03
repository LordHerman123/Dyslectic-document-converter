"""Read along (the reading view): the converted text itself, flowing to fit the window (instead of page pictures).

Text size, line spacing, column width and page colour change at once, without converting or drawing any page,
and the text fits any screen, including a phone. The content is the composed document (the same the exports use),
so OCR corrections, bold word starts, moved citations and list markers are all there. Where you were is
remembered per document.

Colour help (optional) gives every other syllable of a word, or every other sentence, a second colour, so the eye
finds where a word or sentence changes. Reading along: read aloud from any paragraph, the sentence being read is
lightly marked and the word being said more strongly, and the text scrolls smoothly to keep them in view. The
reading speed is kept per document.
"""
from __future__ import annotations

import asyncio
import bisect
import functools
import re
from typing import TYPE_CHECKING, Optional

import flet as ft

from .. import speech
from ..render.compose import ComposeResult, RItem, Run

if TYPE_CHECKING:
    from .app import ConverterApp

# page colours (same as focus mode): background, text
PAPER = {"white": ("#FFFFFF", "#1A1A1A"), "cream": ("#FAF1D6", "#1A1A1A"), "blue": ("#D6E6F8", "#1A1A1A"),
         "green": ("#D8F0DC", "#1A1A1A"), "grey": ("#E2E2E2", "#1A1A1A"), "dark": ("#202024", "#E6E1DC")}
# the reading font of the document settings -> the font the app can show (bundled with it)
FONT_FAMILIES = {"Atkinson Hyperlegible": "Atkinson", "OpenDyslexic": "OpenDyslexic", "DejaVu Sans": "DejaVu",
                 "Verdana": "DejaVu", "Tahoma": "DejaVu", "Arial": "Liberation", "Liberation Sans": "Liberation"}
WIDTHS = {"narrow": 560, "medium": 720, "wide": 960}
# colour help: the second colour (every other syllable or sentence) on light pages and on the dark page
COLOUR_HELP = ("off", "syllables", "sentences")
SECOND_COLOUR = {"syllables": ("#1D5FA8", "#8FBFFF"), "sentences": ("#8A3B12", "#F2B27A")}
# reading along: the sentence being read (light) and the word being said (stronger), light / dark page
SENTENCE_BG = ("#2EFFC83C", "#40D8B45A")
WORD_BG = ("#8CFFD65A", "#A08A6A20")
SPEEDS = (0.5, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 1.75, 2.0)
SPACING = 12  # between items, in pixels (plus each item's own space below)
TOP_PAD = 28  # room above the first item


class ReflowMode:
    """The reading view. Created once by the app (``app.reflow``); :meth:`open` shows it, :meth:`close` goes back."""

    def __init__(self, app: "ConverterApp"):
        self.app = app
        self.from_focus = False  # opened from focus mode: leaving goes back to focus mode
        self.active = False
        self.items: list[RItem] = []
        self.result: Optional[ComposeResult] = None
        self.texts: dict[int, ft.Text] = {}  # item index -> its Text (for highlighting the word being read)
        self.heights: dict[int, float] = {}
        self.current = 0  # the item at the top of the view
        self._scroll_px = 0.0
        self._saved: list = []
        self._prev_keys = None
        self._units: list[speech.Sentence] = []
        self._unit_spans: list[list[tuple[int, int]]] = []  # per sentence, per word: (start, end) in its item
        self._reading = False
        self._read_pos: Optional[int] = None
        self._lit: Optional[int] = None  # item with a highlighted word
        self._marks: dict[int, list[tuple[int, int]]] = {}  # item -> parts in the second colour (colour help)
        self._viewport = 600.0  # height of the visible text, from the scroll events

    # ------------------------------------------------------------------ settings kept between sessions
    def _get(self, key: str, default):
        return self.app.ui.get(key, default)

    def _save(self, key: str, value) -> None:
        self.app.ui[key] = value
        self.app.store.save_ui(self.app.ui)

    @property
    def size(self) -> float:
        """Text size in pixels."""
        base = (self.app.settings.font_size or 12) * 1.35
        return float(self._get("reflow_size", round(base)))

    @property
    def line(self) -> float:
        return float(self._get("reflow_line", max(1.3, float(self.app.settings.line_spacing or 1.5))))

    @property
    def width(self) -> str:
        return self._get("reflow_width", "medium")

    @property
    def tint(self) -> str:
        return self._get("focus_tint", "cream")

    @property
    def family(self) -> Optional[str]:
        return FONT_FAMILIES.get(self.app.settings.font)

    @property
    def colour_help(self) -> str:
        """"off", "syllables" or "sentences"."""
        mode = self._get("reflow_colours", "off")
        return mode if mode in COLOUR_HELP else "off"

    @property
    def speed(self) -> float:
        """Reading speed for this document (the app's reading speed until one is chosen here)."""
        return float(self.app.reading_position("speed", self.app.ui.get("read_speed", 1.0)))

    # ------------------------------------------------------------------ open / close
    async def open(self, start_text: Optional[str] = None) -> None:
        """Show the reading view of the converted document, at the place it was left last time, or at the
        paragraph that holds ``start_text`` (the first words of the page shown in focus mode)."""
        app, t = self.app, self.app.t
        if not app.session:
            app.notify(t("Open a PDF first."), error=True)
            return
        app.stop_reading()
        self.active = True
        self.result = await app.in_thread(app.session.compose, app.settings)
        self.items = [it for it in self.result.items if it.kind != "equation" or it.image is not None]
        self.current = int(app.reading_position("reflow", 0))
        if start_text:
            found = self._item_with(start_text)
            if found is not None:
                self.current = found
        self.current = min(self.current, max(0, len(self.items) - 1))
        self._units, self._unit_spans = [], []
        self._reading, self._read_pos, self._lit = False, None, None
        self._marks = {}

        self.progress = app.text("", 13, color=ft.Colors.ON_SURFACE_VARIANT)
        self.read_btn = ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, tooltip=t("Read aloud"), on_click=self.on_read,
                                      visible=app._speech_allowed())
        self.stop_btn = ft.IconButton(ft.Icons.STOP_ROUNDED, tooltip=t("Stop"), on_click=self.on_stop,
                                      visible=False)
        self.speed_menu = ft.PopupMenuButton(
            content=ft.Container(app.text(self._speed_label(), 13, weight=ft.FontWeight.BOLD),
                                 padding=ft.Padding.symmetric(horizontal=8, vertical=6)),
            tooltip=t("Reading speed (kept for this document)"), visible=app._speech_allowed(),
            items=[ft.PopupMenuItem(self._speed_text(v), data=v, checked=abs(v - self.speed) < 0.01,
                                    on_click=self.on_speed) for v in SPEEDS])
        labels = {"off": t("No colour help"), "syllables": t("Colour syllables"),
                  "sentences": t("Colour sentences")}
        self.colour_menu = ft.PopupMenuButton(
            icon=ft.Icons.PALETTE_OUTLINED, tooltip=t("Colour help: syllables or sentences in two colours"),
            items=[ft.PopupMenuItem(labels[m], data=m, checked=m == self.colour_help, on_click=self.on_colour_help)
                   for m in COLOUR_HELP])
        # tap to read off: the reading view is one continuous page to scroll through, taps do nothing
        self.tap_btn = ft.IconButton(ft.Icons.TOUCH_APP_OUTLINED, selected_icon=ft.Icons.TOUCH_APP,
                                     selected=self.tap_to_read, on_click=self.on_tap_toggle,
                                     visible=app._speech_allowed(),
                                     style=ft.ButtonStyle(bgcolor={ft.ControlState.SELECTED: ft.Colors.PRIMARY_CONTAINER}))
        self._tap_tooltip()
        self.options_menu = app.reading_options_menu(["skip_citations", "skip_end", "reading_highlight"],
                                                     on_change=self._options_changed)
        self.options_menu.visible = app._speech_allowed()
        bar = ft.Row([
            ft.IconButton(ft.Icons.CLOSE, tooltip=t("Leave read along"), on_click=self.on_close),
            ft.IconButton(ft.Icons.TEXT_DECREASE, tooltip=t("Smaller text"), on_click=lambda e: self._size_by(-2)),
            ft.IconButton(ft.Icons.TEXT_INCREASE, tooltip=t("Larger text"), on_click=lambda e: self._size_by(2)),
            ft.IconButton(ft.Icons.FORMAT_LINE_SPACING, tooltip=t("More space between lines"),
                          on_click=lambda e: self._line_by(0.15)),
            ft.IconButton(ft.Icons.DENSITY_MEDIUM, tooltip=t("Less space between lines"),
                          on_click=lambda e: self._line_by(-0.15)),
            ft.IconButton(ft.Icons.WIDTH_NORMAL, tooltip=t("Column width"), on_click=self.on_width),
            self._tint_row(),
            self.colour_menu,
            ft.VerticalDivider(width=10),
            self.read_btn,
            self.stop_btn,
            self.speed_menu,
            self.tap_btn,
            self.options_menu,
            ft.IconButton(ft.Icons.AUTO_STORIES_OUTLINED, tooltip=t("Show the pages (focus mode)"),
                          on_click=self.on_pages),
            ft.Container(expand=True),
            self.progress,
        ], spacing=2, scroll=ft.ScrollMode.AUTO, vertical_alignment=ft.CrossAxisAlignment.CENTER)
        # leaving is always on the right, outside the part of the bar that scrolls on a narrow window
        exit_btn = ft.FilledTonalButton(t("Exit read along"), icon=ft.Icons.LOGOUT, on_click=self.on_close,
                                        tooltip=t("Back to where you came from"))
        bar = ft.Row([ft.Container(bar, expand=True), exit_btn], spacing=8,
                     vertical_alignment=ft.CrossAxisAlignment.CENTER)
        self.top = ft.Container(bar, padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
                                border=ft.Border.only(bottom=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)))
        self.column = ft.Column([], spacing=SPACING, tight=True)
        self.body = ft.Column([ft.Container(self.column, padding=ft.Padding.only(left=20, right=20, top=TOP_PAD,
                                                                                  bottom=120),
                                            alignment=ft.Alignment.TOP_CENTER)],
                              scroll=ft.ScrollMode.AUTO, expand=True, on_scroll=self.on_scroll, scroll_interval=150,
                              horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        self.paper = ft.Container(self.body, expand=True)
        self.root = ft.Column([self.top, self.paper], spacing=0, expand=True)
        self._build_items()
        self._apply_look()
        self._saved = list(app.page.controls)
        app.page.controls.clear()
        app.page.add(self.root)
        self._prev_keys = app.page.on_keyboard_event
        app.page.on_keyboard_event = self.on_key
        self._update_progress()
        app.page.update()
        if self.current:
            app.page.run_task(self._back_to, self.current)  # back to where reading stopped last time

    async def close(self) -> None:
        """Back to the app, remembering where reading stopped."""
        app = self.app
        if not self.active:
            return
        self.active = False
        self._stop_reading()
        app.save_reading_position("reflow", self.current)
        app.page.on_keyboard_event = self._prev_keys
        app.page.controls.clear()
        app.page.controls.extend(self._saved)
        app.page.update()

    async def on_close(self, e=None) -> None:
        """Exit read along: back to focus mode at the same place when it was opened from there, else back to the
        main screen."""
        if self.from_focus:
            self.from_focus = False
            await self.on_pages()
            return
        await self.close()

    async def on_pages(self, e=None) -> None:
        """Switch to focus mode (the pages), at the page of the paragraph being read."""
        page = await self.app.in_thread(self._page_of, self.current)
        await self.close()
        if page is not None:
            self.app.conv_page = page
        await self.app.focus.open()

    def _item_with(self, text: str) -> Optional[int]:
        """The first paragraph (item) that holds ``text`` (letters compared only), or None."""
        def norm(x: str) -> str:
            return re.sub(r"\W+", "", x.lower())

        probe = norm(text)
        for size in (40, 24, 12):  # a page may start halfway a paragraph that began on the page before
            p = probe[:size]
            if len(p) < 8:
                continue
            for i, it in enumerate(self.items):
                if p in norm(self.plain(it)):
                    return i
        return None

    def _page_of(self, index: int) -> Optional[int]:
        """The page of the converted document that holds item ``index`` (from its block), if known."""
        import pymupdf

        pdf = self.app.converted_pdf
        if not self.items or not pdf:
            return None
        probe = ""
        for it in self.items[index:index + 8]:  # the first item with enough text to find
            probe = re.sub(r"\W+", "", self.plain(it).lower())[:30]
            if len(probe) >= 8:
                break
        if len(probe) < 8:
            return None
        with pymupdf.open(stream=bytes(pdf), filetype="pdf") as doc:
            for n, page in enumerate(doc):
                if probe in re.sub(r"\W+", "", page.get_text().lower()):
                    return n
        return None

    async def on_key(self, e: ft.KeyboardEvent) -> None:
        if e.key == "Escape":
            await self.close()
        elif e.key in ("=", "+", "Numpad Add"):
            self._size_by(2)
        elif e.key in ("-", "Numpad Subtract"):
            self._size_by(-2)
        elif e.key == " " and self.app._speech_allowed():
            await self.on_read(None)

    # ------------------------------------------------------------------ the text
    def _build_items(self) -> None:
        """One control per item of the composed document: headings, paragraphs, lists, pictures, tables."""
        self.texts, self.heights = {}, {}
        controls = []
        for i, it in enumerate(self.items):
            c = self._item_control(i, it)
            controls.append(ft.Container(c, data=i, on_size_change=self.on_item_size,
                                         on_click=self.on_item_click, border_radius=6,
                                         padding=ft.Padding.symmetric(horizontal=4, vertical=0)))
        self.column.controls = controls

    def _spans(self, i: int, it: RItem, lit: Optional[tuple[int, int]] = None,
               sentence: Optional[tuple[int, int]] = None) -> list[ft.TextSpan]:
        """The runs of an item as styled spans. ``lit`` (start, end) is the word being read aloud, ``sentence`` the
        sentence it is in; with colour help, every other syllable or sentence is in the second colour."""
        dark = 1 if self.tint == "dark" else 0
        runs = self._runs(it)
        marks = self._colour_marks(i, it) if self.colour_help != "off" else []
        second = SECOND_COLOUR.get(self.colour_help, ("", ""))[dark]
        cuts = {0}
        pos = 0
        for r in runs:
            pos += len(r.text)
            cuts.add(pos)
        for rng in [lit, sentence] + marks:
            if rng:
                cuts.update(rng)
        cuts = sorted(c for c in cuts if 0 <= c <= pos)
        spans, pos = [], 0
        mi = 0
        for r in runs:
            end_run = pos + len(r.text)
            for a, b in zip(cuts, cuts[1:]):
                if b <= pos or a >= end_run:
                    continue
                while mi < len(marks) and marks[mi][1] <= a:
                    mi += 1
                coloured = mi < len(marks) and marks[mi][0] <= a < marks[mi][1]
                if lit and lit[0] <= a < lit[1]:
                    bg = WORD_BG[dark]
                elif sentence and sentence[0] <= a < sentence[1]:
                    bg = SENTENCE_BG[dark]
                else:
                    bg = None
                style = ft.TextStyle(weight=ft.FontWeight.BOLD if r.bold else None,
                                     italic=r.italic or None, bgcolor=bg,
                                     color=second if coloured else None,
                                     font_family="Liberation" if r.math else None,
                                     size=self.size * 0.7 if (r.superscript or r.subscript) else None)
                spans.append(ft.TextSpan(r.text[a - pos:b - pos], style=style))
            pos = end_run
        return spans

    def _colour_marks(self, i: int, it: RItem) -> list[tuple[int, int]]:
        """Parts of item ``i`` in the second colour: every other syllable of each word (starting with the second),
        or every other sentence of the paragraph (starting with the second). Kept until the text changes."""
        if i in self._marks:
            return self._marks[i]
        if it.kind == "about":  # the converter's own note at the end stays plain
            return []
        text = self.plain(it)
        out: list[tuple[int, int]] = []
        if self.colour_help == "syllables":
            lang = getattr(self.app.session.document, "language", "en") if self.app.session else "en"
            for m in re.finditer(r"[^\W\d_]{4,}", text):  # short words are one syllable anyway
                pos = m.start()
                for k, part in enumerate(_syllables(m.group(), lang or "en")):
                    if k % 2:
                        out.append((pos, pos + len(part)))
                    pos += len(part)
        elif self.colour_help == "sentences":
            words = list(re.finditer(r"\S+", text))
            start, n = 0, 0
            for k, m in enumerate(words):
                nxt = words[k + 1].group() if k + 1 < len(words) else None
                if speech._ends_sentence(m.group(), nxt) or nxt is None:
                    if n % 2:
                        out.append((start, m.end()))
                    n += 1
                    start = words[k + 1].start() if nxt is not None else m.end()
        self._marks[i] = out
        return out

    def on_colour_help(self, e) -> None:
        """Colour help chosen: no colours, syllables or sentences."""
        ft.context.disable_auto_update()
        self._save("reflow_colours", e.control.data)
        for item in self.colour_menu.items:
            item.checked = item.data == self.colour_help
        self._marks = {}
        self._respan()
        self.app.page.update()

    def _respan(self) -> None:
        """Styled text again for every paragraph (after the colour help or the page colour changed)."""
        for i, text in self.texts.items():
            text.spans = self._spans(i, self.items[i])
        self._lit = None
        if self._reading and self._read_pos is not None:
            self._mark_reading(self._read_pos, 0)

    def _runs(self, it: RItem) -> list[Run]:
        """The item's runs, with small formula pictures written as their text (a picture cannot sit in a line)."""
        pics = self.result.inline_images if self.result else {}
        out = []
        for r in it.runs:
            if any(ch in pics for ch in r.text):
                text = "".join((" " + (pics[ch].alt or "▢") + " ") if ch in pics else ch for ch in r.text)
                out.append(Run(text, bold=r.bold, italic=r.italic, math=True))
            else:
                out.append(r)
        return out

    def plain(self, it: RItem) -> str:
        """The item's text as it is shown (and read aloud)."""
        return "".join(r.text for r in self._runs(it))

    def _item_control(self, i: int, it: RItem) -> ft.Control:
        k = it.kind
        s = self.size
        if k == "image" or (k == "equation" and it.image is not None):
            img = it.image
            w = min(float(WIDTHS.get(self.width, 720)) - 40, max(80.0, img.width * (0.75 if k == "image" else 0.5)))
            h = w * img.height / max(1, img.width)  # its height from the start: the text below never jumps
            return ft.Container(ft.Image(src=img.data, width=w, height=h, fit=ft.BoxFit.CONTAIN),
                                alignment=ft.Alignment.CENTER, padding=ft.Padding.symmetric(vertical=6))
        if k == "table" and it.table is not None:
            return self._table(it)
        if k in ("title", "heading", "box_heading"):
            level = 0 if k == "title" else (it.level or 1)
            factor = {0: 1.6, 1: 1.4, 2: 1.2, 3: 1.1}.get(level, 1.05)
            text = ft.Text(spans=self._spans(i, it), size=s * factor, weight=ft.FontWeight.BOLD,
                           font_family=self.family, selectable=False)
            self.texts[i] = text
            return ft.Container(text, padding=ft.Padding.only(top=s * (0.9 if level <= 1 else 0.5)))
        small = k in ("caption", "endnote", "small", "about", "reference")
        text = ft.Text(spans=self._spans(i, it), size=s * (0.9 if small else 1.0), font_family=self.family,
                       style=ft.TextStyle(height=self.line, letter_spacing=self._letter(),
                                          word_spacing=self._word()),
                       italic=k in ("caption", "quote") or None)
        self.texts[i] = text
        if it.marker or k == "list_item":
            marker = ft.Text(it.marker or "•", size=s, weight=ft.FontWeight.BOLD, font_family=self.family,
                             style=ft.TextStyle(height=self.line), width=s * 2.2, text_align=ft.TextAlign.RIGHT)
            return ft.Row([marker, ft.Container(text, expand=True)], spacing=8,
                          vertical_alignment=ft.CrossAxisAlignment.START)
        if k in ("quote", "box_paragraph"):
            return ft.Container(text, padding=ft.Padding.only(left=14), border=ft.Border.only(
                left=ft.BorderSide(3, "#7A2E3A" if self.tint != "dark" else "#E3A3AE")))
        return text

    def _letter(self) -> float:
        return float(self.app.settings.letter_spacing or 0) * 1.33

    def _word(self) -> float:
        return max(0.0, float(self.app.settings.word_spacing or 0)) * 1.33

    def _table(self, it: RItem) -> ft.Control:
        rows = it.table.rows
        head = min(it.table.header_rows, len(rows))
        s = self.size * 0.9
        line = PAPER.get(self.tint, PAPER["white"])[1]
        out = []
        for ri, row in enumerate(rows):
            cells = [ft.Container(ft.Text(c, size=s, font_family=self.family,
                                          weight=ft.FontWeight.BOLD if ri < head else None),
                                  padding=6, width=max(90.0, min(260.0, s * 12)),
                                  border=ft.Border.all(1, line + "40"))
                     for c in row]
            out.append(ft.Row(cells, spacing=0))
        return ft.Row([ft.Column(out, spacing=0)], scroll=ft.ScrollMode.AUTO)

    def _apply_look(self) -> None:
        """Page colour, text colour and column width."""
        bg, fg = PAPER.get(self.tint, PAPER["white"])
        self.paper.bgcolor = bg
        self.column.width = WIDTHS.get(self.width, 720)
        for text in self._all_texts():
            text.color = fg

    def _all_texts(self):
        def walk(c):
            if isinstance(c, ft.Text):
                yield c
            for attr in ("content", "controls"):
                v = getattr(c, attr, None)
                if isinstance(v, list):
                    for x in v:
                        yield from walk(x)
                elif v is not None and hasattr(v, "__dict__"):
                    yield from walk(v)
        yield from walk(self.column)

    def _relayout(self) -> None:
        """Rebuild the text after a size or spacing change and keep the place."""
        ft.context.disable_auto_update()  # one update below is enough
        keep = self.current
        self._lit = None
        self._build_items()
        self._apply_look()
        self.app.page.update()
        self.app.page.run_task(self._back_to, keep)

    def _top_of(self, index: int) -> float:
        """Where paragraph ``index`` starts in the scrolling text, in pixels (from the measured heights)."""
        y = TOP_PAD
        for i in range(min(index, len(self.items))):
            y += self.heights.get(i, self.size * 3) + SPACING
        return y

    async def _back_to(self, index: int, duration: int = 0, wait: float = 0.2) -> None:
        """Scroll so paragraph ``index`` is at the top (once the paragraphs before it have been measured)."""
        await asyncio.sleep(wait)
        for _ in range(30):  # the window reports the height of every paragraph once it is laid out
            if all(i in self.heights for i in range(min(index, len(self.items)))):
                break
            await asyncio.sleep(0.1)
        try:
            await asyncio.wait_for(self.body.scroll_to(offset=max(0.0, self._top_of(index) - 8),
                                                       duration=duration), 3)
        except Exception:
            pass

    def _size_by(self, step: float) -> None:
        self._save("reflow_size", max(12.0, min(48.0, self.size + step)))
        self._relayout()

    def _line_by(self, step: float) -> None:
        self._save("reflow_line", round(max(1.1, min(3.0, self.line + step)), 2))
        self._relayout()

    def on_width(self, e) -> None:
        ft.context.disable_auto_update()
        order = list(WIDTHS)
        self._save("reflow_width", order[(order.index(self.width) + 1) % len(order)] if self.width in order
                   else "medium")
        self._apply_look()
        self.app.page.update()

    def _tint_row(self) -> ft.Control:
        dots = []
        for name, (bg, _) in PAPER.items():
            dots.append(ft.Container(width=22, height=22, border_radius=11, bgcolor=bg, data=name,
                                     border=ft.Border.all(2 if name == self.tint else 1,
                                                          ft.Colors.PRIMARY if name == self.tint
                                                          else ft.Colors.OUTLINE),
                                     tooltip=self.app.t(name.capitalize()), on_click=self.on_tint))
        self.tint_row = ft.Row(dots, spacing=6, tight=True)
        return ft.Container(self.tint_row, padding=ft.Padding.symmetric(horizontal=6))

    def on_tint(self, e) -> None:
        ft.context.disable_auto_update()
        self._save("focus_tint", e.control.data)
        for dot in self.tint_row.controls:
            on = dot.data == self.tint
            dot.border = ft.Border.all(2 if on else 1, ft.Colors.PRIMARY if on else ft.Colors.OUTLINE)
        self._apply_look()
        if self.colour_help != "off" or self._lit is not None:  # the colours of marks follow the page colour
            self._respan()
        self.app.page.update()

    # ------------------------------------------------------------------ where the reader is
    def on_item_size(self, e) -> None:
        """A paragraph reports its height (every paragraph does once it is laid out): only remembered. No update
        of the window follows, which for a whole book would mean comparing every paragraph a thousand times."""
        ft.context.disable_auto_update()
        self.heights[e.control.data] = e.height

    def on_scroll(self, e: ft.OnScrollEvent) -> None:
        """Follow scrolling: the paragraph at the top is where the reader is (only the percentage is updated)."""
        ft.context.disable_auto_update()
        self._scroll_px = e.pixels
        if e.viewport_dimension:
            self._viewport = float(e.viewport_dimension)
        tops, y = [], float(TOP_PAD)
        for i in range(len(self.items)):
            tops.append(y)
            y += self.heights.get(i, self.size * 3) + SPACING
        i = max(0, bisect.bisect_right(tops, e.pixels + 20) - 1)
        if i != self.current:
            self.current = i
            self._update_progress()
            self.progress.update()

    def _update_progress(self) -> None:
        n = max(1, len(self.items))
        self.progress.value = f"{round(100 * (self.current + 1) / n)} %"

    # ------------------------------------------------------------------ reading aloud
    def _sentences(self) -> None:
        """The text as sentences of words, each word knowing its item and place, for the speech engine."""
        units, spans = [], []
        for i, it in enumerate(self.items):
            if it.kind in ("image", "equation", "table") or it.kind == "about":
                continue
            text = self.plain(it)
            words = [(m.start(), m.end(), m.group()) for m in re.finditer(r"\S+", text)]
            cur, cur_spans = [], []
            for k, (a, b, w) in enumerate(words):
                start = sum(len(x.text) + 1 for x in cur)
                cur.append(speech.Word(w, i, [], start))
                cur_spans.append((a, b))
                nxt = words[k + 1][2] if k + 1 < len(words) else None
                if len(cur) >= speech.MAX_WORDS or speech._ends_sentence(w, nxt) or nxt is None:
                    units.append(speech.Sentence(cur))
                    spans.append(cur_spans)
                    cur, cur_spans = [], []
        self._units, self._unit_spans = units, spans

    @property
    def tap_to_read(self) -> bool:
        """Whether a tap on a paragraph reads from there (off: one continuous page, taps do nothing)."""
        return bool(self.app.ui.get("reflow_tap_read", True))

    def _tap_tooltip(self) -> None:
        t = self.app.t
        self.tap_btn.tooltip = t("Tap to read: on (tap a paragraph to read from there)") if self.tap_to_read else \
            t("Tap to read: off (the text is one continuous page; taps do nothing)")

    def on_tap_toggle(self, e) -> None:
        """Tap to read on or off."""
        ft.context.disable_auto_update()
        self.app.ui["reflow_tap_read"] = not self.tap_to_read
        self.app.store.save_ui(self.app.ui)
        self.tap_btn.selected = self.tap_to_read
        self._tap_tooltip()
        self._safe_update(self.tap_btn)

    async def _options_changed(self) -> None:
        """A reading option changed: while reading, the current sentence starts again with it."""
        if self._reading and self._read_pos is not None:
            self._start_reading(self._read_pos)

    def _end_unit(self) -> Optional[int]:
        """The first sentence of the reference list and notes at the end (None: there are none)."""
        from ..audio_export import END_HEADINGS

        first = next((i for i, it in enumerate(self.items) if it.kind in ("reference", "endnote")), None)
        if first is None:
            return None
        while first > 0 and self.items[first - 1].kind == "heading" and END_HEADINGS.match(self.items[first - 1].text):
            first -= 1
        if any(it.kind not in ("reference", "endnote", "heading", "about", "small") for it in self.items[first:]) \
                and not END_HEADINGS.match(self.items[first].text):
            return None  # running text after it: not the end of the document
        return next((k for k, u in enumerate(self._units) if u.page >= first), None)

    async def on_read(self, e) -> None:
        """The play / pause button: read aloud from the paragraph at the top, or from where it paused."""
        ft.context.disable_auto_update()
        if self._reading:
            self._stop_reading(keep=True)
            self._update_read_btn()
            self._safe_update(self.top)
            return
        if not self._units:
            self._sentences()
        if not self._units:
            return
        start = self._read_pos
        if start is None or start >= len(self._units) or self._units[start].page < self.current:
            start = next((k for k, u in enumerate(self._units) if u.page >= self.current), 0)
        self._start_reading(start)

    async def on_stop(self, e) -> None:
        """Stop reading aloud; the next start is from the paragraph at the top."""
        ft.context.disable_auto_update()
        self._stop_reading()
        if self._lit is not None:
            self._highlight(self._lit, None)
        self._update_read_btn()
        self._safe_update(self.top)

    def on_item_click(self, e) -> None:
        """Clicking a paragraph while reading aloud (or paused, or with "tap to read" on) reads from there."""
        ft.context.disable_auto_update()
        if not self.tap_to_read:
            return  # a continuous page: taps do nothing
        if not (self._reading or self._read_pos is not None or self.app.ui.get("tap_to_read", False)):
            return
        if not self.app._speech_allowed():
            return
        if not self._units:
            self._sentences()
        start = next((k for k, u in enumerate(self._units) if u.page >= e.control.data), None)
        if start is not None:
            if self._lit is not None:
                self._highlight(self._lit, None)
            self._start_reading(start)

    def on_speed(self, e) -> None:
        """A new reading speed, kept for this document; while reading, the current sentence starts again at it."""
        ft.context.disable_auto_update()
        self.app.save_reading_position("speed", float(e.control.data))
        for item in self.speed_menu.items:
            item.checked = abs(item.data - self.speed) < 0.01
        self.speed_menu.content.content.value = self._speed_label()
        self._safe_update(self.speed_menu)
        if self._reading and self._read_pos is not None:
            self._start_reading(self._read_pos)

    def _speed_label(self) -> str:
        return self._speed_text(self.speed)

    @staticmethod
    def _speed_text(v: float) -> str:
        text = f"{v:.2f}".rstrip("0").rstrip(".")
        return text + "×"

    def _start_reading(self, start: int) -> None:
        app = self.app
        loop = asyncio.get_running_loop()

        def post(coro):
            try:
                asyncio.run_coroutine_threadsafe(coro, loop)
            except RuntimeError:
                pass

        self._reading = True
        self._read_pos = start
        self._update_read_btn()
        self._safe_update(self.top)
        end = self._end_unit() if app.reading_option("skip_end") else None
        spoken, self._maps = speech.prepare_reading(self._units, app.reading_option("skip_citations"),
                                                    end if end is not None and start < end else None)
        app.speaker.start(spoken, start, self.speed, app._voice(),
                          on_word=lambda si, wi: post(self._show_word(si, wi)),
                          on_sentence=lambda si: post(self._show_word(si, 0)),
                          on_done=lambda finished: post(self._read_done(finished)))

    async def _show_word(self, si: int, wi: int) -> None:
        if not self._reading or si >= len(self._units):
            return
        self._read_pos = si
        kept = self._maps[si] if si < len(getattr(self, "_maps", [])) else []
        if kept:  # the word as numbered in the full sentence (citations may have been left out)
            wi = kept[min(wi, len(kept) - 1)]
        self._mark_reading(si, wi)

    def _mark_reading(self, si: int, wi: int) -> None:
        """Mark sentence ``si`` and its word ``wi`` and keep them in view (scrolling smoothly when the reading
        gets near the bottom of the window, or is out of view)."""
        item = self._units[si].page
        spans = self._unit_spans[si]
        span = spans[min(wi, len(spans) - 1)]
        if self._lit is not None and self._lit != item:
            self._highlight(self._lit, None)
        if self.app.reading_option("reading_highlight"):
            self._highlight(item, span, (spans[0][0], spans[-1][1]))
        elif self._lit is not None:
            self._highlight(self._lit, None)
        if item != self.current:
            self.current = item
            self._update_progress()
            self._safe_update(self.progress)
        # where the word is: its paragraph's top plus the part of the paragraph before it (an estimate)
        length = max(1, len(self.plain(self.items[item])))
        y = self._top_of(item) + self.heights.get(item, self.size * 3) * span[0] / length
        view = self._viewport
        if not (self._scroll_px + view * 0.12 <= y <= self._scroll_px + view * 0.7):
            self._scroll_px = max(0.0, y - view * 0.3)  # the reading line about a third from the top
            self.app.page.run_task(self._scroll_smoothly, self._scroll_px)

    async def _scroll_smoothly(self, offset: float) -> None:
        try:
            await asyncio.wait_for(self.body.scroll_to(offset=offset, duration=450), 3)
        except Exception:
            pass

    def _highlight(self, item: int, span: Optional[tuple[int, int]],
                   sentence: Optional[tuple[int, int]] = None) -> None:
        """Mark the word being said in paragraph ``item`` (None: no mark); only that paragraph is sent again."""
        text = self.texts.get(item)
        if text is None:
            return
        text.spans = self._spans(item, self.items[item], span, sentence)
        self._lit = item if span else None
        self._safe_update(text)

    @staticmethod
    def _safe_update(control: ft.Control) -> None:
        try:
            control.update()
        except Exception:  # not on the screen (the reading view was closed)
            pass

    async def _read_done(self, finished: bool) -> None:
        self._reading = False
        if finished:
            self._read_pos = None
        if self._lit is not None:
            self._highlight(self._lit, None)
        self._update_read_btn()
        self._safe_update(self.top)

    def _stop_reading(self, keep: bool = False) -> None:
        self._reading = False
        self.app.speaker.stop()
        if not keep:
            self._read_pos = None

    def _update_read_btn(self) -> None:
        t = self.app.t
        if self._reading:
            self.read_btn.icon, self.read_btn.tooltip = ft.Icons.PAUSE_ROUNDED, t("Pause")
        else:
            self.read_btn.icon = ft.Icons.PLAY_ARROW_ROUNDED
            self.read_btn.tooltip = t("Continue") if self._read_pos is not None else t("Read aloud")
        self.stop_btn.visible = self._reading or self._read_pos is not None


@functools.lru_cache(maxsize=20000)
def _syllables(word: str, language: str) -> tuple[str, ...]:
    """A word's syllables (kept: the same words come back often in a text)."""
    from ..dictionary import syllables

    return tuple(syllables(word, language))
