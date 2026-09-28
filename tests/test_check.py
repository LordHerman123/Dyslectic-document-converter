"""The whole-document AI check: findings are checked against the text, fixes happen only when chosen, and every
fix can be undone. The AI is a stand-in with a fixed answer."""
import re

import pytest

from dyslexia_converter.model import Block, BlockKind, Document, PageInfo, TableData

TEXTS = {
    "t": (BlockKind.TITLE, "The price of knowledge"),
    "p1": (BlockKind.PARAGRAPH, "Publishers say that their costs are high. The num ber of journals has grown fast. "
                                "1 2 | S C I E N C E | V O L 7 Yet prices still vary."),
    "p2": (BlockKind.PARAGRAPH, "2. Methods We asked forty publishers and recieved twelve answers by mail."),
    "h": (BlockKind.HEADING, "Figure 2"),
    "p3": (BlockKind.PARAGRAPH, "Most of them said that the new rnodel was cheaper forthe small journals."),
    "p4": (BlockKind.PARAGRAPH, "Prices are hidden by the non- Germany; and the Trust in London, have joined. "
                                "disclosure agreements. Write to jane@example.org for data."),
    "f": (BlockKind.PARAGRAPH, "© 2013 Example Publishers Limited. All rights reserved"),
    "r": (BlockKind.REFERENCE, "Smith, J. (2020). A reference that is never sent. Journal 3, 1-9."),
}
ANSWER = [
    {"b": 1, "t": "word", "q": "num ber", "w": "number", "r": "broken word"},
    {"b": 1, "t": "furniture", "q": "1 2 | S C I E N C E | V O L 7", "w": "", "r": "footer"},
    {"b": 2, "t": "heading", "q": "2. Methods", "w": "", "r": "heading in paragraph"},
    {"b": 2, "t": "word", "q": "recieved", "w": "received", "r": "spelling"},  # the author's own: dropped
    {"b": 3, "t": "not_heading", "q": "Figure 2", "w": "", "r": "figure label"},
    {"b": 4, "t": "scan", "q": "rnodel", "w": "model", "r": "misread"},
    {"b": 4, "t": "word", "q": "forthe", "w": "for the", "r": "run together"},
    {"b": 5, "t": "order", "q": "Germany; and the Trust in London, have joined.", "w": "", "r": "other column"},
    {"b": 5, "t": "word", "q": "non- Germany", "w": "non-Germany", "r": "hyphen"},  # letters kept: allowed
    {"b": 6, "t": "furniture", "q": "© 2013 Example Publishers Limited. All rights reserved", "w": "", "r": "x"},
    {"b": 3, "t": "word", "q": "not in the text", "w": "x", "r": "made up"},  # not there: dropped
    {"b": 99, "t": "word", "q": "num ber", "w": "number", "r": "unknown block"},  # dropped
    {"b": 1, "t": "rewrite", "q": "Publishers say", "w": "They say", "r": "unknown type"},  # dropped
]


def document(ocr_block: str = "p3") -> Document:
    doc = Document("x.pdf", pages=[PageInfo(0, 595, 842, "text", source_page=0),
                                   PageInfo(1, 595, 842, "text", source_page=1)])
    for n, (bid, (kind, text)) in enumerate(TEXTS.items()):
        doc.blocks.append(Block(bid, kind, text, page=0 if n < 3 else 1, level=2 if kind == BlockKind.HEADING else 0,
                                source="ocr" if bid == ocr_block else "text"))
    doc.blocks.append(Block("tab", BlockKind.TABLE, "", page=1, table=TableData([["a", "secret table"]])))
    return doc


class Answering:
    """Stands in for the AI: gives a fixed answer and remembers what it was sent."""
    model = "stand-in"
    prompts: list = []

    def __init__(self, answer):
        self.answer = answer

    def complete_json(self, system, prompt, schema, max_tokens=1024, answer_hint=""):
        from dyslexia_converter.ai.providers import Reply

        Answering.prompts.append(prompt)
        return Reply({"f": self.answer}, "{}", 100, 10)


@pytest.fixture
def checked(isolated_home, monkeypatch):
    """A session with the check run on it: (session, assistant)."""
    from dyslexia_converter import pipeline
    from dyslexia_converter.ai import assistant as assistant_mod
    from dyslexia_converter.ai.keystore import KeyStore
    from dyslexia_converter.settings import AISettings
    from dyslexia_converter.transform.spelling import CustomWords

    session = pipeline.Session(document(), CustomWords())
    ks = KeyStore()
    ks._keyring = False
    ks.set("mistral", "test-key-000000000")
    Answering.prompts = []
    monkeypatch.setattr(assistant_mod, "make_provider", lambda *a, **k: Answering(ANSWER))
    ai = assistant_mod.AIAssistant(AISettings(mode="ai_assisted", consent_given=True), ks)
    session.run_check(ai)
    return session, ai


def text_of(session) -> str:
    from dyslexia_converter.settings import FormatSettings

    return " | ".join(f"{it.kind}:{it.text}" for it in session.compose(FormatSettings()).items if it.text)


def kinds(session):
    return {(f.kind, f.quote) for f in session.check_findings}


def test_only_findings_that_hold_are_kept(checked):
    session, _ = checked
    found = kinds(session)
    assert ("word", "num ber") in found and ("scan", "rnodel") in found and ("word", "forthe") in found
    assert ("heading", "2. Methods") in found and ("not_heading", "Figure 2") in found
    assert ("order", "Germany; and the Trust in London, have joined.") in found
    assert not any(q in ("recieved", "not in the text", "Publishers say") for _, q in found)
    assert len(session.check_findings) == 9


def test_what_is_sent(checked):
    prompt = "\n".join(Answering.prompts)
    assert "jane@example.org" not in prompt and "[email]" in prompt  # masked
    assert "never sent" not in prompt and "secret table" not in prompt  # references and tables stay
    assert re.search(r"^4 \| P scan \| p2 \| Most of them", prompt, re.M)  # scanned text is marked


def test_nothing_changes_until_a_fix_is_chosen_and_every_fix_undoes(checked):
    session, _ = checked
    before = text_of(session)
    assert "num ber" in before
    for f in session.check_findings:
        session.fix_finding(f.id)
    after = text_of(session)
    assert "The number of journals" in after and "S C I E N C E" not in after and "grown fast. Yet prices" in after
    assert "heading:2. Methods" in after and "paragraph:We asked forty" in after
    assert "paragraph:Figure 2" in after and "the new model was cheaper for the small" in after
    assert "All rights reserved" not in after and "recieved" in after  # the author's spelling stays
    assert "Germany; and the Trust" in after  # text in the wrong place is only shown
    assert not next(f for f in session.check_findings if f.kind == "order").applied
    session.undo_all_findings()
    assert text_of(session) == before


def test_fix_all_safe_ones_only_joins_and_splits_words(checked):
    session, _ = checked
    n = session.fix_safe_findings()
    fixed = {f.quote for f in session.check_findings if f.applied}
    assert fixed == {"num ber", "forthe", "non- Germany"} and n == 3
    assert "rnodel" in text_of(session)  # a letter change is never made without the reader choosing it


def test_a_letter_change_outside_scans_is_not_allowed(isolated_home):
    from dyslexia_converter import check

    doc = document(ocr_block="none")
    part = check.parts(doc)[0]
    found = check.findings_from(ANSWER, part, doc, doc)
    assert not any(f.quote == "rnodel" for f in found)  # not a scan: the author's word stays


def test_checking_again_sends_nothing_new_and_keeps_fixes(checked):
    session, ai = checked
    f = next(f for f in session.check_findings if f.quote == "num ber")
    session.fix_finding(f.id)
    sent = len(Answering.prompts)
    requests, words = session.check_preview(ai)
    assert words > 50
    session.run_check(ai)
    assert session.finding(f.id).applied
    assert len(Answering.prompts) - sent == len(requests)  # only text changed by the fix is sent again


def test_a_fix_on_text_the_user_edited_is_refused(checked):
    session, _ = checked
    f = next(f for f in session.check_findings if f.quote == "forthe")
    b = session.document.block(f.block_id)
    from dyslexia_converter.model import Correction

    session.document.corrections.append(Correction("user-1", b.id, f.start, f.end, b.text[f.start:f.end], "for  the",
                                                   1.0, "accepted", "user"))
    assert not session.fix_finding(f.id)


def test_a_refused_key_stops_the_check(isolated_home, monkeypatch):
    from dyslexia_converter import pipeline
    from dyslexia_converter.ai import assistant as assistant_mod
    from dyslexia_converter.ai.keystore import KeyStore
    from dyslexia_converter.ai.providers import AIError
    from dyslexia_converter.settings import AISettings
    from dyslexia_converter.transform.spelling import CustomWords

    class Refusing:
        model = "stand-in"

        def complete_json(self, *a, **k):
            raise AIError("The API key was rejected by Mistral. Check the key in AI Settings.")

    ks = KeyStore()
    ks._keyring = False
    ks.set("mistral", "test-key-000000000")
    monkeypatch.setattr(assistant_mod, "make_provider", lambda *a, **k: Refusing())
    ai = assistant_mod.AIAssistant(AISettings(mode="ai_assisted", consent_given=True), ks)
    session = pipeline.Session(document(), CustomWords())
    with pytest.raises(AIError):
        session.run_check(ai)
    assert session.check_findings == []
    assert ai.log.entries()[-1].error


def test_no_check_without_consent_or_key(isolated_home):
    from dyslexia_converter import pipeline
    from dyslexia_converter.ai.assistant import AIAssistant, ConsentRequired
    from dyslexia_converter.ai.keystore import KeyStore
    from dyslexia_converter.ai.providers import AIError
    from dyslexia_converter.settings import AISettings
    from dyslexia_converter.transform.spelling import CustomWords

    ks = KeyStore()
    ks._keyring = False
    session = pipeline.Session(document(), CustomWords())
    with pytest.raises(ConsentRequired):
        session.run_check(AIAssistant(AISettings(mode="local_only"), ks))
    with pytest.raises(AIError):
        session.run_check(AIAssistant(AISettings(mode="ai_assisted", consent_given=True), ks))
