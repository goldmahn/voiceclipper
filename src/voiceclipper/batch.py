from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from faster_whisper import WhisperModel

from voiceclipper.config import ClipJob
from voiceclipper.manifest import manifest_is_current
from voiceclipper.pipeline import run_clip_job
from voiceclipper.util import sanitize_session_id


@dataclass(frozen=True)
class BatchSessionResult:
    input_path: Path
    session_id: str
    status: str
    clips_exported: int = 0
    message: str = ""


@dataclass(frozen=True)
class BatchResult:
    sessions: list[BatchSessionResult]
    processed: int
    skipped: int
    failed: int


def discover_audio_files(input_dir: Path) -> list[Path]:
    patterns = ("*.mp3", "*.MP3", "*.wav", "*.WAV", "*.m4a", "*.M4A", "*.flac", "*.FLAC")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(input_dir.glob(pattern))
    return sorted({path.resolve() for path in files})


def append_index_record(index_path: Path, record: dict[str, object]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=False) + "\n")


def run_batch(
    input_dir: Path,
    output_dir: Path,
    phrases_path: Path,
    phrases: list,
    *,
    whisper_model: str = "base",
    device: str = "cpu",
    compute_type: str = "int8",
    skip_existing: bool = False,
    fail_fast: bool = False,
    index_path: Path | None = None,
    manifest_only: bool = False,
    run_postprocess: bool = True,
    target_lufs: float = -23.0,
    leading_pad_ms: int = 75,
    trailing_pad_ms: int = 75,
    fade_ms: int = 3,
    metadata_path: Path | None = None,
    interactive_metadata: bool = False,
) -> BatchResult:
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Batch input is not a directory: {input_dir}")

    audio_files = discover_audio_files(input_dir)
    if not audio_files:
        raise FileNotFoundError(f"No audio files found in {input_dir}")

    model = None if manifest_only else WhisperModel(whisper_model, device=device, compute_type=compute_type)

    sessions: list[BatchSessionResult] = []
    processed = 0
    skipped = 0
    failed = 0

    for audio_path in audio_files:
        session_id = sanitize_session_id(audio_path.stem)
        session_dir = output_dir / session_id
        manifest_path = session_dir / "manifest.json"

        if skip_existing and manifest_is_current(manifest_path, audio_path, phrases_path):
            skipped += 1
            sessions.append(
                BatchSessionResult(
                    input_path=audio_path,
                    session_id=session_id,
                    status="skipped",
                    message="manifest exists with matching source hash",
                )
            )
            continue

        job = ClipJob(
            input_path=audio_path,
            output_dir=output_dir,
            phrases_path=phrases_path,
            phrases=phrases,
            session_id=session_id,
            whisper_model=whisper_model,
            device=device,
            compute_type=compute_type,
            manifest_only=manifest_only,
            run_postprocess=run_postprocess,
            target_lufs=target_lufs,
            leading_pad_ms=leading_pad_ms,
            trailing_pad_ms=trailing_pad_ms,
            fade_ms=fade_ms,
            metadata_path=metadata_path,
            interactive_metadata=interactive_metadata,
        )

        try:
            result = run_clip_job(job, model=model)
        except Exception as exc:  # pragma: no cover - surfaced in batch summary
            failed += 1
            sessions.append(
                BatchSessionResult(
                    input_path=audio_path,
                    session_id=session_id,
                    status="failed",
                    message=str(exc),
                )
            )
            if fail_fast:
                break
            continue

        processed += 1
        sessions.append(
            BatchSessionResult(
                input_path=audio_path,
                session_id=session_id,
                status="ok",
                clips_exported=result.manifest.stats["clips_exported"],
            )
        )

        if index_path is not None:
            append_index_record(
                index_path,
                {
                    "session_id": session_id,
                    "source_path": str(audio_path),
                    "source_sha256": result.manifest.source["sha256"],
                    "clips": result.manifest.stats["clips_exported"],
                    "missing": result.manifest.stats["phrase_types_missing"],
                    "manifest": str(result.manifest_path),
                    "status": "ok",
                    "finished_at": datetime.now(UTC).isoformat(),
                },
            )

    return BatchResult(
        sessions=sessions,
        processed=processed,
        skipped=skipped,
        failed=failed,
    )
