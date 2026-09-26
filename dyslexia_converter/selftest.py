"""Headless self-test for packaged builds.

    DyslexiaConverter.exe --selftest input.pdf output.pdf [log.txt]

Converts one PDF without opening a window and writes a short report. The
release workflow runs this on the finished .exe before publishing it.
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path


def _speech_report() -> str:
    """Whether reading aloud works in this build: a missing module is a packaging error; a computer
    without voices is not."""
    try:
        import pyttsx3  # noqa: F401
        from .speech import Speaker
    except ImportError as e:
        return f"Speech: MISSING MODULE {e.name}"
    sp = Speaker()
    try:
        if sys.platform == "win32":
            import pyttsx3.drivers.sapi5  # noqa: F401  the Windows driver must be in the build
    except ImportError as e:
        return f"Speech: MISSING MODULE {e.name}"
    n = len(sp.voices()) if sp.available() else 0
    report = f"Speech: {'available' if n else 'no voices on this computer'} ({n} voices)"
    if n and sys.platform == "win32":
        report += "\n" + _speak_test()
    elif sp.last_error:
        report += f" - {sp.last_error}"
    return report


def _speak_test() -> str:
    """Speak one sentence into a WAV file with the real Windows voice, as the app would."""
    import tempfile
    import threading

    from .speech import SapiEngine, Sentence, Speaker, Word, WinRtEngine

    with tempfile.TemporaryDirectory() as d:
        wav = Path(d) / "speech.wav"
        words = [Word(w, 0, [(0, 0, 1, 1)]) for w in "The converted text is read aloud.".split()]
        pos = 0
        for w in words:
            w.start, pos = pos, pos + len(w.text) + 1
        heard, done = [], threading.Event()
        modern = None
        try:
            modern = WinRtEngine(play=False)
            voices = modern.getProperty("voices")
        except Exception as e:  # noqa: BLE001
            voices, note = [], f"modern voices unavailable: {e}"
        if voices:  # the engine the app uses on Windows 10/11
            note = "modern voices: " + ", ".join(sorted({v.languages[0] for v in voices if v.languages}))
            sp = Speaker(engine_factory=lambda: modern)
        else:
            sp = Speaker(engine_factory=lambda: SapiEngine(output_wav=str(wav)))
        sp.start([Sentence(words)], 0, on_word=lambda s, w: heard.append(w), on_done=lambda f: done.set())
        done.wait(60)
        if voices:
            wav.write_bytes(modern.last_wav)
        size = wav.stat().st_size if wav.exists() else 0
        if sp.last_error or size < 2000:
            return f"Speech test FAILED: WAV {size} bytes, {sp.last_error}"
        return (f"Speech test: OK, WAV {size} bytes, {len(set(heard))} of {len(words)} words timed; "
                f"{note}")


def run(argv: list[str]) -> int:
    src = Path(argv[0]) if argv else None
    out = Path(argv[1]) if len(argv) > 1 else None
    log = Path(argv[2]) if len(argv) > 2 else (out.with_suffix(".log") if out else Path("selftest.log"))
    lines: list[str] = []
    try:
        from . import __version__, pipeline
        from .extract.ocr import find_tesseract

        lines.append(f"Dyslexia Converter {__version__}")
        lines.append(f"Tesseract: {find_tesseract()}")
        lines.append(_speech_report())
        if src is None or out is None:
            raise SystemExit("usage: --selftest input.pdf output.pdf [log.txt]")
        session = pipeline.load(src)
        doc = session.document
        lines.append(f"PDF type: {doc.pdf_type}; OCR used: {doc.ocr_used}; blocks: {len(doc.blocks)}")
        lines += [f"Warning: {w}" for w in doc.warnings]
        out.write_bytes(session.export("pdf", pipeline.FormatSettings()))
        lines.append(f"Wrote {out} ({out.stat().st_size} bytes)")
        code = 0
    except BaseException:  # the report must always be written
        lines.append(traceback.format_exc())
        code = 1
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if sys.stdout is not None:
        print("\n".join(lines))
    return code
