from __future__ import annotations

from pathlib import Path

from voiceclipper.detector import SpeakerSegment


def diarize(audio_path: Path, hf_token: str) -> list[SpeakerSegment]:
    try:
        from pyannote.audio import Pipeline
    except ImportError:
        raise ImportError(
            "pyannote.audio is required for speaker diarization. "
            "Install it with: pip install 'voiceclipper[diarize]'"
        ) from None

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
    )
    diarization = pipeline(str(audio_path))

    segments: list[SpeakerSegment] = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        segments.append(SpeakerSegment(speaker=speaker, start=turn.start, end=turn.end))
    return segments
