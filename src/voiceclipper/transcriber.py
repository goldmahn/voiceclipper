from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from faster_whisper import WhisperModel


@dataclass(frozen=True)
class TranscriptSegment:
    text: str
    start: float
    end: float


def transcribe(
    audio_path: Path,
    *,
    model_name: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
) -> list[TranscriptSegment]:
    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    segments, _info = model.transcribe(str(audio_path), word_timestamps=False)

    results: list[TranscriptSegment] = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        results.append(
            TranscriptSegment(
                text=text,
                start=float(segment.start),
                end=float(segment.end),
            )
        )

    return results
