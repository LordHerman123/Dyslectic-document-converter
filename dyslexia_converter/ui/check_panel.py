"""The AI check on the Convert screen: a button next to Focus mode, a dialog that says what will be sent, and a
panel (in place of the settings column) with what the AI found. The reader chooses what to fix; every fix can be
undone, and "Show" turns the preview to the page."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import flet as ft

from ..ai.assistant import ConsentRequired
from ..ai.keystore import redact
from ..ai.providers import PROVIDERS, AIError

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
        self.open = False  # the results are shown in place of the settings column

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
        """Show the results when there are any, else start a check."""
        if self.app.session and self.app.session.check_findings and not self.open:
            self.show()
            return
        await self.run()

    # ------------------------------------------------------------------ running the check
    async def run(self) -> None:
        """Say what will be sent, then check the document part by part (answers known from earlier are reused)."""
        app, t = self.app, self.app.t
        ok, why = self.ready()
        if not ok:
            app.notify(why, error=True)
            return
        try:
            requests, words = await app.in_thread(app.session.check_preview, app.assistant)
        except Exception as ex:
            log.error("check preview failed: %s", redact(str(ex)))
            app.notify(t("The AI check failed; nothing was changed."), error=True)
            return
        if not words:
            app.notify(t("This document has no text to check."))
            return
        if requests and not await app.confirm(t("Check the whole document with AI?"),
                                              self._send_notice(requests, words), t("Check"), t("Cancel")):
            return
        app.busy(True, t("Checking the document with AI..."))

        def progress(msg: str, frac: float) -> None:
            """Progress from the check: part n of m."""
            app.status.value = t.message(msg)
            app.progress.value = frac
            try:
                app.page.update()
            except Exception:
                pass

        try:
            found = await app.in_thread(app.session.run_check, app.assistant, progress)
        except ConsentRequired as ex:
            app.notify(t.message(str(ex).split("\n")[0]), error=True)
            return
        except AIError as ex:
            app.notify(t.message(str(ex)) + " " + t("Nothing was changed."), error=True)
            return
        except Exception as ex:
            log.error("check failed: %s", redact(str(ex)))
            app.notify(t("The AI check failed; nothing was changed."), error=True)
            return
        finally:
            app.busy(False, app.doc_status() if app.session else "")
            app.refresh_ai_log()
        waiting = sum(1 for f in found if not f.applied)
        app.status.value = t("AI check: {n} possible conversion mistake(s) found.", n=waiting) if waiting else \
            t("AI check: no conversion mistakes found.")
        if app.session.check_failed:
            app.notify(t("{n} part(s) of the document could not be checked (the AI's answer was unreadable). "
                         "Check again to retry them.", n=app.session.check_failed), error=True)
        self.show()

    def _send_notice(self, requests, words: int) -> ft.Control:
        """What the check does and what it sends, with the exact text behind a fold."""
        app, t = self.app, self.app.t
        ai = app.ai_settings
        cls = PROVIDERS.get(ai.provider)
        model = ai.model or (cls.default_model if cls else "")
        sent = "\n\n".join(r.prompt for r in requests)
        return ft.Container(ft.Column([
            app.text(t("The AI reads the converted text and lists places where the conversion may have gone wrong: "
                       "broken or joined words, headers or page numbers in the text, headings run into the text, "
                       "and text in the wrong place. It does not look for the author's own spelling mistakes. "
                       "Nothing is changed until you choose Fix, and every fix can be undone."), 14),
            app.text(t("This sends the whole text of the document to {provider} ({model}): about {words} words in "
                       "{n} request(s).", provider=cls.label if cls else ai.provider, model=model, words=words,
                       n=len(requests)), 14, weight=ft.FontWeight.BOLD),
            app.text(t("E-mail addresses, links and long numbers are masked. Tables, pictures and the reference list "
                       "are not sent. Everything sent is listed in the privacy log in AI settings. Your provider may "
                       "charge for this."), 13),
            ft.ExpansionTile(title=app.text(t("Show the text that will be sent"), 14),
                             controls=[ft.Container(ft.Column([ft.Text(sent, size=app.fs(12), selectable=True)],
                                                              scroll=ft.ScrollMode.AUTO), height=240, padding=8,
                                                    border_radius=6, bgcolor=ft.Colors.SURFACE_CONTAINER_LOW)]),
        ], spacing=10, tight=True), width=620)

    # ------------------------------------------------------------------ the results
    def show(self) -> None:
        """Show the findings in place of the settings column (on a phone: in the Layout tab)."""
        self.open = True
        self.app.left_holder.content = self.panel()
        if self.app.tabs.selected_index != 0:
            self.app.tabs.selected_index = 0
        self.update_button()
        self.app.page.update()

    def close(self, e=None) -> None:
        """Back to the settings."""
        self.open = False
        self.app.left_holder.content = self.app.settings_col
        self.update_button()
        self.app.page.update()

    def refresh(self) -> None:
        """Draw the panel again (after a fix or an undo)."""
        if self.open:
            self.app.left_holder.content = self.panel()
        self.update_button()

    def panel(self) -> ft.Control:
        """The heading, what was found, the buttons for all findings, and one card per finding."""
        app, t = self.app, self.app.t
        findings = app.session.check_findings if app.session else []
        safe = [f for f in findings if f.safe and not f.applied]
        applied = [f for f in findings if f.applied]
        if findings:
            summary = t("{n} possible conversion mistake(s) found. Nothing is changed until you choose Fix; every "
                        "fix can be undone.", n=len(findings))
        else:
            summary = t("The AI found no conversion mistakes.")
        tools = [ft.FilledButton(t("Fix all broken words ({n})", n=len(safe)), icon=ft.Icons.AUTO_FIX_HIGH,
                                 on_click=self.on_fix_safe, disabled=not safe,
                                 tooltip=t("Only fixes that change nothing but spaces and hyphens")),
                 ft.OutlinedButton(t("Undo all fixes"), icon=ft.Icons.UNDO, on_click=self.on_undo_all,
                                   disabled=not applied),
                 ft.TextButton(t("Check again"), icon=ft.Icons.REFRESH, on_click=self.on_check_again,
                               disabled=not self.ready()[0])]
        cards = [self.card(f) for f in findings]
        # pages read in the AI's order: each can go back to the app's own order
        doc = app.session.document if app.session else None
        reordered = []
        for number in sorted(app.session.layout_orders) if app.session else []:
            info = doc.pages[number] if 0 <= number < len(doc.pages) else None
            shown = (info.source_page + 1) if info is not None and info.source_page >= 0 else number + 1
            reordered.append(ft.Row([
                ft.Icon(ft.Icons.SWAP_VERT, size=app.fs(16), color=ft.Colors.PRIMARY),
                app.text(t("Page {n} is read in the AI's order.", n=shown), 13, expand=True),
                ft.TextButton(t("Undo"), icon=ft.Icons.UNDO, data=number, on_click=self.on_undo_reorder)],
                spacing=6))
        return ft.Column([
            ft.Row([ft.Icon(ft.Icons.FACT_CHECK_OUTLINED, color=ft.Colors.PRIMARY),
                    app.text(t("AI check"), 18, weight=ft.FontWeight.BOLD, expand=True),
                    ft.IconButton(ft.Icons.CLOSE, tooltip=t("Back to the settings"), on_click=self.close)]),
            app.text(summary, 13),
            ft.Row(tools, wrap=True, spacing=8, run_spacing=6),
            *reordered,
            ft.ListView(cards, spacing=8, expand=True, padding=ft.Padding.only(right=8, bottom=24)),
        ], spacing=8, expand=True)

    def card(self, f) -> ft.Control:
        """One finding: what it is, where, the text with the quote marked, the fix, and Show / Fix / Undo."""
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
        else:
            fix = t("The app cannot move text: compare with the original, or read only the original in focus mode.")
        mark = ft.TextStyle(weight=ft.FontWeight.BOLD, bgcolor=app.pal["notice_warning"],
                            decoration=ft.TextDecoration.LINE_THROUGH if f.applied and f.kind in (
                                "word", "scan", "furniture") else ft.TextDecoration.UNDERLINE,
                            decoration_color=app.pal["primary"])
        actions = [ft.TextButton(t("Show"), icon=ft.Icons.VISIBILITY_OUTLINED, data=f.id, on_click=self.on_show,
                                 tooltip=t("Show this page in the preview"))]
        if f.applied:
            actions.append(ft.OutlinedButton(t("Undo"), icon=ft.Icons.UNDO, data=f.id, on_click=self.on_undo))
        elif f.fixable:
            actions.append(ft.FilledTonalButton(t("Fix"), icon=ft.Icons.CHECK, data=f.id, on_click=self.on_fix))
        elif f.kind == "order" and self.ready()[0]:
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
        return ft.Card(content=ft.Container(ft.Column([
            ft.Row(head, spacing=6, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            ft.Text(spans=[ft.TextSpan(f.before + " " if f.before else ""), ft.TextSpan(f.quote, style=mark),
                           ft.TextSpan(" " + f.after if f.after else "")], size=app.fs(14), selectable=True),
            ft.Row([ft.Icon(ft.Icons.ARROW_FORWARD if f.fixable else ft.Icons.INFO_OUTLINE, size=app.fs(16)),
                    app.text(fix, 13, expand=True)], spacing=6, vertical_alignment=ft.CrossAxisAlignment.START)
            if fix is not None else
            ft.Row([app.text(f"“{f.quote}”", 13), ft.Icon(ft.Icons.EAST, size=app.fs(16)),
                    app.text(f"“{f.fix}”", 13, weight=ft.FontWeight.BOLD)], spacing=6, wrap=True),
            app.text(t("AI: {reason}", reason=f.reason), 12, italic=True, color=app.pal["muted"])
            if f.reason else ft.Container(),
            ft.Row(actions, spacing=6, wrap=True),
        ], spacing=6), padding=10))

    # ------------------------------------------------------------------ actions
    async def _changed(self) -> None:
        """A fix was made or undone: draw the panel and the preview again."""
        self.refresh()
        self.app.page.update()
        await self.app.rerender()

    async def on_fix(self, e) -> None:
        """Fix one finding."""
        if not self.app.session.fix_finding(e.control.data):
            self.app.notify(self.app.t("This text was already changed (by you or another fix); undo that first."),
                            error=True)
            return
        await self._changed()

    async def on_undo(self, e) -> None:
        """Undo the fix of one finding."""
        self.app.session.undo_finding(e.control.data)
        await self._changed()

    async def on_fix_safe(self, e) -> None:
        """Fix every broken or joined word."""
        if self.app.session.fix_safe_findings():
            await self._changed()

    async def on_undo_all(self, e) -> None:
        """Undo every fix made from the check."""
        if self.app.session.undo_all_findings():
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
        app.busy(True, t("Asking AI for the reading order of the page..."))
        try:
            page = await app.in_thread(app.session.reorder_page, f.id, app.assistant, app.settings)
        except ConsentRequired as ex:
            app.notify(t.message(str(ex).split("\n")[0]), error=True)
            return
        except AIError as ex:
            app.notify(t.message(str(ex)) + " " + t("Nothing was changed."), error=True)
            return
        except Exception as ex:
            log.error("reorder failed: %s", redact(str(ex)))
            app.notify(t("The AI check failed; nothing was changed."), error=True)
            return
        finally:
            app.busy(False, app.doc_status() if app.session else "")
            app.refresh_ai_log()
        if page is None:
            app.notify(t("The AI gave no usable order; the page is unchanged."))
            return
        app.notify(t("Page {n} is read in the AI's order.", n=f.page))
        app.refresh_review()
        await self._changed()

    async def on_undo_reorder(self, e) -> None:
        """Read a page in the app's own order again."""
        self.app.session.undo_reorder(int(e.control.data), self.app.settings)
        self.app.refresh_review()
        await self._changed()

    async def on_check_again(self, e) -> None:
        """Check again (parts whose text did not change are answered from earlier answers)."""
        await self.run()

    async def on_show(self, e) -> None:
        """Turn the preview to the page of a finding (both sides in Both view)."""
        app = self.app
        f = app.session.finding(e.control.data)
        if f is None:
            return
        app.orig_page = max(0, min(app.orig_count - 1, f.page - 1))
        app._converted_follows()
        if app.tabs.selected_index != app.preview_tab_index:
            app.tabs.selected_index = app.preview_tab_index
        await app.show_pages()
