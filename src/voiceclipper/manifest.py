from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from voiceclipper import __version__
from voiceclipper.util import file_sha256


MANIFEST_VERSION = 1


@dataclass(frozen=True)
class ClipEntry:
    clip_id: str
    phrase_id: str
    occurrence_index: int
    filename: str
    path: str
    matched_text: str
    start_ms: int
    end_ms: int
    duration_ms: int
    word_start_index: int
    word_end_index: int


@dataclass(frozen=True)
class SessionManifest:
    manifest_version: int
    tool: str
    tool_version: str
    created_at: str
    session_id: str
    source: dict[str, object]
    phrases: dict[str, object]
    transcription: dict[str, object]
    stats: dict[str, int]
    missing_phrase_ids: list[str]
    clips: list[ClipEntry]

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["clips"] = [asdict(clip) for clip in self.clips]
        return payload


def build_manifest(
    *,
    session_id: str,
    source_path: Path,
    source_duration_ms: int,
    phrases_path: Path,
    phrases_count: int,
    whisper_model: str,
    device: str,
    word_count: int,
    missing_phrase_ids: list[str],
    clips: list[ClipEntry],
) -> SessionManifest:
    matched_types = {clip.phrase_id for clip in clips}
    return SessionManifest(
        manifest_version=MANIFEST_VERSION,
        tool="voiceclipper",
        tool_version=__version__,
        created_at=datetime.now(UTC).isoformat(),
        session_id=session_id,
        source={
            "path": str(source_path),
            "sha256": file_sha256(source_path),
            "duration_ms": source_duration_ms,
            "format": source_path.suffix.lstrip(".").lower() or "unknown",
        },
        phrases={
            "path": str(phrases_path),
            "sha256": file_sha256(phrases_path),
            "count": phrases_count,
        },
        transcription={
            "model": whisper_model,
            "device": device,
            "word_count": word_count,
        },
        stats={
            "clips_exported": len(clips),
            "phrase_types_matched": len(matched_types),
            "phrase_types_missing": len(missing_phrase_ids),
        },
        missing_phrase_ids=missing_phrase_ids,
        clips=clips,
    )


def write_manifest(manifest_path: Path, manifest: SessionManifest) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest.to_dict(), indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def read_manifest(manifest_path: Path) -> dict[str, object]:
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def manifest_is_current(
    manifest_path: Path,
    source_path: Path,
    phrases_path: Path,
) -> bool:
    if not manifest_path.exists():
        return False
    try:
        payload = read_manifest(manifest_path)
    except (OSError, json.JSONDecodeError):
        return False

    source = payload.get("source")
    phrases = payload.get("phrases")
    if not isinstance(source, dict) or not isinstance(phrases, dict):
        return False

    source_hash = source.get("sha256")
    phrases_hash = phrases.get("sha256")
    if not isinstance(source_hash, str) or not isinstance(phrases_hash, str):
        return False

    return source_hash == file_sha256(source_path) and phrases_hash == file_sha256(phrases_path)


def clip_filename(phrase_id: str, occurrence_index: int) -> str:
    if occurrence_index == 0:
        return f"{phrase_id}.wav"
    return f"{phrase_id}{occurrence_index}.wav"
