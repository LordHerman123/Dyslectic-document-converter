"""AI providers. Each provider answers one small JSON question at a time.

The user supplies their own API key. Their provider may charge for usage.
"""
from __future__ import annotations

import json
from typing import Optional

from .keystore import redact


class AIError(Exception):
    """A provider error with any API key removed from the message."""


class AIProvider:
    name = ""
    label = ""
    models: list[str] = []
    default_model = ""
    note = ""

    def __init__(self, api_key: str, model: str = ""):
        self._key = api_key
        self.model = model or self.default_model

    def complete_json(self, system: str, prompt: str, schema: dict) -> dict:
        raise NotImplementedError


class AnthropicProvider(AIProvider):
    name = "anthropic"
    label = "Anthropic (Claude)"
    models = ["claude-opus-5", "claude-sonnet-5", "claude-haiku-4-5"]
    default_model = "claude-opus-5"
    note = "Paid API (billed by Anthropic per token). Smaller models cost less."

    def complete_json(self, system: str, prompt: str, schema: dict) -> dict:
        try:
            import anthropic
        except ImportError as e:
            raise AIError("The 'anthropic' package is not installed (pip install anthropic).") from e
        client = anthropic.Anthropic(api_key=self._key, max_retries=2, timeout=60.0)
        output_config: dict = {"format": {"type": "json_schema", "schema": schema}}
        if not self.model.startswith("claude-haiku"):
            output_config["effort"] = "low"  # tiny classification tasks
        kwargs = dict(model=self.model, max_tokens=2048, system=system,
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
        try:
            return json.loads(text)
        except ValueError as e:
            raise AIError("The AI returned an unreadable answer; the local result was kept.") from e


class GeminiProvider(AIProvider):
    name = "gemini"
    label = "Google Gemini"
    models = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    default_model = "gemini-2.5-flash"
    note = "Has a free tier with rate limits (check Google's current terms). Free-tier data may be used by Google."

    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def complete_json(self, system: str, prompt: str, schema: dict) -> dict:
        import httpx

        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": prompt + "\n\nAnswer with JSON matching this schema: "
                                                     + json.dumps(schema)}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0},
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
            return json.loads(text)
        except (KeyError, IndexError, ValueError) as e:
            raise AIError("The AI returned an unreadable answer; the local result was kept.") from e


PROVIDERS: dict[str, type[AIProvider]] = {p.name: p for p in (AnthropicProvider, GeminiProvider)}


def make_provider(name: str, api_key: str, model: Optional[str] = None) -> AIProvider:
    cls = PROVIDERS.get(name)
    if cls is None:
        raise AIError(f"Unknown AI provider: {name}")
    return cls(api_key, model or "")
