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
from .keystore import KeyStore, redact
from .log import LogEntry, RequestLog
from .privacy import window
from .prompts import CITATIONS, OCR, Task, citation_prompt, ocr_prompt
from .providers import AIError, Reply, make_provider

PRIVACY_NOTICE = (
    "Some document content will be sent to the AI provider using your API key.\n\n"
    "Only a few words around each uncertain citation or OCR word are sent - never the whole PDF - and "
    "e-mail addresses, links and long numbers in them are masked. Everything that is sent is listed in the "
    "privacy log in the AI tab. Your AI provider may charge you for this usage, and its own privacy terms "
    "apply. Choose 'Local-only' at any time to keep all content on this device."
)
CHUNK = 30  # items per request: the fixed instructions and examples are shared by more items


class ConsentRequired(Exception):
    """AI was asked for while it is off or the user has not agreed to the privacy notice yet."""
    pass


@dataclass
class UsageEntry:
    """What one AI task used: how many items, how many characters were sent, whether it came from the cache, and the
    tokens.
    """
    task: str
    items: int
    chars_sent: int
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

    @property
    def system(self) -> str:
        """The fixed instructions of the task (the same for every request, so providers can cache them)."""
        return self.task.system

    @property
    def max_tokens(self) -> int:
        """The answer length to allow: a little for the frame plus a fixed amount per snippet."""
        return 64 + self.task.tokens_per_item * len(self.keys)


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
        """Whether an API key is stored for the chosen provider."""
        return bool(self.keystore.get(self.settings.provider))

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
        key = self.keystore.get(self.settings.provider)
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
        self.usage.append(UsageEntry(request.task.name, len(request.keys), entry.chars, False,
                                     reply.input_tokens, reply.output_tokens))
        return reply

    # ------------------------------------------------------------------ tasks
    def classify_citations(self, candidates: list[tuple[str, str, int, int]],
                           progress: Optional[Callable[[str, float], None]] = None) -> dict[str, bool]:
        """Decide for each candidate whether it is a citation. Returns candidate key -> is_citation."""
        requests, decisions = self.plan_citations(candidates)
        if decisions:
            self.usage.append(UsageEntry("citations", len(decisions), 0, True))
        for n, req in enumerate(requests):
            if progress:
                progress("Asking AI about uncertain citations", n / max(1, len(requests)))
            yes = {i for i in self.send(req).data.get("c", []) if isinstance(i, int)}
            values = {ck: i in yes for i, ck in enumerate(req.keys)}
            self.cache.put_many(values)
            for i, keys in enumerate(req.items):
                for key in keys:
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
            self.usage.append(UsageEntry("ocr", len(known), 0, True))
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
