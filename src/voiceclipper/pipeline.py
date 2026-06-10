from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from faster_whisper import WhisperModel

from voiceclipper.clipper import ExportedClip, export_clips
from voiceclipper.config import ClipJob
from voiceclipper.detector import PhraseMatch, find_phrase_matches
from voiceclipper.ffmpeg_io import probe_duration_ms
from voiceclipper.manifest import SessionManifest, build_manifest, write_manifest
from voiceclipper.transcriber import transcribe
from voiceclipper.transcript_cache import (
    load_transcript_cache,
    save_transcript_cache,
    transcript_cache_path,
)
from voiceclipper.metadata import collect_corpus_metadata
from voiceclipper.postprocess import PostProcessResult, run_postprocess
from voiceclipper.util import sanitize_session_id


@dataclass(frozen=True)
class ClipResult:
    entry: ExportedClip

    @property
    def output_path(self) -> Path:
        return self.entry.output_path


@dataclass(frozen=True)
class PipelineResult:
    session_id: str
    session_dir: Path
    manifest_path: Path
    manifest: SessionManifest
    matches: list[PhraseMatch]
    clips: list[ClipResult]
    missing_phrase_ids: list[str]
    skipped: bool = False
    postprocess: PostProcessResult | None = None


def resolve_session_paths(job: ClipJob) -> tuple[str, Path, Path]:
    session_id = sanitize_session_id(job.session_id or job.input_path.stem)
    session_dir = job.output_dir / session_id
    clips_dir = session_dir / "clips"
    return session_id, session_dir, clips_dir


def run_clip_job(job: ClipJob, *, model: WhisperModel | None = None) -> PipelineResult:
    if not job.input_path.exists():
        raise FileNotFoundError(f"Input audio not found: {job.input_path}")

    session_id, session_dir, clips_dir = resolve_session_paths(job)
    corpus_metadata = collect_corpus_metadata(
        session_id=session_id,
        source_path=job.input_path,
        metadata_path=job.metadata_path,
        interactive=job.interactive_metadata,
    )
    cache_path = transcript_cache_path(session_dir)

    words = load_transcript_cache(cache_path)
    if words is None:
        if job.manifest_only:
            raise FileNotFoundError(
                f"Transcript cache not found for manifest-only run: {cache_path}"
            )
        words = transcribe(
            job.input_path,
            model_name=job.whisper_model,
            device=job.device,
            compute_type=job.compute_type,
            model=model,
        )
        save_transcript_cache(cache_path, words)

    matches = find_phrase_matches(job.phrases, words)

    exported = export_clips(
        job.input_path,
        words,
        matches,
        clips_dir,
        session_id,
    )
    clips = [ClipResult(entry=item) for item in exported]

    matched_ids = {match.phrase.id for match in matches}
    missing = [phrase.id for phrase in job.phrases if phrase.id not in matched_ids]

    source_duration_ms = probe_duration_ms(job.input_path)
    manifest = build_manifest(
        session_id=session_id,
        source_path=job.input_path,
        source_duration_ms=source_duration_ms,
        phrases_path=job.phrases_path,
        phrases_count=len(job.phrases),
        whisper_model=job.whisper_model,
        device=job.device,
        word_count=len(words),
        missing_phrase_ids=missing,
        clips=[item.entry for item in exported],
        session_metadata=dict(corpus_metadata.session),
        speaker_metadata=dict(corpus_metadata.speaker),
    )

    manifest_path = session_dir / "manifest.json"
    if job.write_manifest:
        write_manifest(manifest_path, manifest)

    postprocess: PostProcessResult | None = None
    if job.run_postprocess and clips:
        postprocess = run_postprocess(
            session_dir,
            clips_dir,
            manifest_path=manifest_path,
            target_lufs=job.target_lufs,
            leading_pad_ms=job.leading_pad_ms,
            trailing_pad_ms=job.trailing_pad_ms,
            fade_ms=job.fade_ms,
        )

    return PipelineResult(
        session_id=session_id,
        session_dir=session_dir,
        manifest_path=manifest_path,
        manifest=manifest,
        matches=matches,
        clips=clips,
        missing_phrase_ids=missing,
        postprocess=postprocess,
    )
