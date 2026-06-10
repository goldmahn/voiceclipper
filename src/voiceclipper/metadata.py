from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Callable

SESSION_LOCATION_TYPES = (
    "home office",
    "bedroom",
    "studio",
    "living room",
    "classroom",
    "other",
)

CONTENT_METADATA_FIELDS = (
    "species",
    "situation",
    "emotion",
    "intensity",
    "character_archetype",
    "delivery_style",
    "context_notes",
)

SPEAKER_FIELDS = (
    "speaker_name",
    "speaker_id",
    "speaker_display_name",
    "consent_status",
    "consent_version",
    "age_range",
    "native_language",
    "accent_or_dialect",
    "vocal_notes",
)

SESSION_FIELDS = (
    "session_id",
    "recording_date",
    "recording_location_type",
    "room_description",
    "microphone",
    "recorder_device",
    "recording_distance",
    "recording_position",
    "background_noise",
    "source_audio_filename",
    "recording_notes",
)


@dataclass
class CorpusMetadata:
    speaker: dict[str, str] = field(default_factory=dict)
    session: dict[str, str] = field(default_factory=dict)


PromptFn = Callable[[str, str], str]


def generate_speaker_id(speaker_name: str, session_id: str) -> str:
    if speaker_name.strip():
        slug = re.sub(r"[^a-zA-Z0-9]+", "_", speaker_name.strip().lower()).strip("_")
        if slug:
            return f"speaker_{slug}"
    return f"speaker_{session_id}"


def default_corpus_metadata(
    *,
    session_id: str,
    source_path: Path,
) -> CorpusMetadata:
    today = date.today().isoformat()
    return CorpusMetadata(
        speaker={
            "speaker_name": "",
            "speaker_id": generate_speaker_id("", session_id),
            "speaker_display_name": "",
            "consent_status": "",
            "consent_version": "",
            "age_range": "",
            "native_language": "",
            "accent_or_dialect": "",
            "vocal_notes": "",
        },
        session={
            "session_id": session_id,
            "recording_date": today,
            "recording_location_type": "",
            "room_description": "",
            "microphone": "",
            "recorder_device": "",
            "recording_distance": "",
            "recording_position": "",
            "background_noise": "",
            "source_audio_filename": source_path.name,
            "recording_notes": "",
        },
    )


def load_metadata_json(path: Path) -> CorpusMetadata:
    if not path.exists():
        raise FileNotFoundError(f"Metadata file not found: {path}")

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Metadata JSON must parse: {path}") from exc

    if not isinstance(payload, dict):
        raise ValueError("Metadata JSON must be an object")

    speaker = _coerce_layer(payload.get("speaker"), SPEAKER_FIELDS)
    session = _coerce_layer(payload.get("session"), SESSION_FIELDS)
    return CorpusMetadata(speaker=speaker, session=session)


def merge_corpus_metadata(base: CorpusMetadata, override: CorpusMetadata) -> CorpusMetadata:
    speaker = dict(base.speaker)
    session = dict(base.session)

    for key, value in override.speaker.items():
        if _has_value(value):
            speaker[key] = value

    for key, value in override.session.items():
        if _has_value(value):
            session[key] = value

    return CorpusMetadata(speaker=speaker, session=session)


def collect_corpus_metadata(
    *,
    session_id: str,
    source_path: Path,
    metadata_path: Path | None = None,
    interactive: bool = False,
    prompt_fn: PromptFn | None = None,
) -> CorpusMetadata:
    metadata = default_corpus_metadata(session_id=session_id, source_path=source_path)

    if metadata_path is not None:
        metadata = merge_corpus_metadata(metadata, load_metadata_json(metadata_path))

    if interactive:
        if not sys.stdin.isatty():
            raise RuntimeError("Interactive metadata requires a TTY")
        metadata = merge_corpus_metadata(
            metadata,
            prompt_for_corpus_metadata(metadata, prompt_fn=prompt_fn or input),
        )

    validate_corpus_metadata(metadata, source_path=source_path)
    return finalize_corpus_metadata(metadata, session_id=session_id, source_path=source_path)


def prompt_for_corpus_metadata(
    existing: CorpusMetadata,
    *,
    prompt_fn: PromptFn,
) -> CorpusMetadata:
    print("\nCorpus Voces metadata capture")
    print("Press Enter to keep the shown default. Most fields are optional.\n")

    speaker = dict(existing.speaker)
    session = dict(existing.session)

    print("Speaker metadata")
    for field_name in SPEAKER_FIELDS:
        if field_name == "speaker_id":
            continue
        label = field_name.replace("_", " ")
        speaker[field_name] = _prompt_value(
            prompt_fn,
            label,
            speaker.get(field_name, ""),
        )

    speaker["speaker_id"] = _prompt_value(
        prompt_fn,
        "speaker id",
        speaker.get("speaker_id", ""),
    )

    print("\nSession metadata")
    for field_name in SESSION_FIELDS:
        label = field_name.replace("_", " ")
        default = session.get(field_name, "")
        if field_name == "recording_location_type":
            session[field_name] = _prompt_choice(
                prompt_fn,
                label,
                default,
                SESSION_LOCATION_TYPES,
            )
        else:
            session[field_name] = _prompt_value(prompt_fn, label, default)

    return CorpusMetadata(speaker=speaker, session=session)


def validate_corpus_metadata(metadata: CorpusMetadata, *, source_path: Path) -> None:
    if not source_path.exists():
        raise FileNotFoundError(f"Input audio not found: {source_path}")

    session_id = metadata.session.get("session_id", "").strip()
    if not session_id:
        raise ValueError("session_id is required")

    speaker_id = metadata.speaker.get("speaker_id", "").strip()
    if not speaker_id:
        raise ValueError("speaker_id is required")


def finalize_corpus_metadata(
    metadata: CorpusMetadata,
    *,
    session_id: str,
    source_path: Path,
) -> CorpusMetadata:
    speaker = dict(metadata.speaker)
    session = dict(metadata.session)

    session["session_id"] = session.get("session_id", "").strip() or session_id
    session["source_audio_filename"] = (
        session.get("source_audio_filename", "").strip() or source_path.name
    )

    if not session.get("recording_date", "").strip():
        session["recording_date"] = date.today().isoformat()

    speaker_name = speaker.get("speaker_name", "").strip()
    if not speaker.get("speaker_id", "").strip():
        speaker["speaker_id"] = generate_speaker_id(speaker_name, session["session_id"])

    return CorpusMetadata(speaker=speaker, session=session)


def parse_phrase_content_metadata(raw: object) -> dict[str, object]:
    if raw is None:
        return _empty_content_metadata()

    if not isinstance(raw, dict):
        raise ValueError("phrase metadata must be a mapping")

    content: dict[str, object] = _empty_content_metadata()
    for key in CONTENT_METADATA_FIELDS:
        if key not in raw:
            continue
        value = raw[key]
        if key == "intensity":
            content[key] = _parse_intensity(value)
        else:
            content[key] = "" if value is None else str(value)

    return content


def content_metadata_to_dict(metadata: dict[str, object]) -> dict[str, object]:
    payload = dict(metadata)
    intensity = payload.get("intensity")
    if intensity == "" or intensity is None:
        payload["intensity"] = ""
    return payload


def _empty_content_metadata() -> dict[str, object]:
    return {key: "" for key in CONTENT_METADATA_FIELDS}


def _parse_intensity(value: object) -> int | str:
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        raise ValueError("intensity must be numeric if present")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return ""
        if not stripped.isdigit():
            raise ValueError("intensity must be numeric if present")
        return int(stripped)
    raise ValueError("intensity must be numeric if present")


def _coerce_layer(raw: object, fields: tuple[str, ...]) -> dict[str, str]:
    layer = {field_name: "" for field_name in fields}
    if not isinstance(raw, dict):
        return layer
    for field_name in fields:
        value = raw.get(field_name)
        if value is None:
            continue
        layer[field_name] = str(value)
    return layer


def _has_value(value: object) -> bool:
    return value is not None and str(value).strip() != ""


def _prompt_value(prompt_fn: PromptFn, label: str, default: str) -> str:
    suffix = f" [{default}]" if default else ""
    response = prompt_fn(f"{label}{suffix}: ").strip()
    return response or default


def _prompt_choice(
    prompt_fn: PromptFn,
    label: str,
    default: str,
    options: tuple[str, ...],
) -> str:
    print(f"{label} options: {', '.join(options)}")
    response = _prompt_value(prompt_fn, label, default)
    if not response:
        return default
    if response in options:
        return response
    if response.lower() in options:
        return response.lower()
    return response
