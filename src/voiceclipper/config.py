from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class PhraseTarget:
    id: str
    text: str
    padding_ms: int = 250


@dataclass(frozen=True)
class ClipJob:
    input_path: Path
    output_dir: Path
    phrases_path: Path
    phrases: list[PhraseTarget]
    session_id: str | None = None
    whisper_model: str = "base"
    device: str = "cpu"
    compute_type: str = "int8"
    write_manifest: bool = True
    manifest_only: bool = False
    run_postprocess: bool = True
    target_lufs: float = -23.0
    leading_pad_ms: int = 75
    trailing_pad_ms: int = 75
    fade_ms: int = 3


def load_phrases(path: Path) -> list[PhraseTarget]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
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
