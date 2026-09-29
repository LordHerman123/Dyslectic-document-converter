"""Reading view: the converted text itself, flowing to fit the window (instead of page pictures).

Text size, line spacing, column width and page colour change at once, without converting or drawing any page,
and the text fits any screen, including a phone. The content is the composed document (the same the exports use),
so OCR corrections, bold word starts, moved citations and list markers are all there. Reading aloud goes sentence
by sentence and highlights the word being said. Where you were is remembered per document.
"""
from __future__ import annotations

import asyncio
import bisect
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
SPACING = 12  # between items, in pixels (plus each item's own space below)
TOP_PAD = 28  # room above the first item


class ReflowMode:
    """The reading view. Created once by the app (``app.reflow``); :meth:`open` shows it, :meth:`close` goes back."""

    def __init__(self, app: "ConverterApp"):
        self.app = app
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

    # ------------------------------------------------------------------ open / close
    async def open(self) -> None:
        """Show the reading view of the converted document, at the place it was left last time."""
        app, t = self.app, self.app.t
        if not app.session:
            app.notify(t("Open a PDF first."), error=True)
            return
        app.stop_reading()
        self.active = True
        self.result = await app.in_thread(app.session.compose, app.settings)
        self.items = [it for it in self.result.items if it.kind != "equation" or it.image is not None]
        self.current = int(app.reading_position("reflow", 0))
        self.current = min(self.current, max(0, len(self.items) - 1))
        self._units, self._unit_spans = [], []
        self._reading, self._read_pos, self._lit = False, None, None

        self.progress = app.text("", 13, color=ft.Colors.ON_SURFACE_VARIANT)
        self.read_btn = ft.IconButton(ft.Icons.PLAY_ARROW_ROUNDED, tooltip=t("Read aloud"), on_click=self.on_read,
                                      visible=app._speech_allowed())
        bar = ft.Row([
            ft.IconButton(ft.Icons.CLOSE, tooltip=t("Leave the reading view"), on_click=self.on_close),
            ft.IconButton(ft.Icons.TEXT_DECREASE, tooltip=t("Smaller text"), on_click=lambda e: self._size_by(-2)),
            ft.IconButton(ft.Icons.TEXT_INCREASE, tooltip=t("Larger text"), on_click=lambda e: self._size_by(2)),
            ft.IconButton(ft.Icons.FORMAT_LINE_SPACING, tooltip=t("More space between lines"),
                          on_click=lambda e: self._line_by(0.15)),
            ft.IconButton(ft.Icons.DENSITY_MEDIUM, tooltip=t("Less space between lines"),
                          on_click=lambda e: self._line_by(-0.15)),
            ft.IconButton(ft.Icons.WIDTH_NORMAL, tooltip=t("Column width"), on_click=self.on_width),
            self._tint_row(),
            self.read_btn,
            ft.IconButton(ft.Icons.AUTO_STORIES_OUTLINED, tooltip=t("Show the pages (focus mode)"),
                          on_click=self.on_pages),
            ft.Container(expand=True),
            self.progress,
        ], spacing=2, scroll=ft.ScrollMode.AUTO, vertical_alignment=ft.CrossAxisAlignment.CENTER)
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
        await self.close()

    async def on_pages(self, e=None) -> None:
        """Switch to focus mode (the pages), at the page of the paragraph being read."""
        page = await self.app.in_thread(self._page_of, self.current)
        await self.close()
        if page is not None:
            self.app.conv_page = page
        await self.app.focus.open()

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
            controls.append(ft.Container(c, key=f"item-{i}", data=i, on_size_change=self.on_item_size,
                                         on_click=self.on_item_click, border_radius=6,
                                         padding=ft.Padding.symmetric(horizontal=4, vertical=0)))
        self.column.controls = controls

    def _spans(self, i: int, it: RItem, lit: Optional[tuple[int, int]] = None) -> list[ft.TextSpan]:
        """The runs of an item as styled spans; ``lit`` (start, end) is the word being read aloud."""
        spans, pos = [], 0
        mark_bg = "#69FFD65A" if self.tint != "dark" else "#8A6A5A20"
        for r in self._runs(it):
            text = r.text
            parts = [(0, len(text), False)]
            if lit and pos < lit[1] and lit[0] < pos + len(text):
                a, b = max(0, lit[0] - pos), min(len(text), lit[1] - pos)
                parts = [(0, a, False), (a, b, True), (b, len(text), False)]
            for a, b, on in parts:
                if b <= a:
                    continue
                style = ft.TextStyle(weight=ft.FontWeight.BOLD if r.bold else None,
                                     italic=r.italic or None,
                                     bgcolor=mark_bg if on else None,
                                     font_family="Liberation" if r.math else None,
                                     size=self.size * 0.7 if (r.superscript or r.subscript) else None)
                spans.append(ft.TextSpan(text[a:b], style=style))
            pos += len(text)
        return spans

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
        if self._lit is not None:
            self._highlight(self._lit, None)
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

    async def on_read(self, e) -> None:
        """The play / pause button: read aloud from the paragraph at the top, or from where it paused."""
        ft.context.disable_auto_update()
        if self._reading:
            self._stop_reading(keep=True)
            self._update_read_btn()
            self._safe_update(self.read_btn)
            return
        if not self._units:
            self._sentences()
        if not self._units:
            return
        start = self._read_pos
        if start is None or start >= len(self._units) or self._units[start].page < self.current:
            start = next((k for k, u in enumerate(self._units) if u.page >= self.current), 0)
        self._start_reading(start)

    def on_item_click(self, e) -> None:
        """Clicking a paragraph while reading aloud moves the reading there."""
        ft.context.disable_auto_update()
        if not self._reading:
            return
        if not self._units:
            self._sentences()
        start = next((k for k, u in enumerate(self._units) if u.page >= e.control.data), None)
        if start is not None:
            self._start_reading(start)

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
        self._safe_update(self.read_btn)
        app.speaker.start(self._units, start, float(app.ui.get("read_speed", 1.0)), app._voice(),
                          on_word=lambda si, wi: post(self._show_word(si, wi)),
                          on_sentence=lambda si: post(self._show_word(si, 0)),
                          on_done=lambda finished: post(self._read_done(finished)))

    async def _show_word(self, si: int, wi: int) -> None:
        if not self._reading or si >= len(self._units):
            return
        self._read_pos = si
        item = self._units[si].page
        span = self._unit_spans[si][min(wi, len(self._unit_spans[si]) - 1)]
        if self._lit is not None and self._lit != item:
            self._highlight(self._lit, None)
        self._highlight(item, span)
        if item != self.current:  # follow the reading
            self.current = item
            self._update_progress()
            self._safe_update(self.progress)
            self.app.page.run_task(self._back_to, item, 300, 0)

    def _highlight(self, item: int, span: Optional[tuple[int, int]]) -> None:
        """Mark the word being said in paragraph ``item`` (None: no mark); only that paragraph is sent again."""
        text = self.texts.get(item)
        if text is None:
            return
        text.spans = self._spans(item, self.items[item], span)
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
        self._safe_update(self.read_btn)

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
