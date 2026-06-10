from __future__ import annotations

import argparse
import sys
from pathlib import Path

from voiceclipper import __version__
from voiceclipper.config import ClipJob, ProcessingConfig, load_phrases
from voiceclipper.pipeline import run_clip_job

_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".opus", ".wma"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voiceclipper",
        description=(
            "Review an audio recording, locate configured phrases, "
            "and export each match as a separate WAV clip."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    # --- inputs ---
    parser.add_argument(
        "input",
        type=Path,
        nargs="*",
        help="One or more source audio files. Omit when using --input-dir.",
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        metavar="DIR",
        help="Process all audio files in this directory.",
    )
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

    # --- transcription ---
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

    # --- matching ---
    match_grp = parser.add_argument_group("phrase matching")
    match_grp.add_argument(
        "--min-confidence",
        type=float,
        default=1.0,
        metavar="0-1",
        help=(
            "Minimum match confidence for fuzzy matching (default: 1.0 = exact substring). "
            "Lower values allow near-matches, e.g. 0.8."
        ),
    )

    # --- audio processing ---
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
        help="Disable spectral noise reduction",
    )
    proc.add_argument(
        "--no-compression",
        action="store_true",
        default=False,
        help="Disable dynamic range compression",
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
        help="Presence boost gain in dB (default: 2.5)",
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
        help="Compression ratio (default: 3.0)",
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
        help="Target integrated loudness in LUFS; pass 0 to skip (default: -16.0)",
    )

    # --- diarization ---
    diar = parser.add_argument_group("speaker diarization (requires voiceclipper[diarize])")
    diar.add_argument(
        "--diarize",
        action="store_true",
        default=False,
        help="Run speaker diarization and label each clip with the dominant speaker",
    )
    diar.add_argument(
        "--hf-token",
        metavar="TOKEN",
        help="HuggingFace access token (required when --diarize is set)",
    )

    return parser


def _collect_inputs(args: argparse.Namespace, parser: argparse.ArgumentParser) -> list[Path]:
    inputs: list[Path] = list(args.input or [])
    if args.input_dir:
        if not args.input_dir.is_dir():
            parser.error(f"--input-dir is not a directory: {args.input_dir}")
        inputs += sorted(
            p for p in args.input_dir.iterdir() if p.suffix.lower() in _AUDIO_EXTENSIONS
        )
    if not inputs:
        parser.error("provide at least one input file or use --input-dir")
    return inputs


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    inputs = _collect_inputs(args, parser)
    is_batch = len(inputs) > 1

    try:
        phrases = load_phrases(args.phrases)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.diarize and not args.hf_token:
        print("error: --hf-token is required when --diarize is set", file=sys.stderr)
        return 1

    if args.min_confidence < 0.0 or args.min_confidence > 1.0:
        print("error: --min-confidence must be between 0.0 and 1.0", file=sys.stderr)
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

    any_clips = False
    exit_code = 0

    for input_path in inputs:
        output_dir = args.output_dir / input_path.stem if is_batch else args.output_dir

        job = ClipJob(
            input_path=input_path,
            output_dir=output_dir,
            phrases=phrases,
            whisper_model=args.model,
            device=args.device,
            compute_type=args.compute_type,
            processing=processing,
            min_confidence=args.min_confidence,
            diarize=args.diarize,
            hf_token=args.hf_token,
        )

        prefix = f"[{input_path.name}] " if is_batch else ""

        try:
            result = run_clip_job(job)
        except FileNotFoundError as exc:
            print(f"{prefix}error: {exc}", file=sys.stderr)
            exit_code = 1
            continue
        except Exception as exc:
            print(f"{prefix}error: {exc}", file=sys.stderr)
            exit_code = 1
            continue

        for clip in result.clips:
            segment = clip.match.segment
            confidence_note = (
                f" (confidence: {clip.match.confidence:.0%})"
                if args.min_confidence < 1.0
                else ""
            )
            speaker_note = f" [{clip.match.speaker}]" if clip.match.speaker else ""
            print(
                f"{prefix}saved {clip.output_path} "
                f"({clip.match.start_ms}-{clip.match.end_ms} ms)"
                f"{speaker_note}"
                f"{confidence_note} "
                f"from segment: {segment.text!r}"
            )
            any_clips = True

        if result.missing_phrase_ids:
            print(
                f"{prefix}warning: no match found for: "
                + ", ".join(result.missing_phrase_ids),
                file=sys.stderr,
            )

        if not result.clips:
            exit_code = 1

    if not any_clips:
        print("error: no phrase matches found; no clips were exported", file=sys.stderr)
        return 1

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
