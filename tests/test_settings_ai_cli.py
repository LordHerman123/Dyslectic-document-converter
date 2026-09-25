
import pytest

from dyslexia_converter import cli, pipeline
from dyslexia_converter.ai import assistant as assistant_mod
from dyslexia_converter.ai.assistant import AIAssistant, ConsentRequired
from dyslexia_converter.ai.keystore import KeyStore, redact
from dyslexia_converter.model import Correction
from dyslexia_converter.settings import AISettings, FormatSettings, SettingsStore


def test_settings_persist_and_reset(isolated_home):
    store = SettingsStore()
    s = FormatSettings(font="OpenDyslexic", font_size=14, reading_width=13, bold_word_start=True)
    store.save_format(s)
    assert SettingsStore().load_format() == s
    assert SettingsStore().preset("My Settings") == s
    assert store.reset_format() == FormatSettings()
    assert not store.has_saved_format()


def test_api_key_never_in_settings_file(isolated_home):
    store = SettingsStore()
    ks = KeyStore()
    ks._keyring = False
    ks.set("anthropic", "sk-ant-secret-key-123456789")
    store.save_ai(AISettings(mode="ai_assisted", consent_given=True))
    assert "sk-ant" not in store.path.read_text()
    assert ks.get("anthropic") == "sk-ant-secret-key-123456789"
    ks.remove("anthropic")
    assert ks.get("anthropic") is None


def test_redaction():
    msg = "error for key sk-ant-abcdefghijk123 with header x-api-key: sk-ant-zzzzzzzzzz9"
    out = redact(msg, "sk-ant-abcdefghijk123")
    assert "sk-ant" not in out


class FakeProvider:
    calls = 0

    def __init__(self, answer):
        self.answer = answer

    def complete_json(self, system, prompt, schema):
        FakeProvider.calls += 1
        FakeProvider.last_prompt = prompt
        return self.answer


def make_assistant(isolated_home, answer, monkeypatch, mode="ai_assisted", consent=True):
    ks = KeyStore()
    ks._keyring = False
    ks.set("anthropic", "sk-ant-test-000000000")
    FakeProvider.calls = 0
    monkeypatch.setattr(assistant_mod, "make_provider", lambda *a, **k: FakeProvider(answer))
    return AIAssistant(AISettings(mode=mode, consent_given=consent), ks)


def test_ai_requires_mode_and_consent(isolated_home, monkeypatch):
    a = make_assistant(isolated_home, {"results": []}, monkeypatch, mode="local_only")
    with pytest.raises(ConsentRequired):
        a.classify_citations([("k", "(x, 2020)", "ctx")])
    a = make_assistant(isolated_home, {"results": []}, monkeypatch, consent=False)
    with pytest.raises(ConsentRequired):
        a.classify_citations([("k", "(x, 2020)", "ctx")])
    assert FakeProvider.calls == 0


def test_ai_citations_cached_and_minimal(isolated_home, monkeypatch):
    a = make_assistant(isolated_home, {"results": [{"id": 0, "is_citation": True}]}, monkeypatch)
    cands = [("author_date:(boyd and Crawford, 2012)", "(boyd and Crawford, 2012)", "short context")]
    assert a.classify_citations(cands) == {"author_date:(boyd and Crawford, 2012)": True}
    assert a.classify_citations(cands) == {"author_date:(boyd and Crawford, 2012)": True}
    assert FakeProvider.calls == 1  # second answer came from the cache
    assert len(FakeProvider.last_prompt) < 600


def test_ai_ocr_cannot_rewrite(isolated_home, monkeypatch):
    c1 = Correction("c1", "b", 0, 8, "reserach", "research", 0.6)
    c2 = Correction("c2", "b", 0, 5, "Tlie", "Die", 0.5)
    answer = {"results": [{"id": 0, "is_ocr_error": True, "correct_word": "research"},
                          {"id": 1, "is_ocr_error": True, "correct_word": "a completely different phrase"}]}
    a = make_assistant(isolated_home, answer, monkeypatch)
    a.review_ocr_words([(c1, "The reserach suggests"), (c2, "Tlie results")])
    assert c1.confidence >= 0.9 and c1.status == "pending"  # AI agrees, user still decides
    assert c2.replacement == "Die"  # rewrite attempt rejected


def test_session_run_ai_sends_only_uncertain_citations(paper, isolated_home, monkeypatch):
    a = make_assistant(isolated_home, {"results": [{"id": 0, "is_citation": True}]}, monkeypatch)
    session = pipeline.load(paper)
    summary = session.run_ai(a, FormatSettings(move_citations=True))
    assert "1 uncertain citation" in summary  # "(see Miller, 2018, for the procedure)"
    assert "Miller" in FakeProvider.last_prompt and "Smith, 2020" not in FakeProvider.last_prompt


def test_cli_converts_and_refuses_overwrite(paper, tmp_path, capsys):
    out = tmp_path / "out.pdf"
    assert cli.main([str(paper), "-o", str(out), "--preset", "Spacious", "--bold-start"]) == 0
    assert out.read_bytes().startswith(b"%PDF")
    assert cli.main([str(paper), "-o", str(paper)]) == 2
