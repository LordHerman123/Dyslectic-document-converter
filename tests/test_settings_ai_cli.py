import json

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
    model = "fake-model"

    def __init__(self, answer):
        self.answer = answer

    def complete_json(self, system, prompt, schema, max_tokens=1024, answer_hint=""):
        from dyslexia_converter.ai.providers import Reply

        FakeProvider.calls += 1
        FakeProvider.last_prompt = prompt
        FakeProvider.last_system = system
        FakeProvider.last_max_tokens = max_tokens
        return Reply(self.answer, json.dumps(self.answer), 120, 8, 100)


def make_assistant(isolated_home, answer, monkeypatch, mode="ai_assisted", consent=True):
    ks = KeyStore()
    ks._keyring = False
    ks.set("mistral", "test-key-000000000")
    FakeProvider.calls = 0
    monkeypatch.setattr(assistant_mod, "make_provider", lambda *a, **k: FakeProvider(answer))
    return AIAssistant(AISettings(mode=mode, consent_given=consent), ks)


def cite(text, citation, key=None):
    i = text.index(citation)
    return (key or "author_date:" + citation, text, i, i + len(citation))


def test_ai_requires_mode_and_consent(isolated_home, monkeypatch):
    a = make_assistant(isolated_home, {"c": []}, monkeypatch, mode="local_only")
    with pytest.raises(ConsentRequired):
        a.classify_citations([cite("as shown (x, 2020) here", "(x, 2020)")])
    a = make_assistant(isolated_home, {"c": []}, monkeypatch, consent=False)
    with pytest.raises(ConsentRequired):
        a.classify_citations([cite("as shown (x, 2020) here", "(x, 2020)")])
    assert FakeProvider.calls == 0


def test_ai_citations_cached_per_item_minimal_and_logged(isolated_home, monkeypatch):
    a = make_assistant(isolated_home, {"c": [0]}, monkeypatch)
    text = ("A very long paragraph that goes on and on about many things before the point where it says, "
            "as argued (boyd and Crawford, 2012) data changes research, and then it continues for a long "
            "while with mail to jan.jansen@example.org or a call to +31 6 1234 5678 about the results.")
    cands = [cite(text, "(boyd and Crawford, 2012)")]
    assert a.classify_citations(cands) == {"author_date:(boyd and Crawford, 2012)": True}
    assert a.classify_citations(cands) == {"author_date:(boyd and Crawford, 2012)": True}
    assert FakeProvider.calls == 1  # second answer came from the cache
    sent = FakeProvider.last_prompt
    assert "[[(boyd and Crawford, 2012)]]" in sent
    assert "A very long paragraph" not in sent and "jan.jansen" not in sent  # a few words only
    assert len(sent) < 160
    # the fixed part carries worked examples (few-shot)
    assert "Examples" in FakeProvider.last_system and "Answer:" in FakeProvider.last_system
    # a new candidate: only that one is sent, not the cached one again
    more = cands + [cite("the data (Laney, 2001) show", "(Laney, 2001)")]
    a.classify_citations(more)
    assert FakeProvider.calls == 2 and "Laney" in FakeProvider.last_prompt and "boyd" not in FakeProvider.last_prompt
    entries = a.log.entries()
    assert len(entries) == 2 and entries[0].items == 1 and "boyd" in entries[0].prompt
    assert entries[0].input_tokens == 120 and entries[0].cached_tokens == 100
    assert "test-key" not in a.log.as_text()


def test_ai_ocr_cannot_rewrite(isolated_home, monkeypatch):
    c1 = Correction("c1", "b", 4, 12, "reserach", "research", 0.6)
    c2 = Correction("c2", "b", 0, 4, "Tlie", "Die", 0.5)
    c3 = Correction("c3", "b", 4, 11, "Kildare", "Kilmore", 0.5)
    answer = {"f": [{"i": 0, "w": "research"}, {"i": 1, "w": "a completely different phrase"}]}
    a = make_assistant(isolated_home, answer, monkeypatch)
    a.review_ocr_words([(c1, "The reserach suggests", 4, 12), (c2, "Tlie results", 0, 4),
                        (c3, "Co. Kildare, Ireland", 4, 11)])
    assert c1.confidence >= 0.9 and c1.status == "pending"  # AI agrees, user still decides
    assert c2.replacement == "Die"  # rewrite attempt rejected
    assert c3.confidence <= 0.3  # not listed: the AI thinks the word is correct
    assert "suggested: research | The [[reserach]] suggests" in FakeProvider.last_prompt


def test_session_run_ai_sends_only_uncertain_citations(paper, isolated_home, monkeypatch):
    a = make_assistant(isolated_home, {"c": [0]}, monkeypatch)
    session = pipeline.load(paper)
    preview = session.ai_preview(a, FormatSettings(move_citations=True))
    assert len(preview) == 1 and "Miller" in preview[0].prompt and FakeProvider.calls == 0
    summary = session.run_ai(a, FormatSettings(move_citations=True))
    assert "1 uncertain citation" in summary  # "(see Miller, 2018, for the procedure)"
    assert "Miller" in FakeProvider.last_prompt and "Smith, 2020" not in FakeProvider.last_prompt
    assert session.ai_preview(a, FormatSettings(move_citations=True)) == []  # answered: nothing left to send


def test_privacy_masking():
    from dyslexia_converter.ai.privacy import mask, window
    out = mask("Mail j.doe@uni.nl, see https://x.org/a?b=1, call +31 6 1234 5678, IBAN NL91ABNA0417164300, "
               "war (1914-1918) and (Smith, 2019), n = 42")
    assert "j.doe" not in out and "x.org" not in out and "1234" not in out and "0417164300" not in out
    assert "(1914-1918)" in out and "(Smith, 2019)" in out and "n = 42" in out
    text = "one two three four five six seven eight nine ten (Kim, 2020) a b c d e f g h"
    i = text.index("(Kim")
    assert window(text, i, i + 11, before=3, after=2) == "…eight nine ten [[(Kim, 2020)]] a b…"


def test_privacy_log_keeps_errors_trims_and_skips_damaged_lines(isolated_home, monkeypatch):
    from dyslexia_converter.ai import log as log_mod
    from dyslexia_converter.ai.log import LogEntry, RequestLog
    from dyslexia_converter.ai.providers import AIError

    class Failing:
        model = "fake-model"

        def complete_json(self, *a, **k):
            raise RuntimeError("boom sk-ant-should-not-leak-123456")

    a = make_assistant(isolated_home, {"c": []}, monkeypatch)
    monkeypatch.setattr(assistant_mod, "make_provider", lambda *x, **k: Failing())
    with pytest.raises(AIError):
        a.classify_citations([cite("as shown (x, 2020) here", "(x, 2020)")])
    (entry,) = a.log.entries()
    assert entry.error and "boom" not in entry.error and "[[(x, 2020)]]" in entry.prompt  # sent, so logged
    assert "sk-ant" not in a.log.path.read_text(encoding="utf-8")
    # a damaged line (e.g. the app was closed mid-write) is skipped, not fatal
    with a.log.path.open("a", encoding="utf-8") as f:
        f.write('{"task": "ocr", "provider"\n')
    assert len(a.log.entries()) == 1
    monkeypatch.setattr(log_mod, "MAX_ENTRIES", 5)
    log = RequestLog(a.log.path)
    for i in range(9):
        log.add(LogEntry("ocr", "p", "m", 1, "sys", f"prompt {i}"))
    assert [e.prompt for e in log.entries()] == [f"prompt {i}" for i in range(4, 9)]
    text = log.as_text()
    assert "--- document snippets sent\nprompt 8" in text and "--- instructions and examples sent\nsys" in text
    log.clear()
    assert log.entries() == [] and log.as_text() == ""
    log.clear()  # clearing twice is fine


def test_duplicate_snippets_are_sent_once_but_answer_every_item(isolated_home, monkeypatch):
    a = make_assistant(isolated_home, {"c": [0]}, monkeypatch)
    text = "as shown (Lee, 2019) before"
    got = a.classify_citations([cite(text, "(Lee, 2019)", "k1"), cite(text, "(Lee, 2019)", "k2")])
    assert got == {"k1": True, "k2": True}
    assert FakeProvider.last_prompt.count("Lee") == 1 and a.log.entries()[0].items == 1


def test_weird_snippets_survive_masking():
    from dyslexia_converter.ai.privacy import mask, window
    assert mask("") == ""
    assert window("(Kim, 2020)", 0, 11) == "[[(Kim, 2020)]]"  # the item is the whole text
    # a DOI link inside the citation is masked, the author and year stay
    out = window("see (Kim, 2020, https://doi.org/10.1000/xyz123) here", 4, 47)
    assert "doi.org" not in out and "Kim, 2020" in out and out.startswith("see [[")
    # page ranges, ISBN-less years and 'et al.' are not personal data
    assert mask("(Smith et al., 2019, pp. 12-15)") == "(Smith et al., 2019, pp. 12-15)"
    # newlines and tabs never break the one-line-per-item format
    assert "\n" not in window("a\nb\t(X, 2001)\nc", 4, 13)


def test_cli_converts_and_refuses_overwrite(paper, tmp_path, capsys):
    out = tmp_path / "out.pdf"
    assert cli.main([str(paper), "-o", str(out), "--preset", "Spacious", "--bold-start"]) == 0
    assert out.read_bytes().startswith(b"%PDF")
    assert cli.main([str(paper), "-o", str(paper)]) == 2


def test_mistral_provider_request_and_errors(monkeypatch):
    import httpx

    from dyslexia_converter.ai.providers import AIError, make_provider

    sent = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.update(url=url, body=json, headers=headers)
        content = '{"results": [{"id": 0, "is_citation": true}]}'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    p = make_provider("mistral", "secret-mistral-key")
    assert p.model == "mistral-small-latest"
    reply = p.complete_json("sys", "question", {"type": "object"}, 300, 'Answer with JSON only: {"c": [ids]}')
    assert reply.data == {"results": [{"id": 0, "is_citation": True}]}
    assert sent["body"]["max_tokens"] == 300 and sent["body"]["messages"][0] == {"role": "system", "content": "sys"}
    assert sent["url"] == "https://api.mistral.ai/v1/chat/completions"
    assert sent["headers"]["Authorization"] == "Bearer secret-mistral-key"
    assert sent["body"]["response_format"] == {"type": "json_object"}

    monkeypatch.setattr(httpx, "post", lambda *a, **k: httpx.Response(401, text="bad secret-mistral-key"))
    with pytest.raises(AIError) as err:
        p.complete_json("sys", "q", {})
    assert "secret-mistral-key" not in str(err.value)


def test_mistral_is_default_provider():
    assert AISettings().provider == "mistral"


def test_anthropic_request_caches_instructions_and_reports_usage(monkeypatch):
    import sys
    import types

    from dyslexia_converter.ai.providers import make_provider

    sent = {}

    class Usage:
        input_tokens, output_tokens, cache_read_input_tokens, cache_creation_input_tokens = 40, 9, 600, 0

    class Resp:
        stop_reason = "end_turn"
        usage = Usage()
        content = [types.SimpleNamespace(type="text", text='{"c": [1]}')]

    class Messages:
        def create(self, **kw):
            sent.update(kw)
            return Resp()

    class Client:
        def __init__(self, **kw):
            self.messages = Messages()
            self.beta = types.SimpleNamespace(messages=Messages())

    fake = types.SimpleNamespace(Anthropic=Client, AuthenticationError=KeyError, RateLimitError=KeyError,
                                 APIStatusError=KeyError, APIConnectionError=KeyError)
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    p = make_provider("anthropic", "sk-test", "claude-sonnet-5")
    reply = p.complete_json("instructions and examples", "0: …", {"type": "object"}, 200)
    assert reply.data == {"c": [1]} and reply.input_tokens == 640 and reply.cached_tokens == 600
    assert sent["system"] == [{"type": "text", "text": "instructions and examples",
                               "cache_control": {"type": "ephemeral"}}]
    assert sent["output_config"]["effort"] == "low" and sent["output_config"]["format"]["type"] == "json_schema"
    assert sent["messages"] == [{"role": "user", "content": "0: …"}]


def test_gemini_request_has_no_thinking_and_reports_usage(monkeypatch):
    import httpx

    from dyslexia_converter.ai.providers import make_provider

    sent = {}

    def fake_post(url, json=None, headers=None, timeout=None):
        sent.update(body=json)
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": '{"f": []}'}]}}],
            "usageMetadata": {"promptTokenCount": 700, "candidatesTokenCount": 5, "cachedContentTokenCount": 512}})

    monkeypatch.setattr(httpx, "post", fake_post)
    reply = make_provider("gemini", "g-key").complete_json("sys", "0: …", {}, 150, "hint")
    assert reply.data == {"f": []} and reply.input_tokens == 700 and reply.cached_tokens == 512
    cfg = sent["body"]["generationConfig"]
    assert cfg["thinkingConfig"] == {"thinkingBudget": 0} and cfg["maxOutputTokens"] == 150
    assert sent["body"]["systemInstruction"]["parts"][0]["text"] == "sys"
