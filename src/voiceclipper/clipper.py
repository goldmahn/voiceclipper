from __future__ import annotations

from pathlib import Path

from pydub import AudioSegment

from voiceclipper.config import ProcessingConfig
from voiceclipper.detector import PhraseMatch


def export_clips(
    audio_path: Path,
    matches: list[PhraseMatch],
    output_dir: Path,
    processing: ProcessingConfig | None = None,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    audio = AudioSegment.from_file(audio_path)

    chain = None
    if processing is not None:
        from voiceclipper.processor import ProcessingChain
        chain = ProcessingChain(processing)

    exported: list[Path] = []
    for match in matches:
        clip = audio[match.start_ms : match.end_ms]
        if chain is not None:
            clip = chain.process(clip)
        stem = match.phrase.id
        if match.speaker:
            stem = f"{stem}_{match.speaker}"
        destination = output_dir / f"{stem}.wav"
        clip.export(destination, format="wav")
        exported.append(destination)

    return exported
