from __future__ import annotations

import json
import subprocess
from pathlib import Path


def probe_duration_ms(audio_path: Path) -> int:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    duration_seconds = float(result.stdout.strip())
    return int(duration_seconds * 1000)


def export_clip_ffmpeg(
    audio_path: Path,
    output_path: Path,
    start_ms: int,
    end_ms: int,
) -> None:
    if start_ms >= end_ms:
        raise ValueError(f"Invalid clip range: {start_ms}-{end_ms} ms")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = end_ms - start_ms
    start_seconds = start_ms / 1000
    duration_seconds = duration_ms / 1000

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-ss",
            f"{start_seconds:.3f}",
            "-i",
            str(audio_path),
            "-t",
            f"{duration_seconds:.3f}",
            "-ac",
            "1",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ],
        check=True,
    )
