"""Optional AI assistance for cases local rules cannot decide.

Rules:
* Nothing is sent unless the user chose "AI-assisted" mode, entered a key and
  confirmed the privacy notice (``consent_given``).
* Only a few words around each uncertain item are sent, never the whole PDF, with e-mail addresses,
  links and long numbers masked. Everything sent is written to a privacy log on this device.
* Answers are cached per item, so the same content is never sent twice.
* Prompts carry worked examples (few-shot) in a fixed part that providers can cache, and answers only
  list the exceptions, to keep the number of tokens low.
* The AI only *classifies* or *proposes*; it never rewrites the document.
  AI proposals for OCR corrections always go to the review list.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from rapidfuzz.distance import Levenshtein

from ..model import Correction
from ..settings import AISettings, app_data_dir
from . import keys
from .keystore import KeyStore, redact
from .log import LogEntry, RequestLog
from .privacy import mask, window
from .prompts import (CITATIONS, LAYOUT, OCR, SUMMARY, Task, citation_prompt, layout_prompt, ocr_prompt,
                      summary_prompt)
from .providers import AIError, Reply, make_provider

PRIVACY_NOTICE = (
    "Some document content will be sent to the AI provider using your API key.\n\n"
    "Only a few words around each uncertain citation or OCR word are sent - never the whole PDF - and "
    "e-mail addresses, links and long numbers in them are masked. Everything that is sent is listed in the "
    "privacy log in the AI tab. Your AI provider may charge you for this usage, and its own privacy terms "
    "apply. Choose 'Local-only' at any time to keep all content on this device."
)
CHUNK = 30  # items per request: the fixed instructions and examples are shared by more items
SUMMARY_WORDS = 3000  # a longer text is summarised in parts, and the parts' points summarised once more
SUMMARY_POINTS = {False: 5, True: 10}  # most points in a short / detailed summary


class ConsentRequired(Exception):
    """AI was asked for while it is off or the user has not agreed to the privacy notice yet."""
    pass


@dataclass
class UsageEntry:
    """What one AI task used: how many items, whether it came from the cache, and the tokens."""
    task: str
    items: int
    cached: bool
    input_tokens: int = 0
    output_tokens: int = 0
    when: float = field(default_factory=time.time)


@dataclass
class Request:
    """One request as it would be sent: the fixed instructions, and the numbered snippets of this request."""
    task: Task
    prompt: str
    keys: list[str]  # cache key of each item, in order
    items: list  # what each numbered line is about (used to apply the answer)
    answer_items: int = 0  # how many numbers the answer lists, when not one per key (the pieces of a page)

    @property
    def system(self) -> str:
        """The fixed instructions of the task (the same for every request, so providers can cache them)."""
        return self.task.system

    @property
    def max_tokens(self) -> int:
        """The answer length to allow: a little for the frame plus a fixed amount per snippet."""
        return 64 + self.task.tokens_per_item * (self.answer_items or len(self.keys))


class AICache:
    """AI answers kept on this device, keyed by task, provider, model and snippet, so the same text is never sent
    twice.
    """
    def __init__(self, path: Optional[Path] = None):
        """Load the cache file (an empty cache when it is missing or damaged)."""
        self.path = path or (app_data_dir() / "ai_cache.json")
        try:
            self.data: dict = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}

    @staticmethod
    def key(*parts: str) -> str:
        """A hash of the parts: the cache never stores the document text itself as a key."""
        return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()

    def get(self, key: str):
        """The stored answer for a key, or None."""
        return self.data.get(key)

    def put(self, key: str, value) -> None:
        """Store one answer."""
        self.data[key] = value
        self._save()

    def put_many(self, values: dict) -> None:
        """Store several answers at once (one write)."""
        self.data.update(values)
        self._save()

    def _save(self) -> None:
        """Write the cache file (failing to write is ignored: it is only a cache)."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data), encoding="utf-8")
        except OSError:
            pass

    def clear(self) -> None:
        """Forget every stored answer and delete the file."""
        self.data = {}
        try:
            self.path.unlink()
        except OSError:
            pass


class AIAssistant:
    """Sends small, masked snippets of the document to the user's AI provider, only when AI-assisted mode is on and
    the user agreed.

    It builds compact requests (few-shot prompts, several snippets per request), reuses cached answers, records
    every request in the privacy log, and applies the answers with safety checks (the AI may only fix a word, not
    rewrite text).
    """
    def __init__(self, settings: AISettings, keystore: Optional[KeyStore] = None, cache: Optional[AICache] = None,
                 log: Optional[RequestLog] = None):
        """``settings``: mode, provider, model and tasks; the key store, cache and log can be replaced for tests."""
        self.settings = settings
        self.keystore = keystore or KeyStore()
        self.cache = cache or AICache()
        self.log = log or RequestLog()
        self.usage: list[UsageEntry] = []

    # ------------------------------------------------------------------ state
    @property
    def has_key(self) -> bool:
        """Whether there is an API key to use (the key in use, or the provider's key from older versions)."""
        return bool(keys.secret(self.settings, self.keystore))

    @property
    def active(self) -> bool:
        """Whether AI can be used now (AI-assisted mode and a key)."""
        return self.settings.mode == "ai_assisted" and self.has_key

    def _provider(self):
        """The provider client to send with; raises when AI is off, consent is missing or there is no key."""
        if self.settings.mode != "ai_assisted":
            raise ConsentRequired("AI is switched off (Local-only mode).")
        if not self.settings.consent_given:
            raise ConsentRequired(PRIVACY_NOTICE)
        key = keys.secret(self.settings, self.keystore)
        if not key:
            raise AIError("No API key entered. Add one in AI Settings.")
        return make_provider(self.settings.provider, key, self.settings.model or None), key

    def _item_key(self, task: str, snippet: str) -> str:
        """Cache key of one snippet for one task with the current provider and model."""
        return AICache.key(task, self.settings.provider, self.settings.model, snippet)

    # --------------------------------------------------------------- planning
    def plan_citations(self, candidates: list[tuple[str, str, int, int]]) -> tuple[list[Request], dict[str, bool]]:
        """``candidates``: (key, text around it, start, end of the citation in that text).

        Returns the requests that would be sent, and the decisions already known from earlier answers.
        """
        known: dict[str, bool] = {}
        groups: dict[str, tuple[str, list[str]]] = {}  # cache key -> (snippet, candidate keys): sent once
        for key, text, start, end in candidates:
            snippet = window(text, start, end, before=8, after=6)
            ck = self._item_key("citations", snippet)
            hit = self.cache.get(ck)
            if hit is not None:
                known[key] = bool(hit)
            else:
                groups.setdefault(ck, (snippet, []))[1].append(key)
        todo = list(groups.items())
        requests = []
        for start in range(0, len(todo), CHUNK):
            chunk = todo[start:start + CHUNK]
            requests.append(Request(CITATIONS, citation_prompt([snip for _, (snip, _) in chunk]),
                                    [ck for ck, _ in chunk], [keys for _, (_, keys) in chunk]))
        return requests, known

    def plan_ocr(self, items: list[tuple[Correction, str, int, int]]) -> tuple[list[Request], dict[int, dict]]:
        """``items``: (correction, text around it, start, end of the OCR word in that text)."""
        known: dict[int, dict] = {}
        todo: list[tuple[Correction, str, str, str]] = []
        for i, (c, text, start, end) in enumerate(items):
            snippet = window(text, start, end, before=6, after=6)
            ck = self._item_key("ocr", c.replacement + "|" + snippet)
            hit = self.cache.get(ck)
            if hit is not None:
                known[i] = hit
            else:
                todo.append((c, c.replacement, snippet, ck))
        requests = []
        for start in range(0, len(todo), CHUNK):
            chunk = todo[start:start + CHUNK]
            requests.append(Request(OCR, ocr_prompt([(sug, snip) for _, sug, snip, _ in chunk]),
                                    [ck for *_, ck in chunk], [c for c, *_ in chunk]))
        return requests, known

    # ---------------------------------------------------------------- sending
    def send(self, request: Request) -> Reply:
        """Send one request, log exactly what was sent and received (also when it fails), and return the reply."""
        provider, key = self._provider()
        entry = LogEntry(request.task.name, self.settings.provider, provider.model, len(request.keys),
                         request.system, request.prompt)
        try:
            reply = provider.complete_json(request.system, request.prompt, request.task.schema,
                                           request.max_tokens, request.task.answer_hint)
        except AIError as e:
            entry.error = str(e)
            self.log.add(entry)
            raise
        except Exception as e:  # never leak the key through unexpected errors
            entry.error = f"request failed ({type(e).__name__})"
            self.log.add(entry)
            raise AIError(redact(f"AI request failed: {type(e).__name__}", key)) from None
        entry.answer = reply.text or json.dumps(reply.data)
        entry.input_tokens, entry.output_tokens = reply.input_tokens, reply.output_tokens
        entry.cached_tokens = reply.cached_tokens
        self.log.add(entry)
        self.usage.append(UsageEntry(request.task.name, len(request.keys), False,
                                     reply.input_tokens, reply.output_tokens))
        return reply

    def check_key(self, provider: str, value: str, model: str = "") -> "keys.CheckResult":
        """Check that a key works with one tiny request (no document text); the check is in the privacy log."""
        result, used_model, answer = keys.check(provider, value, model)
        self.log.add(LogEntry("check", provider, used_model, 0, keys.CHECK_SYSTEM, keys.CHECK_PROMPT, answer=answer,
                              error=redact(result.message, value) if not result.ok else ""))
        result.message = redact(result.message, value)
        return result

    # ------------------------------------------------------------------ unusual page layouts
    def plan_layout(self, pages: dict[int, list]) -> tuple[list[Request], dict[int, list[int]]]:
        """``pages``: page number -> its pieces (x0, y0, x1, y1 in % of the page, font size, text or None for a
        picture). One request per page, with the text masked and only the first and last words of each piece;
        orders known from earlier answers are reused."""
        known: dict[int, list[int]] = {}
        requests = []
        for page, ps in pages.items():
            prompt = layout_prompt([(x0, y0, x1, y1, size, mask(text) if text is not None else None)
                                    for x0, y0, x1, y1, size, text in ps])
            ck = self._item_key("layout", prompt)
            hit = self.cache.get(ck)
            if hit is not None:
                known[page] = list(hit)
            else:
                requests.append(Request(LAYOUT, prompt, [ck], [(page, len(ps))], answer_items=len(ps)))
        return requests, known

    def order_layout(self, pages: dict[int, list],
                     progress: Optional[Callable[[str, float], None]] = None) -> dict[int, list[int]]:
        """The reading order of the pieces of pages with an unusual layout (page number -> piece numbers). An
        answer that would lose or repeat text is not used: that page keeps the local order."""
        requests, orders = self.plan_layout(pages)
        if orders:
            self.usage.append(UsageEntry("layout", len(orders), True))
        for n, req in enumerate(requests):
            if progress:
                progress("Asking AI about unusual page layouts", n / max(1, len(requests)))
            page, count = req.items[0]
            order = checked_order(self.send(req).data.get("o"), count)
            if order is not None:
                orders[page] = order
                self.cache.put(req.keys[0], order)
        return orders

    # ------------------------------------------------------------------ summaries
    def summary_words(self, text: str) -> int:
        """How many words a summary of ``text`` sends (to tell the user before sending)."""
        return len(text.split())

    def summarise(self, text: str, language: str = "en", detailed: bool = False, plain: bool = True,
                  progress: Optional[Callable[[str, float], None]] = None) -> Summary:
        """A summary of a part of the document chosen by the reader (only in AI-assisted mode, with consent).

        E-mail addresses, links and long numbers are masked first. A long text is summarised in parts of about
        SUMMARY_WORDS words, and the points of the parts are summarised once more. Answers are cached, so
        summarising the same text again sends nothing.
        """
        self._provider()  # refuses when AI is off or there is no consent or key
        parts = _summary_parts(mask(text))
        if not parts:
            return Summary("", [])
        if len(parts) > 1:
            points = []
            for n, part in enumerate(parts):
                if progress:
                    progress(f"Summarising part {n + 1} of {len(parts)}", n / (len(parts) + 1))
                s = self._summary_request(part, language, False, False)
                points += [f"{s.title}: {p}" for p in s.points] if s.title else s.points
            text = "\n".join(f"- {p}" for p in points)
        else:
            text = parts[0]
        return self._summary_request(text, language, detailed, plain)

    def _summary_request(self, text: str, language: str, detailed: bool, plain: bool) -> Summary:
        """One summary request (or its cached answer)."""
        prompt = summary_prompt(text, language, detailed, plain)
        ck = self._item_key("summary", prompt)
        hit = self.cache.get(ck)
        if hit is None:
            reply = self.send(Request(SUMMARY, prompt, [ck], [None]))
            hit = {"t": str(reply.data.get("t", "")), "b": [str(p) for p in reply.data.get("b", []) if str(p).strip()]}
            self.cache.put(ck, hit)
        else:
            self.usage.append(UsageEntry("summary", 1, True))
        # the length the user chose, even when a model gives more points than asked
        return Summary(hit.get("t", ""), list(hit.get("b", []))[:SUMMARY_POINTS[detailed]])

    # ------------------------------------------------------------------ tasks
    def classify_citations(self, candidates: list[tuple[str, str, int, int]],
                           progress: Optional[Callable[[str, float], None]] = None) -> dict[str, bool]:
        """Decide for each candidate whether it is a citation. Returns candidate key -> is_citation."""
        requests, decisions = self.plan_citations(candidates)
        if decisions:
            self.usage.append(UsageEntry("citations", len(decisions), True))
        for n, req in enumerate(requests):
            if progress:
                progress("Asking AI about uncertain citations", n / max(1, len(requests)))
            yes = {i for i in self.send(req).data.get("c", []) if isinstance(i, int)}
            values = {ck: i in yes for i, ck in enumerate(req.keys)}
            self.cache.put_many(values)
            for i, cands in enumerate(req.items):
                for key in cands:
                    decisions[key] = values[req.keys[i]]
        return decisions

    def review_ocr_words(self, items: list[tuple[Correction, str, int, int]],
                         progress: Optional[Callable[[str, float], None]] = None) -> None:
        """Give a second opinion on uncertain OCR corrections (updates them in place).

        The AI may agree, propose a different word, or say the word is correct. Proposals stay pending:
        the user decides.
        """
        requests, known = self.plan_ocr(items)
        if known:
            self.usage.append(UsageEntry("ocr", len(known), True))
        for i, verdict in known.items():
            _apply_ocr(items[i][0], verdict)
        for n, req in enumerate(requests):
            if progress:
                progress("Asking AI about uncertain OCR words", n / max(1, len(requests)))
            fixes = {}
            for r in self.send(req).data.get("f", []):
                if isinstance(r, dict) and isinstance(r.get("i"), int):
                    fixes[r["i"]] = str(r.get("w", "")).strip()
            values = {}
            for i, c in enumerate(req.items):
                verdict = {"err": i in fixes, "w": fixes.get(i, "")}
                values[req.keys[i]] = verdict
                _apply_ocr(c, verdict)
            self.cache.put_many(values)


@dataclass
class Summary:
    """An AI summary: a short title and the main points."""
    title: str
    points: list[str]


def _summary_parts(text: str, size: int = SUMMARY_WORDS) -> list[str]:
    """The text in parts of about ``size`` words, cut after a sentence where possible."""
    words = text.split()
    parts, start = [], 0
    while start < len(words):
        end = min(len(words), start + size)
        if end < len(words):  # end the part at the last full stop in its final fifth
            for k in range(end, start + size * 4 // 5, -1):
                if words[k - 1].endswith((".", "!", "?")):
                    end = k
                    break
        parts.append(" ".join(words[start:end]))
        start = end
    return parts


def checked_order(answer, count: int) -> Optional[list[int]]:
    """The AI's reading order of ``count`` pieces, if it keeps every piece exactly once: an unknown or repeated
    number makes the answer unusable (None); pieces it left out are added at the end in their local order."""
    if not isinstance(answer, list) or not all(isinstance(i, int) and 0 <= i < count for i in answer):
        return None
    if len(set(answer)) != len(answer):
        return None
    given = set(answer)
    return list(answer) + [i for i in range(count) if i not in given]


def _apply_ocr(c: Correction, verdict: dict) -> None:
    """Apply the AI's verdict on one OCR correction: lower its confidence if it is not an error, or use the AI's word
    when it is only a small change from the OCR text.
    """
    word = str(verdict.get("w", "")).strip()
    if not verdict.get("err"):
        c.confidence = min(c.confidence, 0.3)
        c.source = "dictionary; AI: probably not an error"
        return
    # guard: the AI may only fix the word, not rewrite it
    if not word or " " in word or Levenshtein.distance(word.lower(), c.original.lower()) > max(
            2, len(c.original) // 3):
        return
    if word == c.replacement:
        c.confidence = max(c.confidence, 0.9)
        c.source = "dictionary; AI agrees"
    else:
        c.replacement = word
        c.source = "ai"
        c.confidence = 0.8
