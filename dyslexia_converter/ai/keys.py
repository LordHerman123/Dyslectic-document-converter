"""The user's named API keys.

Each key has a name the user chose, a provider and an id. The names and providers are kept in the AI settings;
the secret itself only in the key store, under the id. One key is "in use": AI requests are sent with it.
A key in a provider's environment variable (such as MISTRAL_API_KEY) is listed too, but never stored.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Optional

from ..settings import AISettings
from .keystore import KeyStore
from .providers import PROVIDERS, make_provider

CHECK_SYSTEM = 'This is a connection check. Answer with JSON only: {"ok": true}'
CHECK_PROMPT = "test"
CHECK_SCHEMA = {"type": "object", "additionalProperties": False, "required": ["ok"],
                "properties": {"ok": {"type": "boolean"}}}


@dataclass
class KeyEntry:
    """One key as the AI settings list it: id (where the secret is stored), name, provider, and whether it comes
    from an environment variable (then it cannot be removed in the app)."""
    id: str
    name: str
    provider: str
    from_env: bool = False


@dataclass
class CheckResult:
    """The outcome of a connection check: whether it worked, the message to show, and how long it took."""
    ok: bool
    message: str
    seconds: float = 0.0
    when: float = 0.0


def entries(settings: AISettings, store: KeyStore) -> list[KeyEntry]:
    """Every key the user can pick: the named keys, then keys found in environment variables."""
    out = [KeyEntry(k["id"], k.get("name") or k["id"], k["provider"]) for k in settings.keys
           if k.get("provider") in PROVIDERS]
    ids = {e.id for e in out}
    for name, cls in PROVIDERS.items():
        if name not in ids and store.env_key(name):
            out.append(KeyEntry(name, cls.label, name, from_env=True))
    return out


def migrate(settings: AISettings, store: KeyStore) -> bool:
    """Keys saved by older versions (one per provider, stored under the provider's name) become named keys.
    Returns whether the settings changed."""
    if settings.keys:
        return False
    for name, cls in PROVIDERS.items():
        if store.get(name, env=False):
            settings.keys.append({"id": name, "name": cls.label, "provider": name})
    if settings.keys and not settings.active_key:
        mine = [k for k in settings.keys if k["provider"] == settings.provider]
        settings.active_key = (mine or settings.keys)[0]["id"]
        settings.provider = (mine or settings.keys)[0]["provider"]
    return bool(settings.keys)


def add(settings: AISettings, store: KeyStore, name: str, provider: str, secret: str) -> KeyEntry:
    """Store a new key. The first key (or one added while none is in use) becomes the key in use."""
    kid = f"{provider}-{uuid.uuid4().hex[:8]}"
    store.set(kid, secret)
    name = name.strip() or PROVIDERS[provider].label
    settings.keys.append({"id": kid, "name": name, "provider": provider})
    if not settings.active_key or not any(k["id"] == settings.active_key for k in settings.keys[:-1]):
        use(settings, kid, provider)
    return KeyEntry(kid, name, provider)


def remove(settings: AISettings, store: KeyStore, kid: str) -> None:
    """Delete a named key (the secret too). When it was in use, the next key takes over."""
    store.remove(kid)
    settings.keys = [k for k in settings.keys if k["id"] != kid]
    if settings.active_key == kid:
        rest = entries(settings, store)
        if rest:
            use(settings, rest[0].id, rest[0].provider)
        else:
            settings.active_key = ""


def use(settings: AISettings, kid: str, provider: str) -> None:
    """Make a key the one AI requests use; a different provider starts with its default model."""
    if provider != settings.provider:
        settings.model = ""
    settings.active_key, settings.provider = kid, provider


def secret(settings: AISettings, store: KeyStore, kid: Optional[str] = None) -> Optional[str]:
    """The secret of a key (the key in use by default). Without named keys, the provider's key as before."""
    kid = kid if kid is not None else settings.active_key
    if kid:
        return store.get(kid, env=kid in PROVIDERS)
    return store.get(settings.provider)


def tail(value: Optional[str]) -> str:
    """The last four characters of a key, to tell keys apart without showing them."""
    return value[-4:] if value and len(value) > 8 else ""


def check(provider: str, value: str, model: str = "") -> tuple[CheckResult, str, str]:
    """Send the tiny connection check (the word "test", never document text) with a key.

    Returns the result and the model and answer, for the privacy log. Errors come back as a failed result.
    """
    from .providers import AIError

    start = time.monotonic()
    client = make_provider(provider, value, model or None)
    try:
        reply = client.complete_json(CHECK_SYSTEM, CHECK_PROMPT, CHECK_SCHEMA, 64, "")
    except AIError as e:
        return CheckResult(False, str(e), time.monotonic() - start, time.time()), client.model, ""
    except Exception as e:  # anything unexpected: say what kind, never the key
        return (CheckResult(False, f"The connection check failed ({type(e).__name__}).", time.monotonic() - start,
                            time.time()), client.model, "")
    return CheckResult(True, "", time.monotonic() - start, time.time()), client.model, reply.text
