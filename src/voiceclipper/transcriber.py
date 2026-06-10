from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from faster_whisper import WhisperModel


@dataclass(frozen=True)
class WordTimestamp:
    word: str
    start: float
    end: float


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    start: float
    end: float
    words: tuple[WordTimestamp, ...] = field(default=())


def transcribe(
    audio_path: Path,
    *,
    model_name: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
) -> list[TranscriptSegment]:
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(str(audio_path), word_timestamps=True)

    results: list[TranscriptSegment] = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue

        words: tuple[WordTimestamp, ...] = ()
        if segment.words:
            words = tuple(
                WordTimestamp(word=w.word.strip(), start=w.start, end=w.end)
                for w in segment.words
                if w.word.strip()
            )

        results.append(
            TranscriptSegment(
                text=text,
                start=float(segment.start),
                end=float(segment.end),
                words=words,
            )
        )

    return results
