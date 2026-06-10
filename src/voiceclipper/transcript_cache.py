from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from voiceclipper.transcriber import TranscriptWord


def transcript_cache_path(session_dir: Path) -> Path:
    return session_dir / "transcript.words.json"


def load_transcript_cache(path: Path) -> list[TranscriptWord] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None

    words_payload = payload.get("words")
    if not isinstance(words_payload, list):
        return None

    words: list[TranscriptWord] = []
    for entry in words_payload:
        if not isinstance(entry, dict):
            return None
        text = entry.get("text")
        start = entry.get("start")
        end = entry.get("end")
        if not isinstance(text, str) or not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            return None
        words.append(TranscriptWord(text=text, start=float(start), end=float(end)))

    return words


def save_transcript_cache(path: Path, words: list[TranscriptWord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"words": [asdict(word) for word in words]}
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
