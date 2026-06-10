from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from voiceclipper.clipper import export_clips
from voiceclipper.config import ClipJob
from voiceclipper.detector import PhraseMatch, SpeakerSegment, find_phrase_matches
from voiceclipper.transcriber import transcribe


@dataclass(frozen=True)
class ClipResult:
    match: PhraseMatch
    output_path: Path


@dataclass(frozen=True)
class PipelineResult:
    matches: list[PhraseMatch]
    clips: list[ClipResult]
    missing_phrase_ids: list[str]


def run_clip_job(job: ClipJob) -> PipelineResult:
    if not job.input_path.exists():
        raise FileNotFoundError(f"Input audio not found: {job.input_path}")

    segments = transcribe(
        job.input_path,
        model_name=job.whisper_model,
        device=job.device,
        compute_type=job.compute_type,
    )

    diarization: list[SpeakerSegment] | None = None
    if job.diarize:
        if not job.hf_token:
            raise ValueError("--hf-token is required when --diarize is set")
        from voiceclipper.diarizer import diarize
        diarization = diarize(job.input_path, job.hf_token)

    matches = find_phrase_matches(
        job.phrases,
        segments,
        diarization=diarization,
        min_confidence=job.min_confidence,
    )

    exported_paths = export_clips(job.input_path, matches, job.output_dir, job.processing)
    clips = [
        ClipResult(match=match, output_path=path)
        for match, path in zip(matches, exported_paths, strict=True)
    ]

    matched_ids = {match.phrase.id for match in matches}
    missing = [phrase.id for phrase in job.phrases if phrase.id not in matched_ids]

    return PipelineResult(matches=matches, clips=clips, missing_phrase_ids=missing)
