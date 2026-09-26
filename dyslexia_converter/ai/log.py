"""A log, kept on this device only, of everything that was sent to an AI provider.

Each entry holds the exact text that left the device (the fixed instructions with their examples, and the
document snippets), the answer that came back, and the size of the request. API keys are never part of a
request's text, so they never appear here. The log can be viewed, saved and cleared in the app.
"""
from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from ..settings import app_data_dir

MAX_ENTRIES = 500


@dataclass
class LogEntry:
    task: str
    provider: str
    model: str
    items: int
    system: str  # instructions and examples, the same for every request of this task
    prompt: str  # the document snippets of this request
    answer: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0  # part of the input the provider served from its prompt cache
    error: str = ""
    when: float = field(default_factory=time.time)

    @property
    def chars(self) -> int:
        return len(self.system) + len(self.prompt)

    @property
    def document_chars(self) -> int:
        """Characters of document text in this request (the snippets, not the fixed instructions)."""
        return len(self.prompt)


class RequestLog:
    def __init__(self, path: Optional[Path] = None):
        self.path = path or (app_data_dir() / "ai_requests.jsonl")

    def add(self, entry: LogEntry) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
            self._trim()
        except OSError:
            pass

    def entries(self) -> list[LogEntry]:
        out: list[LogEntry] = []
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return out
        known = set(LogEntry.__dataclass_fields__)
        for line in lines:
            try:
                data = json.loads(line)
                out.append(LogEntry(**{k: v for k, v in data.items() if k in known}))
            except (ValueError, TypeError):
                continue
        return out

    def clear(self) -> None:
        try:
            self.path.unlink()
        except OSError:
            pass

    def _trim(self) -> None:
        lines = self.path.read_text(encoding="utf-8").splitlines()
        if len(lines) > MAX_ENTRIES:
            self.path.write_text("\n".join(lines[-MAX_ENTRIES:]) + "\n", encoding="utf-8")

    def as_text(self) -> str:
        """The whole log as readable text (for saving or sharing)."""
        parts = []
        for e in self.entries():
            stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(e.when))
            parts.append(
                f"=== {stamp}  {e.provider} / {e.model}  task: {e.task}  items: {e.items}\n"
                f"characters sent: {e.chars} (document text: {e.document_chars})  tokens in: {e.input_tokens}"
                f" (from cache: {e.cached_tokens})  tokens out: {e.output_tokens}\n"
                f"--- instructions and examples sent\n{e.system}\n"
                f"--- document snippets sent\n{e.prompt}\n"
                f"--- answer received\n{e.answer or e.error}\n")
        return "\n".join(parts)
