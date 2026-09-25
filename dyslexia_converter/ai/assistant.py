"""Optional AI assistance for cases local rules cannot decide.

Rules:
* Nothing is sent unless the user chose "AI-assisted" mode, entered a key and
  confirmed the privacy notice (``consent_given``).
* Only short snippets around uncertain items are sent, never the whole PDF.
* Answers are cached, so the same content is never sent twice.
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
from .providers import AIError, make_provider

PRIVACY_NOTICE = (
    "Some document content will be sent to the AI provider using your API key.\n\n"
    "Only short snippets around uncertain citations or OCR words are sent - never the whole PDF. "
    "Your AI provider may charge you for this usage, and its own privacy terms apply. "
    "Choose 'Local-only' at any time to keep all content on this device."
)
SYSTEM = ("You help a document-accessibility tool. You never rewrite, summarise or improve text. "
          "You only answer the narrow classification question asked, in JSON.")
CHUNK = 15  # items per request


class ConsentRequired(Exception):
    pass


@dataclass
class UsageEntry:
    task: str
    items: int
    chars_sent: int
    cached: bool
    when: float = field(default_factory=time.time)


class AICache:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or (app_data_dir() / "ai_cache.json")
        try:
            self.data: dict = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self.data = {}

    @staticmethod
    def key(*parts: str) -> str:
        return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()

    def get(self, key: str):
        return self.data.get(key)

    def put(self, key: str, value) -> None:
        self.data[key] = value
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data), encoding="utf-8")
        except OSError:
            pass

    def clear(self) -> None:
        self.data = {}
        try:
            self.path.unlink()
        except OSError:
            pass


class AIAssistant:
    def __init__(self, settings: AISettings, keystore: Optional[KeyStore] = None, cache: Optional[AICache] = None):
        self.settings = settings
        self.keystore = keystore or KeyStore()
        self.cache = cache or AICache()
        self.usage: list[UsageEntry] = []

    # ------------------------------------------------------------------ state
    @property
    def has_key(self) -> bool:
        return bool(self.keystore.get(self.settings.provider))

    @property
    def active(self) -> bool:
        return self.settings.mode == "ai_assisted" and self.has_key

    def _provider(self):
        if self.settings.mode != "ai_assisted":
            raise ConsentRequired("AI is switched off (Local-only mode).")
        if not self.settings.consent_given:
            raise ConsentRequired(PRIVACY_NOTICE)
        key = self.keystore.get(self.settings.provider)
        if not key:
            raise AIError("No API key entered. Add one in AI Settings.")
        return make_provider(self.settings.provider, key, self.settings.model or None), key

    def _ask(self, task: str, prompt: str, schema: dict, cache_parts: list[str]) -> dict:
        ck = AICache.key(task, self.settings.provider, self.settings.model, *cache_parts)
        hit = self.cache.get(ck)
        if hit is not None:
            self.usage.append(UsageEntry(task, len(cache_parts), 0, True))
            return hit
        provider, key = self._provider()
        try:
            result = provider.complete_json(SYSTEM, prompt, schema)
        except AIError:
            raise
        except Exception as e:  # never leak the key through unexpected errors
            raise AIError(redact(f"AI request failed: {type(e).__name__}", key)) from None
        self.usage.append(UsageEntry(task, len(cache_parts), len(prompt), False))
        self.cache.put(ck, result)
        return result

    # ------------------------------------------------------------------ tasks
    def classify_citations(self, candidates: list[tuple[str, str, str]],
                           progress: Optional[Callable[[str, float], None]] = None) -> dict[str, bool]:
        """``candidates``: (key, citation_text, context). Returns key -> is_citation."""
        schema = {"type": "object", "additionalProperties": False, "required": ["results"],
                  "properties": {"results": {"type": "array", "items": {
                      "type": "object", "additionalProperties": False, "required": ["id", "is_citation"],
                      "properties": {"id": {"type": "integer"}, "is_citation": {"type": "boolean"}}}}}}
        decisions: dict[str, bool] = {}
        for start in range(0, len(candidates), CHUNK):
            chunk = candidates[start:start + CHUNK]
            if progress:
                progress("Asking AI about uncertain citations", start / max(1, len(candidates)))
            lines = [f"{i}. candidate: {c[1]!r}\n   context: {c[2]!r}" for i, c in enumerate(chunk)]
            prompt = ("For each numbered candidate, decide whether the parenthesised text is a bibliographic "
                      "in-text citation (author/year reference to a source), as opposed to other parenthetical "
                      "content such as an explanation, statistic or date.\n\n" + "\n".join(lines))
            res = self._ask("citations", prompt, schema, [c[1] + "|" + c[2] for c in chunk])
            for r in res.get("results", []):
                i = r.get("id")
                if isinstance(i, int) and 0 <= i < len(chunk):
                    decisions[chunk[i][0]] = bool(r.get("is_citation"))
        return decisions

    def review_ocr_words(self, items: list[tuple[Correction, str]],
                         progress: Optional[Callable[[str, float], None]] = None) -> None:
        """Give a second opinion on uncertain OCR corrections (updates them in place).

        ``items``: (correction, context snippet). The AI may agree, propose a
        different word, or say the word is correct. Proposals stay pending.
        """
        schema = {"type": "object", "additionalProperties": False, "required": ["results"],
                  "properties": {"results": {"type": "array", "items": {
                      "type": "object", "additionalProperties": False,
                      "required": ["id", "is_ocr_error", "correct_word"],
                      "properties": {"id": {"type": "integer"}, "is_ocr_error": {"type": "boolean"},
                                     "correct_word": {"type": "string"}}}}}}
        for start in range(0, len(items), CHUNK):
            chunk = items[start:start + CHUNK]
            if progress:
                progress("Asking AI about uncertain OCR words", start / max(1, len(items)))
            lines = [f"{i}. word: {c.original!r}  suggested: {c.replacement!r}\n   context: {ctx!r}"
                     for i, (c, ctx) in enumerate(chunk)]
            prompt = ("These words come from OCR of a scanned academic document. For each numbered word decide "
                      "whether it is an OCR recognition error. If it is, give the intended word (only that one "
                      "word, same language, no rephrasing). If the word is a correct name, term or abbreviation, "
                      "set is_ocr_error to false and repeat the word.\n\n" + "\n".join(lines))
            res = self._ask("ocr", prompt, schema, [c.original + "|" + ctx for c, ctx in chunk])
            for r in res.get("results", []):
                i = r.get("id")
                if not (isinstance(i, int) and 0 <= i < len(chunk)):
                    continue
                c = chunk[i][0]
                word = str(r.get("correct_word", "")).strip()
                if not r.get("is_ocr_error"):
                    c.confidence = min(c.confidence, 0.3)
                    c.source = "dictionary; AI: probably not an error"
                    continue
                # guard: the AI may only fix the word, not rewrite it
                if not word or " " in word or Levenshtein.distance(word.lower(), c.original.lower()) > max(
                        2, len(c.original) // 3):
                    continue
                if word == c.replacement:
                    c.confidence = max(c.confidence, 0.9)
                    c.source = "dictionary; AI agrees"
                else:
                    c.replacement = word
                    c.source = "ai"
                    c.confidence = 0.8
