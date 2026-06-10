from __future__ import annotations

from pathlib import Path

from pydub import AudioSegment

from voiceclipper.boundaries import clip_boundaries
from voiceclipper.detector import PhraseMatch
from voiceclipper.transcriber import TranscriptWord


def _clip_filename(phrase_id: str, occurrence_index: int) -> str:
    if occurrence_index == 0:
        return f"{phrase_id}.wav"
    return f"{phrase_id}{occurrence_index}.wav"


def export_clips(
    audio_path: Path,
    words: list[TranscriptWord],
    matches: list[PhraseMatch],
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    audio = AudioSegment.from_file(audio_path)
    audio_length_ms = len(audio)

    exported: list[Path] = []
    occurrence_counts: dict[str, int] = {}

    for match in matches:
        clip_start, clip_end = clip_boundaries(
            words,
            match.start_word_index,
            match.end_word_index,
            match.phrase.padding_ms,
            audio_length_ms=audio_length_ms,
        )
        clip = audio[clip_start:clip_end]

        occurrence_index = occurrence_counts.get(match.phrase.id, 0)
        occurrence_counts[match.phrase.id] = occurrence_index + 1

        destination = output_dir / _clip_filename(match.phrase.id, occurrence_index)
        clip.export(destination, format="wav")
        exported.append(destination)

    return exported
