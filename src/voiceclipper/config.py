from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(frozen=True)
class PhraseTarget:
    id: str
    text: str
    padding_ms: int = 250


@dataclass(frozen=True)
class ProcessingConfig:
    noise_reduction: bool = True
    highpass_hz: int = 80
    presence_gain_db: float = 2.5
    presence_hz: int = 3000
    compression: bool = True
    compression_ratio: float = 3.0
    compression_threshold_db: float = -18.0
    peak_limit_dbtp: float = -1.0
    target_lufs: float | None = -16.0


@dataclass(frozen=True)
class ClipJob:
    input_path: Path
    output_dir: Path
    phrases: list[PhraseTarget]
    whisper_model: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    processing: ProcessingConfig | None = None


def load_phrases(path: Path) -> list[PhraseTarget]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"Failed to parse {path}: {exc}") from exc
    if not isinstance(data, dict) or "phrases" not in data:
        raise ValueError(f"{path} must contain a top-level 'phrases' list")

    phrases: list[PhraseTarget] = []
    for index, entry in enumerate(data["phrases"], start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"phrase #{index} must be a mapping")

        phrase_id = entry.get("id")
        text = entry.get("text")
        if not phrase_id or not text:
            raise ValueError(f"phrase #{index} requires 'id' and 'text'")

        padding_ms = entry.get("padding_ms", 250)
        if not isinstance(padding_ms, int) or padding_ms < 0:
            raise ValueError(f"phrase #{index} padding_ms must be a non-negative integer")

        phrases.append(
            PhraseTarget(
                id=str(phrase_id),
                text=str(text),
                padding_ms=padding_ms,
            )
        )

    if not phrases:
        raise ValueError(f"{path} must define at least one phrase")

    return phrases
