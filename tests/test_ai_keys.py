"""Named API keys: adding, choosing, removing, older saved keys, environment keys, and the connection check."""
import json

from dyslexia_converter.ai import keys
from dyslexia_converter.ai.assistant import AIAssistant
from dyslexia_converter.ai.keystore import KeyStore
from dyslexia_converter.ai.providers import AIError, Reply
from dyslexia_converter.settings import AISettings, SettingsStore


def store():
    ks = KeyStore()
    ks._keyring = False
    return ks


def test_add_use_and_remove_named_keys(isolated_home):
    ks, s = store(), AISettings()
    uni = keys.add(s, ks, "Uni", "mistral", "mistral-secret-111111")
    home = keys.add(s, ks, "", "anthropic", "sk-ant-secret-2222222")
    assert home.name == "Anthropic (Claude)"  # no name given: the provider's name
    assert s.active_key == uni.id and s.provider == "mistral"  # the first key is the one in use
    assert keys.secret(s, ks) == "mistral-secret-111111"
    s.model = "mistral-large-latest"
    keys.use(s, home.id, "anthropic")
    assert s.provider == "anthropic" and s.model == ""  # another provider starts with its default model
    assert keys.secret(s, ks) == "sk-ant-secret-2222222"
    keys.remove(s, ks, home.id)  # removing the key in use: the next one takes over, the secret is gone
    assert s.active_key == uni.id and s.provider == "mistral"
    assert ks.get(home.id, env=False) is None
    keys.remove(s, ks, uni.id)
    assert s.active_key == "" and not keys.entries(s, ks)


def test_named_keys_are_saved_without_secrets(isolated_home):
    ks, s = store(), AISettings()
    keys.add(s, ks, "Uni", "mistral", "mistral-secret-111111")
    SettingsStore().save_ai(s)
    text = SettingsStore().path.read_text()
    assert "mistral-secret" not in text and "Uni" in text
    again = SettingsStore().load_ai()
    assert again.keys[0]["name"] == "Uni" and again.active_key == s.active_key
    assert AIAssistant(again, ks).has_key


def test_key_from_older_version_becomes_named_key(isolated_home):
    ks, s = store(), AISettings(provider="gemini")
    ks.set("gemini", "AIza-old-key-1234567890")
    assert keys.migrate(s, ks)
    assert s.keys == [{"id": "gemini", "name": "Google Gemini", "provider": "gemini"}]
    assert s.active_key == "gemini" and keys.secret(s, ks) == "AIza-old-key-1234567890"
    assert not keys.migrate(s, ks)  # only once


def test_environment_key_is_listed_used_but_not_stored(isolated_home, monkeypatch):
    monkeypatch.setenv("MISTRAL_API_KEY", "env-mistral-key-99999")
    ks, s = store(), AISettings()
    [e] = keys.entries(s, ks)
    assert e.from_env and e.provider == "mistral"
    assert AIAssistant(s, ks).has_key  # nothing chosen yet: the provider's key, as before
    keys.use(s, e.id, e.provider)
    assert keys.secret(s, ks) == "env-mistral-key-99999"
    assert "env-mistral" not in json.dumps(s.keys) and not ks.path.exists()


class Answering:
    """A provider that answers the check, or fails like a rejected key."""
    def __init__(self, fail=None):
        self.fail, self.model = fail, "tiny-model"

    def complete_json(self, system, prompt, schema, max_tokens=1024, answer_hint=""):
        assert prompt == "test" and max_tokens <= 64  # never document text, a tiny answer
        if self.fail:
            raise self.fail
        return Reply({"ok": True}, '{"ok": true}', 20, 4)


def test_connection_check_is_logged_and_hides_the_key(isolated_home, monkeypatch):
    a = AIAssistant(AISettings(), store())  # works before AI is switched on: no document text is sent
    monkeypatch.setattr(keys, "make_provider", lambda *args, **kw: Answering())
    ok = a.check_key("mistral", "mistral-secret-111111")
    assert ok.ok and ok.seconds >= 0
    monkeypatch.setattr(keys, "make_provider", lambda *args, **kw: Answering(
        AIError("The API key was rejected by Mistral. Check the key in AI Settings.")))
    bad = a.check_key("mistral", "mistral-secret-111111")
    assert not bad.ok and "rejected" in bad.message
    monkeypatch.setattr(keys, "make_provider", lambda *args, **kw: Answering(RuntimeError("mistral-secret-111111")))
    odd = a.check_key("mistral", "mistral-secret-111111")
    assert not odd.ok and "mistral-secret" not in odd.message
    entries = a.log.entries()
    assert [e.task for e in entries[-3:]] == ["check"] * 3 and entries[-3].prompt == "test"
    assert all("mistral-secret" not in (e.error + e.answer + e.prompt) for e in entries)


def test_tail_shows_only_the_end():
    assert keys.tail("abcdefghij4Fz6") == "4Fz6" and keys.tail("short") == ""
