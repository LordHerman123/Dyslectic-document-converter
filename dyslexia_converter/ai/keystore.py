"""API-key storage.

The key is never hard-coded, never written to settings.json, logs, exported
files or error messages. It is stored in the operating system's credential
store when the optional ``keyring`` package is available; otherwise in a
separate file readable only by the current user.
"""
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

from ..settings import app_data_dir

SERVICE = "dyslexia-converter"
ENV_VARS = {"mistral": "MISTRAL_API_KEY", "anthropic": "ANTHROPIC_API_KEY", "gemini": "GEMINI_API_KEY"}


class KeyStore:
    def __init__(self, directory: Optional[Path] = None):
        self.path = (directory or app_data_dir()) / "api_keys.json"
        try:
            import keyring  # noqa: F401
            self._keyring = True
        except Exception:
            self._keyring = False

    @property
    def backend(self) -> str:
        return "system keychain" if self._keyring else "private file on this device"

    def get(self, provider: str) -> Optional[str]:
        if self._keyring:
            try:
                import keyring
                v = keyring.get_password(SERVICE, provider)
                if v:
                    return v
            except Exception:
                pass
        try:
            v = json.loads(self.path.read_text(encoding="utf-8")).get(provider)
            if v:
                return v
        except (OSError, ValueError):
            pass
        return os.environ.get(ENV_VARS.get(provider, "")) or None

    def set(self, provider: str, key: str) -> None:
        key = key.strip()
        if self._keyring:
            try:
                import keyring
                keyring.set_password(SERVICE, provider, key)
                return
            except Exception:
                pass
        data = self._read_file()
        data[provider] = key
        self._write_file(data)

    def remove(self, provider: str) -> None:
        if self._keyring:
            try:
                import keyring
                keyring.delete_password(SERVICE, provider)
            except Exception:
                pass
        data = self._read_file()
        if provider in data:
            del data[provider]
            self._write_file(data)

    def _read_file(self) -> dict:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def _write_file(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        tmp.replace(self.path)


# ----------------------------------------------------------------------------- redaction

_KEY_PATTERNS = [re.compile(r"sk-ant-[A-Za-z0-9_\-]{8,}"), re.compile(r"AIza[0-9A-Za-z_\-]{20,}"),
                 re.compile(r"(?i)(x-api-key|x-goog-api-key|authorization)[\"']?\s*[:=]\s*[\"']?[^\s\"',}]+")]


def redact(text: str, *secrets: Optional[str]) -> str:
    """Remove API keys from a string (for error messages and logs)."""
    out = str(text)
    for s in secrets:
        if s:
            out = out.replace(s, "[API key hidden]")
    for p in _KEY_PATTERNS:
        out = p.sub("[API key hidden]", out)
    return out


class RedactingFilter(logging.Filter):
    """Logging filter that strips anything that looks like an API key."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = ()
        return True


def install_log_redaction() -> None:
    root = logging.getLogger()
    if not any(isinstance(f, RedactingFilter) for f in root.filters):
        root.addFilter(RedactingFilter())
    for h in root.handlers:
        if not any(isinstance(f, RedactingFilter) for f in h.filters):
            h.addFilter(RedactingFilter())
