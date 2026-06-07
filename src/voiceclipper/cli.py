from __future__ import annotations

import argparse
import sys
from pathlib import Path

from voiceclipper import __version__
from voiceclipper.config import ClipJob, ProcessingConfig, load_phrases
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

    proc = parser.add_argument_group("audio processing (off by default)")
    proc.add_argument(
        "--process",
        action="store_true",
        default=False,
        help="Enable the full audio processing chain on each clip",
    )
    proc.add_argument(
        "--no-noise-reduction",
        action="store_true",
        default=False,
        help="Disable spectral noise reduction (default: enabled when --process is set)",
    )
    proc.add_argument(
        "--no-compression",
        action="store_true",
        default=False,
        help="Disable dynamic range compression (default: enabled when --process is set)",
    )
    proc.add_argument(
        "--highpass-hz",
        type=int,
        default=80,
        metavar="HZ",
        help="High-pass filter cutoff in Hz (default: 80)",
    )
    proc.add_argument(
        "--presence-gain-db",
        type=float,
        default=2.5,
        metavar="DB",
        help="Presence boost gain in dB around --presence-hz (default: 2.5)",
    )
    proc.add_argument(
        "--presence-hz",
        type=int,
        default=3000,
        metavar="HZ",
        help="Center frequency for presence EQ boost in Hz (default: 3000)",
    )
    proc.add_argument(
        "--compression-ratio",
        type=float,
        default=3.0,
        metavar="RATIO",
        help="Compression ratio, e.g. 3.0 means 3:1 (default: 3.0)",
    )
    proc.add_argument(
        "--compression-threshold",
        type=float,
        default=-18.0,
        metavar="DB",
        help="Compression threshold in dBFS (default: -18.0)",
    )
    proc.add_argument(
        "--peak-limit",
        type=float,
        default=-1.0,
        metavar="DBTP",
        help="True-peak limiter ceiling in dBTP (default: -1.0)",
    )
    proc.add_argument(
        "--target-lufs",
        type=float,
        default=-16.0,
        metavar="LUFS",
        help="Target integrated loudness in LUFS; pass 0 to skip normalization (default: -16.0)",
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

    processing: ProcessingConfig | None = None
    if args.process:
        processing = ProcessingConfig(
            noise_reduction=not args.no_noise_reduction,
            highpass_hz=args.highpass_hz,
            presence_gain_db=args.presence_gain_db,
            presence_hz=args.presence_hz,
            compression=not args.no_compression,
            compression_ratio=args.compression_ratio,
            compression_threshold_db=args.compression_threshold,
            peak_limit_dbtp=args.peak_limit,
            target_lufs=None if args.target_lufs == 0 else args.target_lufs,
        )

    job = ClipJob(
        input_path=args.input,
        output_dir=args.output_dir,
        phrases=phrases,
        whisper_model=args.model,
        device=args.device,
        compute_type=args.compute_type,
        processing=processing,
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
