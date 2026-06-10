from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from faster_whisper import WhisperModel


@dataclass(frozen=True)
class TranscriptWord:
    text: str
    start: float
    end: float


def transcribe(
    audio_path: Path,
    *,
    model_name: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    model: WhisperModel | None = None,
) -> list[TranscriptWord]:
    whisper_model = model or WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, _info = whisper_model.transcribe(str(audio_path), word_timestamps=True)

    words: list[TranscriptWord] = []
    for segment in segments:
        if segment.words is None:
            continue
        for word in segment.words:
            text = word.word.strip()
            if not text:
                continue
            words.append(
                TranscriptWord(
                    text=text,
                    start=float(word.start),
                    end=float(word.end),
                )
            )

    return words
