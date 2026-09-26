"""AI providers. Each provider answers one small JSON question at a time.

The user supplies their own API key. Their provider may charge for usage.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional

from .keystore import redact


class AIError(Exception):
    """A provider error with any API key removed from the message."""


@dataclass
class Reply:
    """A provider's answer and what the request cost in tokens."""
    data: dict
    text: str = ""
    input_tokens: int = 0  # all input, including the part served from the provider's prompt cache
    output_tokens: int = 0
    cached_tokens: int = 0


def _parse(text: str) -> dict:
    try:
        data = json.loads(text)
    except ValueError as e:
        raise AIError("The AI returned an unreadable answer; the local result was kept.") from e
    if not isinstance(data, dict):
        raise AIError("The AI returned an unreadable answer; the local result was kept.")
    return data


class AIProvider:
    name = ""
    label = ""
    models: list[str] = []
    default_model = ""
    note = ""

    def __init__(self, api_key: str, model: str = ""):
        self._key = api_key
        self.model = model or self.default_model

    def complete_json(self, system: str, prompt: str, schema: dict, max_tokens: int = 1024,
                      answer_hint: str = "") -> Reply:
        """Ask one question. ``system`` is the fixed part (instructions and examples, the same for every
        request of a task, so it can be cached); ``prompt`` holds this request's items."""
        raise NotImplementedError


class AnthropicProvider(AIProvider):
    name = "anthropic"
    label = "Anthropic (Claude)"
    models = ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"]
    default_model = "claude-opus-5"
    note = "Paid API (billed by Anthropic per token). Smaller models cost less."

    def complete_json(self, system: str, prompt: str, schema: dict, max_tokens: int = 1024,
                      answer_hint: str = "") -> Reply:
        try:
            import anthropic
        except ImportError as e:
            raise AIError("The 'anthropic' package is not installed (pip install anthropic).") from e
        client = anthropic.Anthropic(api_key=self._key, max_retries=2, timeout=60.0)
        output_config: dict = {"format": {"type": "json_schema", "schema": schema}}
        if not self.model.startswith("claude-haiku"):
            output_config["effort"] = "low"  # small classification tasks: little thinking needed
        # the instructions and examples are the same for every request: cached, later requests pay ~10% for them
        system_blocks = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
        # room for thinking plus the short JSON answer; only the tokens actually used are billed
        kwargs = dict(model=self.model, max_tokens=max(1024, max_tokens), system=system_blocks,
                      messages=[{"role": "user", "content": prompt}], output_config=output_config)
        try:
            if self.model in ("claude-opus-5", "claude-fable-5-1"):
                # server-side fallback if a request is declined by a safety classifier
                resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"],
                                                   fallbacks="default", **kwargs)
            else:
                resp = client.messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise AIError("The API key was rejected by Anthropic. Check the key in AI Settings.") from e
        except anthropic.RateLimitError as e:
            raise AIError("Anthropic rate limit reached. Try again later.") from e
        except anthropic.APIStatusError as e:
            raise AIError(redact(f"Anthropic API error ({e.status_code}).", self._key)) from e
        except anthropic.APIConnectionError as e:
            raise AIError("Could not reach the Anthropic API. Check your internet connection.") from e
        if resp.stop_reason == "refusal":
            raise AIError("The AI declined this request; the local result was kept.")
        text = next((b.text for b in resp.content if getattr(b, "type", "") == "text"), "")
        u = resp.usage
        cached = (getattr(u, "cache_read_input_tokens", 0) or 0)
        written = (getattr(u, "cache_creation_input_tokens", 0) or 0)
        return Reply(_parse(text), text, (u.input_tokens or 0) + cached + written, u.output_tokens or 0, cached)


class GeminiProvider(AIProvider):
    name = "gemini"
    label = "Google Gemini"
    models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    default_model = "gemini-2.5-flash"
    note = "Has a free tier with rate limits (check Google's current terms). Free-tier data may be used by Google."

    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def complete_json(self, system: str, prompt: str, schema: dict, max_tokens: int = 1024,
                      answer_hint: str = "") -> Reply:
        import httpx

        body = {
            # the fixed instructions first: Gemini reuses a repeated prompt start at a lower price
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt + "\n\n" + answer_hint}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0,
                                 "maxOutputTokens": max_tokens,
                                 # no thinking for these small questions: thinking tokens are billed as output
                                 "thinkingConfig": {"thinkingBudget": 0}},
        }
        try:
            r = httpx.post(self.URL.format(model=self.model), json=body, timeout=60.0,
                           headers={"x-goog-api-key": self._key, "content-type": "application/json"})
        except httpx.HTTPError as e:
            raise AIError("Could not reach the Gemini API. Check your internet connection.") from e
        if r.status_code in (401, 403):
            raise AIError("The API key was rejected by Google. Check the key in AI Settings.")
        if r.status_code == 429:
            raise AIError("Gemini rate limit / free-tier quota reached. Try again later.")
        if r.status_code >= 400:
            raise AIError(redact(f"Gemini API error ({r.status_code}).", self._key))
        try:
            data = r.json()
            text = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, ValueError) as e:
            raise AIError("The AI returned an unreadable answer; the local result was kept.") from e
        usage = data.get("usageMetadata", {}) or {}
        out = (usage.get("candidatesTokenCount", 0) or 0) + (usage.get("thoughtsTokenCount", 0) or 0)
        return Reply(_parse(text), text, usage.get("promptTokenCount", 0) or 0, out,
                     usage.get("cachedContentTokenCount", 0) or 0)


class MistralProvider(AIProvider):
    """Mistral AI chat-completions API (La Plateforme). The free "Experiment" plan works with the small models."""

    name = "mistral"
    label = "Mistral AI"
    models = ["mistral-small-latest", "ministral-8b-latest", "open-mistral-nemo", "mistral-large-latest"]
    default_model = "mistral-small-latest"
    note = ("Free 'Experiment' plan available at console.mistral.ai (rate-limited; check Mistral's current "
            "terms - free-plan data may be used to improve their models).")

    URL = "https://api.mistral.ai/v1/chat/completions"

    def complete_json(self, system: str, prompt: str, schema: dict, max_tokens: int = 1024,
                      answer_hint: str = "") -> Reply:
        import httpx

        body = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt + "\n\n" + answer_hint},
            ],
        }
        try:
            r = httpx.post(self.URL, json=body, timeout=60.0,
                           headers={"Authorization": f"Bearer {self._key}", "Content-Type": "application/json",
                                    "Accept": "application/json"})
        except httpx.HTTPError as e:
            raise AIError("Could not reach the Mistral API. Check your internet connection.") from e
        if r.status_code in (401, 403):
            raise AIError("The API key was rejected by Mistral. Check the key in AI Settings.")
        if r.status_code == 429:
            raise AIError("Mistral rate limit / free-plan quota reached. Try again in a minute.")
        if r.status_code >= 400:
            raise AIError(redact(f"Mistral API error ({r.status_code}).", self._key))
        try:
            data = r.json()
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise AIError("The AI returned an unreadable answer; the local result was kept.") from e
        usage = data.get("usage", {}) or {}
        return Reply(_parse(text), text, usage.get("prompt_tokens", 0) or 0, usage.get("completion_tokens", 0) or 0)


PROVIDERS: dict[str, type[AIProvider]] = {p.name: p for p in (MistralProvider, AnthropicProvider, GeminiProvider)}


def make_provider(name: str, api_key: str, model: Optional[str] = None) -> AIProvider:
    cls = PROVIDERS.get(name)
    if cls is None:
        raise AIError(f"Unknown AI provider: {name}")
    return cls(api_key, model or "")
