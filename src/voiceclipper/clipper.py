from __future__ import annotations

from pathlib import Path

from pydub import AudioSegment

from voiceclipper.detector import PhraseMatch


def export_clips(
    audio_path: Path,
    matches: list[PhraseMatch],
    output_dir: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    audio = AudioSegment.from_file(audio_path)

    exported: list[Path] = []
    for match in matches:
        clip = audio[match.start_ms : match.end_ms]
        destination = output_dir / f"{match.phrase.id}.wav"
        clip.export(destination, format="wav")
        exported.append(destination)

    return exported
