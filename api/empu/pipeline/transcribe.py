"""Mode B (D10): local faster-whisper word timestamps as a time anchor for Muse speech terms.

Muse keeps the spelling; only t_start/t_end move. Transcripts are cached by media hash + model.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from faster_whisper import WhisperModel
from rapidfuzz import fuzz

from empu.cache import sha256_file
from empu.enums import Source, TimeSource
from empu.pipeline.merge import AbsOccurrence
from empu.text import normalize

SPOKEN_MIN_RATIO = 60.0


@dataclass(frozen=True)
class Word:
    t_start: float
    t_end: float
    text: str


Transcriber = Callable[[Path], list[Word]]


def whisper_transcriber(model_name: str = "small", language: str = "id") -> Transcriber:
    model: WhisperModel | None = None

    def run(path: Path) -> list[Word]:
        nonlocal model
        if model is None:
            model = WhisperModel(model_name, device="auto", compute_type="int8")
        segments, _info = model.transcribe(
            str(path),
            language=language,
            word_timestamps=True,
            vad_filter=True,
            beam_size=5,
        )
        return [
            Word(round(w.start, 2), round(w.end, 2), w.word.strip())
            for seg in segments
            for w in (seg.words or [])
            if w.word.strip()
        ]

    return run


def transcribe_cached(
    media: Path, transcriber: Transcriber, *, cache_root: Path, model_name: str
) -> list[Word]:
    path = Path(cache_root) / f"{sha256_file(media)}__{model_name}.json"
    if path.exists():
        return [Word(**w) for w in json.loads(path.read_text())]
    words = transcriber(Path(media))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(w) for w in words], ensure_ascii=False))
    return words


def _text(words: list[Word]) -> str:
    return normalize(" ".join(w.text for w in words))


def _best_window(
    quote: str,
    words: list[Word],
    center: float,
    window_s: float,
    *,
    n_words: int,
) -> tuple[float, int, int]:
    n = max(1, n_words)
    best, best_dist = (0.0, -1, -1), float("inf")
    for i, w in enumerate(words):
        dist = abs(w.t_start - center)
        if dist > window_s:
            continue
        j = i + n
        if j > len(words):
            continue
        score = fuzz.partial_ratio(quote, _text(words[i:j]))
        if score > best[0] or (score == best[0] and dist < best_dist):
            best, best_dist = (score, i, j), dist
    return best


def _spoken_span(spoken: str, span: list[Word]) -> tuple[int, int] | None:
    k = max(1, len(spoken.split()))
    best: tuple[float, int, int] = (0.0, 0, 0)
    for size in (k, k + 1):
        for i in range(0, max(0, len(span) - size) + 1):
            score = fuzz.ratio(spoken, _text(span[i : i + size]))
            if score > best[0]:
                best = (score, i, min(len(span), i + size))
    return (best[1], best[2]) if best[0] >= SPOKEN_MIN_RATIO else None


def realign(
    occs: list[AbsOccurrence],
    words: list[Word],
    *,
    window_s: float = 30.0,
    threshold: float = 80.0,
) -> list[AbsOccurrence]:
    if not words:
        return occs
    for o in occs:
        if o.muse.source is not Source.speech:
            continue
        quote = normalize(o.muse.evidence_quote) or normalize(o.muse.spoken)
        if not quote:
            continue
        spoken_norm = normalize(o.muse.spoken)
        n_words = max(1, len(quote.split()), len(spoken_norm.split()) + 1 if spoken_norm else 0)
        score, i, j = _best_window(quote, words, o.t_start, window_s, n_words=n_words)
        if score < threshold or i < 0:
            continue
        span = words[i:j]
        sub = _spoken_span(normalize(o.muse.spoken), span)
        first, last = (span[sub[0]], span[sub[1] - 1]) if sub else (span[0], span[-1])
        o.t_start, o.t_end = first.t_start, last.t_end
        o.time_source, o.asr_score = TimeSource.asr, round(score, 1)
    return occs
