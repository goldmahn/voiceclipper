from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from voiceclipper.boundaries import clip_boundaries
from voiceclipper.detector import PhraseMatch
from voiceclipper.ffmpeg_io import export_clip_ffmpeg, probe_duration_ms
from voiceclipper.manifest import ClipEntry, clip_filename
from voiceclipper.metadata import content_metadata_to_dict
from voiceclipper.transcriber import TranscriptWord

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class ExportedClip:
    entry: ClipEntry
    output_path: Path


def export_clips(
    audio_path: Path,
    words: list[TranscriptWord],
    matches: list[PhraseMatch],
    clips_dir: Path,
    session_id: str,
) -> list[ExportedClip]:
    clips_dir.mkdir(parents=True, exist_ok=True)
    audio_length_ms = probe_duration_ms(audio_path)

    exported: list[ExportedClip] = []
    occurrence_counts: dict[str, int] = {}

    for sequence, match in enumerate(matches, start=1):
        clip_start, clip_end = clip_boundaries(
            words,
            match.start_word_index,
            match.end_word_index,
            match.phrase.padding_ms,
            audio_length_ms=audio_length_ms,
        )

        occurrence_index = occurrence_counts.get(match.phrase.id, 0)
        occurrence_counts[match.phrase.id] = occurrence_index + 1
        filename = clip_filename(match.phrase.id, occurrence_index)
        output_path = clips_dir / filename

        export_clip_ffmpeg(audio_path, output_path, clip_start, clip_end)

        content_metadata = content_metadata_to_dict(match.phrase.content_metadata or {})

        entry = ClipEntry(
            clip_id=f"{session_id}_{sequence:06d}",
            phrase_id=match.phrase.id,
            occurrence_index=occurrence_index,
            filename=filename,
            path=f"clips/{filename}",
            matched_text=match.matched_text,
            start_ms=clip_start,
            end_ms=clip_end,
            duration_ms=clip_end - clip_start,
            word_start_index=match.start_word_index,
            word_end_index=match.end_word_index,
            phrase_text=match.phrase.text,
            start=round(clip_start / 1000, 3),
            end=round(clip_end / 1000, 3),
            content_metadata=content_metadata,
        )
        exported.append(ExportedClip(entry=entry, output_path=output_path))

    return exported
