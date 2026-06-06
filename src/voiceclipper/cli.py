from __future__ import annotations

import argparse
import sys
from pathlib import Path

from voiceclipper import __version__
from voiceclipper.config import ClipJob, load_phrases
from voiceclipper.pipeline import run_clip_job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voiceclipper",
        description=(
            "Review an audio recording, locate configured phrases, "
            "and export each match as a separate WAV clip."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("input", type=Path, help="Path to the source audio file")
    parser.add_argument(
        "--phrases",
        type=Path,
        default=Path("phrases.yaml"),
        help="YAML file listing phrases to detect (default: phrases.yaml)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for exported WAV clips (default: output)",
    )
    parser.add_argument(
        "--model",
        default="base",
        help="faster-whisper model size (default: base)",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        choices=["cpu", "cuda", "auto"],
        help="Inference device for transcription (default: cpu)",
    )
    parser.add_argument(
        "--compute-type",
        default="int8",
        help="faster-whisper compute type (default: int8)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        phrases = load_phrases(args.phrases)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    job = ClipJob(
        input_path=args.input,
        output_dir=args.output_dir,
        phrases=phrases,
        whisper_model=args.model,
        device=args.device,
        compute_type=args.compute_type,
    )

    try:
        result = run_clip_job(job)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - surfaced to CLI users
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for clip in result.clips:
        segment = clip.match.segment
        print(
            f"saved {clip.output_path} "
            f"({clip.match.start_ms}-{clip.match.end_ms} ms) "
            f"from segment: {segment.text!r}"
        )

    if result.missing_phrase_ids:
        print(
            "warning: no match found for: " + ", ".join(result.missing_phrase_ids),
            file=sys.stderr,
        )

    if not result.clips:
        print("error: no phrase matches found; no clips were exported", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
