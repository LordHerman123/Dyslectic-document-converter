"""The AI check: a button next to Focus mode opens its own screen. There the AI can check the converted text, or
check it and fix everything; the findings are listed on the left, the page of the chosen finding (original and
converted) on the right. Nothing changes until the reader chooses, and every fix can be undone. Back returns to
the Convert screen as it was."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

import flet as ft

from ..ai.assistant import ConsentRequired
from ..ai.keystore import redact
from ..ai.providers import PROVIDERS, AIError
from ..render import preview
from .focus import _blank

if TYPE_CHECKING:
    from .app import ConverterApp

log = logging.getLogger(__name__)

KIND_ICONS = {"word": ft.Icons.SPELLCHECK, "scan": ft.Icons.DOCUMENT_SCANNER_OUTLINED,
              "furniture": ft.Icons.VERTICAL_ALIGN_TOP, "heading": ft.Icons.TITLE,
              "not_heading": ft.Icons.FORMAT_CLEAR, "order": ft.Icons.SWAP_VERT}


class CheckPanel:
    """The whole-document AI check: the button, the dialog before sending and the list of findings."""

    def __init__(self, app: "ConverterApp"):
        self.app = app
        self.open = False  # the AI check screen is showing
        self.selected: Optional[str] = None  # the finding whose page is shown

    # ------------------------------------------------------------------ the button
    def button(self) -> ft.Control:
        """The "AI check" button (greyed out while there is no document or AI is not set up)."""
        self.btn = ft.OutlinedButton(self.app.t("AI check"), icon=ft.Icons.FACT_CHECK_OUTLINED,
                                     on_click=self.on_button)
        self.update_button()
        return self.btn

    def ready(self) -> tuple[bool, str]:
        """Whether the check can run now, and the button's tooltip (what it does, or what is missing)."""
        app, t = self.app, self.app.t
        ai = app.ai_settings
        if ai.mode != "ai_assisted" or not ai.consent_given or not app.assistant.has_key:
            return False, t("The AI check needs AI: choose AI-assisted and add an API key in AI settings.")
        if not app.session:
            return False, t("Open a PDF first.")
        return True, t("Let the AI read the converted text and list conversion mistakes; you choose what to fix")

    def update_button(self) -> None:
        """Grey the button out, with a tooltip saying why, when the check cannot run; show how many findings are
        waiting."""
        if not hasattr(self, "btn"):
            return
        ok, tip = self.ready()
        session = self.app.session
        waiting = [f for f in session.check_findings if not f.applied] if session else []
        self.btn.disabled = not ok and not waiting
        self.btn.tooltip = tip
        self.btn.content = self.app.t("AI check") + (f" ({len(waiting)})" if waiting else "")

    async def on_button(self, e) -> None:
        """Open the AI check screen."""
        await self.show()

    # ------------------------------------------------------------------ the screen
    async def show(self) -> None:
        """Open the AI check screen in place of the app's own view (Back or Esc goes back)."""
        app, t = self.app, self.app.t
        if self.open:
            self.refresh()
            app.page.update()
            return
        self.open = True
        app.stop_reading()
        self._saved = list(app.page.controls)
        self._prev_keys = app.page.on_keyboard_event
        app.page.on_keyboard_event = self.on_key
        self.selected: Optional[str] = None
        self.status = app.text("", 13, expand=True)
        self.progress = ft.ProgressBar(value=0, visible=False)
        self.left = ft.Container(expand=True)
        self.orig_img = ft.Image(src=_blank(), fit=ft.BoxFit.CONTAIN, expand=True, gapless_playback=True)
        self.conv_img = ft.Image(src=_blank(), fit=ft.BoxFit.CONTAIN, expand=True, gapless_playback=True)
        self.orig_label = app.text(t("Original"), 13)
        self.conv_label = app.text(t("Converted"), 13)

        def pane(label, img) -> ft.Control:
            return ft.Column([label, ft.Container(img, expand=True, border=ft.Border.all(1, app.pal["frame"]))],
                             expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)

        wide = (app.page.width or 1200) >= 820
        self.preview_row = ft.Row([pane(self.orig_label, self.orig_img), pane(self.conv_label, self.conv_img)],
                                  expand=True, visible=wide, vertical_alignment=ft.CrossAxisAlignment.STRETCH)
        self.auto_btn = ft.FilledButton(t("Check and fix everything"), icon=ft.Icons.AUTO_FIX_HIGH,
                                        on_click=self.on_auto,
                                        tooltip=t("The AI checks the document, puts pages with text in the wrong "
                                                  "place in reading order, and the app makes every fix; all of it "
                                                  "can be undone"))
        self.check_btn = ft.OutlinedButton(t("Check the document"), icon=ft.Icons.FACT_CHECK_OUTLINED,
                                           on_click=self.on_check_again)
        self.undo_btn = ft.OutlinedButton(t("Undo all"), icon=ft.Icons.UNDO, on_click=self.on_undo_all)
        top = ft.Container(ft.Row([
            ft.FilledTonalButton(t("Back to converting"), icon=ft.Icons.ARROW_BACK, on_click=self.close),
            ft.Icon(ft.Icons.FACT_CHECK_OUTLINED, color=ft.Colors.PRIMARY),
            app.text(t("AI check"), 20, weight=ft.FontWeight.BOLD, expand=True),
            self.undo_btn, self.check_btn, self.auto_btn,
        ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10), bgcolor=ft.Colors.SURFACE_CONTAINER_LOW)
        root = ft.Column([
            top,
            ft.Container(ft.Column([ft.Row([self.status]), self.progress], spacing=4),
                         padding=ft.Padding.symmetric(horizontal=16)),
            ft.Row([ft.Container(self.left, width=520 if wide else None, expand=not wide,
                                 padding=ft.Padding.only(left=12, right=4)),
                    ft.VerticalDivider(width=1, visible=wide),
                    ft.Container(self.preview_row, expand=True, padding=8, visible=wide)],
                   expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH),
        ], expand=True, spacing=4)
        app.page.controls.clear()
        app.page.add(root)
        self.refresh()
        app.page.update()
        findings = app.session.check_findings if app.session else []
        if findings:
            await self.select(findings[0].id)
        elif app.session:
            await self._pages(app.orig_page, app.conv_page)

    async def close(self, e=None) -> None:
        """Back to the Convert screen as it was."""
        app = self.app
        if not self.open:
            return
        self.open = False
        app.page.on_keyboard_event = self._prev_keys
        app.page.controls.clear()
        app.page.controls.extend(self._saved)
        self.update_button()
        app.page.update()
        await app.show_pages()

    async def on_key(self, e) -> None:
        """Esc goes back to the Convert screen."""
        if e.key == "Escape":
            await self.close()

    def say(self, message: str, error: bool = False) -> None:
        """A message on the check screen's own status line."""
        self.status.value = message
        self.status.color = ft.Colors.ERROR if error else None
        try:
            self.app.page.update()
        except Exception:
            pass

    def refresh(self) -> None:
        """Draw the list and the buttons again (after a check, a fix or an undo)."""
        self.update_button()
        if not self.open:
            return
        app, t = self.app, self.app.t
        session = app.session
        ok = self.ready()[0]
        self.auto_btn.disabled = self.check_btn.disabled = not ok
        self.check_btn.content = t("Check again") if session and session.check_run else t("Check the document")
        self.undo_btn.disabled = not (session and (any(f.applied for f in session.check_findings)
                                                   or session.check_reordered))
        self.left.content = self.panel() if session and session.check_run else self.intro()

    def intro(self) -> ft.Control:
        """Before the first check: what the two buttons do."""
        app, t = self.app, self.app.t
        return ft.Column([
            ft.Container(height=8),
            app.text(t("The AI reads the converted text and lists places where the conversion may have gone wrong: "
                       "broken or joined words, headers or page numbers in the text, headings run into the text, "
                       "and text in the wrong place. It does not look for the author's own spelling mistakes."), 14),
            ft.Row([ft.Icon(ft.Icons.FACT_CHECK_OUTLINED, color=ft.Colors.PRIMARY),
                    app.text(t("Check the document: you see what was found, and choose what to fix."), 14,
                             expand=True)], vertical_alignment=ft.CrossAxisAlignment.START),
            ft.Row([ft.Icon(ft.Icons.AUTO_FIX_HIGH, color=ft.Colors.PRIMARY),
                    app.text(t("Check and fix everything: the AI goes over all pages, puts pages with text in the "
                               "wrong place in reading order, and the app makes every fix it found. Undo all puts "
                               "everything back."), 14, expand=True)],
                   vertical_alignment=ft.CrossAxisAlignment.START),
            app.text(t("Before anything is sent, you see how much text goes to which provider."), 13,
                     italic=True, color=app.pal["muted"]),
            ft.Row([ft.OutlinedButton(t("Check the document"), icon=ft.Icons.FACT_CHECK_OUTLINED,
                                      on_click=self.on_check_again, disabled=not self.ready()[0]),
                    ft.FilledButton(t("Check and fix everything"), icon=ft.Icons.AUTO_FIX_HIGH,
                                    on_click=self.on_auto, disabled=not self.ready()[0])], wrap=True),
            app.end_space(),
        ], spacing=14, scroll=ft.ScrollMode.AUTO)

    def panel(self) -> ft.Control:
        """What was found, "Fix all broken words", the pages read in the AI's order, and one card per finding."""
        app, t = self.app, self.app.t
        session = app.session
        findings = session.check_findings
        safe = [f for f in findings if f.safe and not f.applied]
        if findings:
            summary = t("{n} possible conversion mistake(s) found. Nothing is changed until you choose Fix; every "
                        "fix can be undone.", n=len(findings))
        else:
            summary = t("The AI found no conversion mistakes.")
        rows = [app.text(summary, 13),
                ft.Row([ft.FilledTonalButton(t("Fix all broken words ({n})", n=len(safe)), icon=ft.Icons.SPELLCHECK,
                                             on_click=self.on_fix_safe, disabled=not safe,
                                             tooltip=t("Only fixes that change nothing but spaces and hyphens"))])]
        # pages read in the AI's order: each can go back to the app's own order
        doc = session.document
        for number in sorted(session.layout_orders):
            info = doc.pages[number] if 0 <= number < len(doc.pages) else None
            shown = (info.source_page + 1) if info is not None and info.source_page >= 0 else number + 1
            rows.append(ft.Row([
                ft.Icon(ft.Icons.SWAP_VERT, size=app.fs(16), color=ft.Colors.PRIMARY),
                app.text(t("Page {n} is read in the AI's order.", n=shown), 13, expand=True),
                ft.TextButton(t("Undo"), icon=ft.Icons.UNDO, data=number, on_click=self.on_undo_reorder)],
                spacing=6))
        cards = [self.card(f) for f in findings]
        return ft.Column([ft.Container(height=4)] + rows + [
            ft.ListView(cards, spacing=8, expand=True, padding=ft.Padding.only(top=4, right=8, bottom=56))],
            spacing=8, expand=True)

    def card(self, f) -> ft.Control:
        """One finding: what it is, where, the text with the quote marked, the fix, and Fix / Undo. Clicking it
        shows its page on the right."""
        app, t = self.app, self.app.t
        label = {"word": t("Broken or joined word"), "scan": t("Misread in the scan"),
                 "furniture": t("Header, footer or page number in the text"),
                 "heading": t("Heading run into the text"), "not_heading": t("Not a heading"),
                 "order": t("Text in the wrong place")}[f.kind]
        if f.kind in ("word", "scan"):
            fix = None  # shown as the old and new words with an arrow between them (below)
        elif f.kind == "furniture":
            fix = t("Hide it, like other headers and footers") if f.whole else t("Remove it from the text")
        elif f.kind == "heading":
            fix = t("Make it a heading")
        elif f.kind == "not_heading":
            fix = t("Make it normal text")
        elif self._reordered(f):
            fix = t("This page is already read in the AI's order: compare with the original, or read only the "
                    "original in focus mode.")
        elif self.ready()[0]:
            fix = t("The AI can put the pieces of this page in reading order; you can undo it.")
        else:
            fix = t("The app cannot move text: compare with the original, or read only the original in focus mode.")
        mark = ft.TextStyle(weight=ft.FontWeight.BOLD, bgcolor=app.pal["notice_warning"],
                            decoration=ft.TextDecoration.LINE_THROUGH if f.applied and f.kind in (
                                "word", "scan", "furniture") else ft.TextDecoration.UNDERLINE,
                            decoration_color=app.pal["primary"])
        actions = []
        if f.applied:
            actions.append(ft.OutlinedButton(t("Undo"), icon=ft.Icons.UNDO, data=f.id, on_click=self.on_undo))
        elif f.fixable:
            actions.append(ft.FilledTonalButton(t("Fix"), icon=ft.Icons.CHECK, data=f.id, on_click=self.on_fix))
        elif f.kind == "order" and self.ready()[0] and not self._reordered(f):
            actions.append(ft.FilledTonalButton(t("Let AI fix the order of this page"), icon=ft.Icons.AUTO_FIX_HIGH,
                                                data=f.id, on_click=self.on_reorder,
                                                tooltip=t("The AI puts the pieces of the page in reading order; "
                                                          "you can undo it")))
        head = [ft.Icon(KIND_ICONS[f.kind], size=app.fs(18), color=ft.Colors.PRIMARY),
                app.text(label, 14, weight=ft.FontWeight.BOLD, expand=True),
                app.text(t("page {n}", n=f.page), 12, color=app.pal["muted"])]
        if f.applied:
            head.insert(2, ft.Icon(ft.Icons.CHECK_CIRCLE, size=app.fs(16), color=ft.Colors.GREEN_700,
                                   tooltip=t("Fixed")))
        chosen = f.id == getattr(self, "selected", None)
        return ft.Container(ft.Column([
            ft.Row(head, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Text(spans=[ft.TextSpan(f.before + " " if f.before else ""), ft.TextSpan(f.quote, style=mark),
                           ft.TextSpan(" " + f.after if f.after else "")], size=app.fs(14)),
            ft.Row([ft.Icon(ft.Icons.ARROW_FORWARD if f.fixable else ft.Icons.INFO_OUTLINE, size=app.fs(16)),
                    app.text(fix, 13, expand=True)], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START)
            if fix is not None else
            ft.Row([app.text(f"“{f.quote}”", 13), ft.Icon(ft.Icons.EAST, size=app.fs(16)),
                    app.text(f"“{f.fix}”", 13, weight=ft.FontWeight.BOLD)], spacing=6, wrap=True),
            app.text(t("AI: {reason}", reason=f.reason), 12, italic=True, color=app.pal["muted"])
            if f.reason else ft.Container(),
            ft.Row(actions, spacing=6, wrap=True) if actions else ft.Container(),
        ], spacing=6), padding=12, border_radius=10, data=f.id, on_click=self.on_card,
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST if chosen else ft.Colors.SURFACE_CONTAINER_LOW,
            border=ft.Border.all(2, ft.Colors.PRIMARY) if chosen else ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            tooltip=t("Show this page in the preview"))

    def _reordered(self, f) -> bool:
        """Whether the page of a finding is already read in the AI's order."""
        session = self.app.session
        b = session.document.block(f.block_id.split("~")[0]) if session else None
        return b is not None and b.page in session.layout_orders

    async def select(self, finding_id: str) -> None:
        """Show the page of a finding on the right: the original page and the converted page with its text."""
        app = self.app
        f = app.session.finding(finding_id) if app.session else None
        if f is None:
            return
        self.selected = f.id
        self.refresh()
        orig = max(0, min(app.orig_count - 1, f.page - 1))
        conv = next((p for p, src in sorted(app._page_map().items()) if orig in src), app.conv_page)
        await self._pages(orig, conv)

    async def _pages(self, orig: int, conv: int) -> None:
        """Show original page ``orig`` and converted page ``conv`` on the right."""
        app, t = self.app, self.app.t
        conv = max(0, min(app.conv_count - 1, conv))
        app.orig_page, app.conv_page = orig, conv  # the Convert screen shows the same pages when going back
        self.orig_label.value = f"{t('Original')} {orig + 1} / {app.orig_count}"
        self.conv_label.value = f"{t('Converted')} {conv + 1} / {app.conv_count}"
        if self.preview_row.visible:
            if app.source_path:
                self.orig_img.src = await app.in_thread(preview.render_page, app.original_view, orig, 900)
            if app.converted_pdf:
                self.conv_img.src = await app.in_thread(preview.render_page, app.converted_pdf, conv, 900)
        app.page.update()

    async def on_card(self, e) -> None:
        """A finding was clicked: show its page."""
        await self.select(e.control.data)

    # ------------------------------------------------------------------ running the check
    async def run(self, auto: bool = False) -> None:
        """Say what will be sent, then check the document part by part (answers known from earlier are reused);
        with ``auto`` also put pages with text in the wrong place in reading order and make every fix."""
        app, t = self.app, self.app.t
        ok, why = self.ready()
        if not ok:
            self.say(why, error=True)
            return
        try:
            requests, words = await app.in_thread(app.session.check_preview, app.assistant)
        except Exception as ex:
            log.error("check preview failed: %s", redact(str(ex)))
            self.say(t("The AI check failed; nothing was changed."), error=True)
            return
        if not words:
            self.say(t("This document has no text to check."))
            return
        if (requests or auto) and not await app.confirm(
                t("Check and fix everything with AI?") if auto else t("Check the whole document with AI?"),
                self._send_notice(requests, words, auto), t("Start") if auto else t("Check"), t("Cancel")):
            return
        self.progress.visible, self.progress.value = True, None
        self.say(t("Checking the document with AI..."))

        def progress(msg: str, frac: float) -> None:
            """Progress from the check: part n of m, then the pages put in order."""
            self.status.value = t.message(msg)
            self.progress.value = frac
            try:
                app.page.update()
            except Exception:
                pass

        try:
            if auto:
                fixed, pages = await app.in_thread(app.session.check_and_fix, app.assistant, app.settings, progress)
            else:
                await app.in_thread(app.session.run_check, app.assistant, progress)
        except ConsentRequired as ex:
            self._done()
            self.say(t.message(str(ex).split("\n")[0]), error=True)
            return
        except AIError as ex:
            self._done()
            self.say(t.message(str(ex)) + " " + (t("What was done so far can be undone.") if auto else
                                                  t("Nothing was changed.")), error=True)
            await self._changed()
            return
        except Exception as ex:
            log.error("check failed: %s", redact(str(ex)))
            self._done()
            self.say(t("The AI check failed; nothing was changed."), error=True)
            return
        self._done()
        findings = app.session.check_findings
        if auto:
            message = t("The AI made {n} fix(es) and put {pages} page(s) in reading order. Undo all puts everything "
                        "back.", n=fixed, pages=len(pages))
        else:
            waiting = sum(1 for f in findings if not f.applied)
            message = t("AI check: {n} possible conversion mistake(s) found.", n=waiting) if waiting else \
                t("AI check: no conversion mistakes found.")
        if app.session.check_failed:
            message += " " + t("{n} part(s) of the document could not be checked (the AI's answer was unreadable). "
                               "Check again to retry them.", n=app.session.check_failed)
        self.say(message, error=bool(app.session.check_failed))
        app.refresh_review()
        await self._changed()
        if findings and not any(f.id == self.selected for f in findings):
            await self.select(findings[0].id)

    def _done(self) -> None:
        """The check has finished: hide the progress bar and note what was sent."""
        self.progress.visible = False
        self.app.refresh_ai_log()

    def _send_notice(self, requests, words: int, auto: bool = False) -> ft.Control:
        """What the check does and what it sends, with the exact text behind a fold."""
        app, t = self.app, self.app.t
        ai = app.ai_settings
        cls = PROVIDERS.get(ai.provider)
        model = ai.model or (cls.default_model if cls else "")
        sent = "\n\n".join(r.prompt for r in requests)
        parts = [app.text(t("The AI goes over all pages: it checks the converted text, puts pages with text in the "
                            "wrong place in reading order, and the app then makes every fix it found. Undo all puts "
                            "everything back.") if auto else
                          t("The AI reads the converted text and lists places where the conversion may have gone "
                            "wrong: broken or joined words, headers or page numbers in the text, headings run into "
                            "the text, and text in the wrong place. It does not look for the author's own spelling "
                            "mistakes. Nothing is changed until you choose Fix, and every fix can be undone."), 14)]
        if requests:
            parts.append(app.text(t("This sends the whole text of the document to {provider} ({model}): about "
                                    "{words} words in {n} request(s).", provider=cls.label if cls else ai.provider,
                                    model=model, words=words, n=len(requests)), 14, weight=ft.FontWeight.BOLD))
        else:
            parts.append(app.text(t("The text was checked before: the earlier answers are used, nothing is sent "
                                    "again."), 14, weight=ft.FontWeight.BOLD))
        if auto:
            parts.append(app.text(t("For each page with text in the wrong place, it also sends where each piece of "
                                    "the page is, its type size and its first and last words."), 13))
        parts.append(app.text(t("E-mail addresses, links and long numbers are masked. Tables, pictures and the "
                                "reference list are not sent. Everything sent is listed in the privacy log in AI "
                                "settings. Your provider may charge for this."), 13))
        if requests:
            parts.append(ft.ExpansionTile(
                title=app.text(t("Show the text that will be sent"), 14),
                controls=[ft.Container(ft.Column([ft.Text(sent, size=app.fs(12), selectable=True)],
                                                 scroll=ft.ScrollMode.AUTO), height=240, padding=12,
                                       border_radius=6, bgcolor=ft.Colors.SURFACE_CONTAINER_LOW)]))
        return ft.Container(ft.Column(parts, spacing=10, tight=True), width=620)

    # ------------------------------------------------------------------ actions
    async def _changed(self) -> None:
        """Something was fixed or undone: convert again, then draw the list and the page again."""
        self.refresh()
        self.app.page.update()
        await self.app.rerender()
        if self.open and self.selected:
            await self.select(self.selected)
        elif self.open:
            self.refresh()
            self.app.page.update()

    async def on_fix(self, e) -> None:
        """Fix one finding."""
        if not self.app.session.fix_finding(e.control.data):
            self.say(self.app.t("This text was already changed (by you or another fix); undo that first."), error=True)
            return
        self.selected = e.control.data
        await self._changed()

    async def on_undo(self, e) -> None:
        """Undo the fix of one finding."""
        self.app.session.undo_finding(e.control.data)
        self.selected = e.control.data
        await self._changed()

    async def on_fix_safe(self, e) -> None:
        """Fix every broken or joined word."""
        if self.app.session.fix_safe_findings():
            await self._changed()

    async def on_undo_all(self, e) -> None:
        """Undo every fix made from the check, and the pages the AI put in order from it."""
        if self.app.session.undo_all_findings(self.app.settings):
            self.say(self.app.t("Everything the AI check changed was undone."))
            self.app.refresh_review()
            await self._changed()

    async def on_reorder(self, e) -> None:
        """Text in the wrong place: after saying what will be sent, ask the AI for the reading order of the page."""
        app, t = self.app, self.app.t
        f = app.session.finding(e.control.data)
        if f is None:
            return
        cls = PROVIDERS.get(app.ai_settings.provider)
        if not await app.confirm(
                t("Let AI fix the order of page {n}?", n=f.page),
                t("This sends where each piece of page {n} is, its type size and its first and last words (e-mail "
                  "addresses, links and long numbers masked) to {provider}. The app then reads the page in the order "
                  "the AI gives; you can undo it. The findings on this page are cleared: Check again checks the page "
                  "anew.",
                  n=f.page, provider=cls.label if cls else app.ai_settings.provider),
                t("Send"), t("Cancel")):
            return
        self.progress.visible, self.progress.value = True, None
        self.say(t("Asking AI for the reading order of the page..."))
        try:
            page = await app.in_thread(app.session.reorder_page, f.id, app.assistant, app.settings)
        except ConsentRequired as ex:
            self._done()
            self.say(t.message(str(ex).split("\n")[0]), error=True)
            return
        except AIError as ex:
            self._done()
            self.say(t.message(str(ex)) + " " + t("Nothing was changed."), error=True)
            return
        except Exception as ex:
            log.error("reorder failed: %s", redact(str(ex)))
            self._done()
            self.say(t("The AI check failed; nothing was changed."), error=True)
            return
        self._done()
        if page is None:
            self.say(t("The AI gave no usable order; the page is unchanged."))
            return
        self.say(t("Page {n} is read in the AI's order.", n=f.page))
        self.selected = None
        app.refresh_review()
        await self._changed()

    async def on_undo_reorder(self, e) -> None:
        """Read a page in the app's own order again."""
        self.app.session.undo_reorder(int(e.control.data), self.app.settings)
        self.app.refresh_review()
        await self._changed()

    async def on_check_again(self, e) -> None:
        """Check (again): parts whose text did not change are answered from earlier answers."""
        await self.run()

    async def on_auto(self, e) -> None:
        """Check and fix everything."""
        await self.run(auto=True)
