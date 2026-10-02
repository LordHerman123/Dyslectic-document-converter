"""Saving text as audio: the whole document, some pages or a selection, spoken by the reading-aloud voice into
one MP3 file to listen to anywhere (a phone, a car, on a walk).

The text is spoken in parts of a few sentences with the same voice and speed as reading aloud; the parts are
joined with a short pause between them and encoded to MP3 as they come, so a long document never has to fit
in memory as raw sound. Everything happens on this device.
"""
from __future__ import annotations

import io
import re
import wave
from typing import Callable, Iterable, Optional

import numpy as np

PART_CHARS = 600  # text spoken per part: whole sentences, about this long
PAUSE = 0.35  # seconds of quiet between parts
KBPS = 64  # MP3 bit rate: clear speech, about 30 MB per hour


class AudioExportError(Exception):
    """The audio could not be made (no voice can save sound, the MP3 encoder is missing, or it was cancelled)."""


def supported() -> bool:
    """Whether MP3 files can be made here (the encoder is installed)."""
    try:
        import lameenc  # noqa: F401
    except Exception:
        return False
    return True


def parts(sentences: Iterable[str], limit: int = PART_CHARS) -> list[str]:
    """Sentences grouped into parts of about ``limit`` characters (a longer sentence is a part of its own)."""
    out: list[str] = []
    cur = ""
    for s in sentences:
        s = " ".join(s.split())
        if not s:
            continue
        if cur and len(cur) + 1 + len(s) > limit:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}" if cur else s
    if cur:
        out.append(cur)
    return out


def split_sentences(text: str) -> list[str]:
    """A selection's text in sentences (after . ! ? followed by a space)."""
    return [s for s in re.split(r"(?<=[.!?])\s+", " ".join(text.split())) if s]


def _pcm(wav: bytes) -> tuple[np.ndarray, int]:
    """WAV bytes as mono 16-bit samples and their rate."""
    with wave.open(io.BytesIO(wav)) as w:
        rate, channels, width = w.getframerate(), w.getnchannels(), w.getsampwidth()
        data = w.readframes(w.getnframes())
    if width == 2:
        x = np.frombuffer(data, dtype="<i2").astype(np.float32)
    elif width == 1:
        x = (np.frombuffer(data, dtype=np.uint8).astype(np.float32) - 128.0) * 256.0
    elif width == 4:
        x = np.frombuffer(data, dtype="<i4").astype(np.float32) / 65536.0
    else:
        raise AudioExportError(f"unsupported sound format ({width * 8}-bit)")
    if channels > 1:
        x = x.reshape(-1, channels).mean(axis=1)
    return x, rate


def _resample(x: np.ndarray, rate: int, target: int) -> np.ndarray:
    """Samples at ``rate`` made into samples at ``target`` (linear interpolation; enough for speech)."""
    if rate == target or len(x) == 0:
        return x
    n = int(round(len(x) * target / rate))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def export_mp3(texts: list[str], render: Callable[[list[str]], Iterable[bytes]],
               progress: Callable[[float], None] = lambda f: None,
               cancelled: Callable[[], bool] = lambda: False, kbps: int = KBPS) -> bytes:
    """Speak ``texts`` (parts of a few sentences) with ``render`` (texts -> WAV bytes of each, e.g.
    :meth:`speech.Speaker.render_many`) into one MP3. ``progress`` gets 0..1; raises :class:`AudioExportError`
    when cancelled or nothing could be spoken."""
    import lameenc

    out = bytearray()
    enc: Optional[lameenc.Encoder] = None
    rate = 0
    total = max(1, sum(len(t) for t in texts))
    done = 0
    for text, wav in zip(texts, render(texts)):
        if cancelled():
            raise AudioExportError("cancelled")
        x, r = _pcm(wav)
        if enc is None:
            rate = r if r in (8000, 11025, 12000, 16000, 22050, 24000, 32000, 44100, 48000) else 22050
            enc = lameenc.Encoder()
            enc.set_bit_rate(kbps)
            enc.set_in_sample_rate(rate)
            enc.set_channels(1)
            enc.set_quality(2)
        x = _resample(x, r, rate)
        x = np.concatenate([x, np.zeros(int(PAUSE * rate), dtype=np.float32)])
        out += enc.encode(np.clip(x, -32768, 32767).astype("<i2").tobytes())
        done += len(text)
        progress(min(1.0, done / total))
    if enc is None:
        raise AudioExportError("nothing to read")
    out += enc.flush()
    return bytes(out)


def minutes(texts: list[str], speed: float = 1.0, wpm: int = 165) -> float:
    """About how long the audio will be, in minutes."""
    words = sum(len(t.split()) for t in texts)
    return words / (wpm * max(0.4, speed))
