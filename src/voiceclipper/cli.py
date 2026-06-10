from __future__ import annotations

import argparse
import sys
from pathlib import Path

from voiceclipper import __version__
from voiceclipper.batch import run_batch
from voiceclipper.config import ClipJob, load_phrases
from voiceclipper.pipeline import PipelineResult, run_clip_job


def _add_shared_args(parser: argparse.ArgumentParser) -> None:
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
        help="Directory for session output (default: output)",
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
    parser.add_argument(
        "--session-id",
        default=None,
        help="Override session id used for output directory naming",
    )
    parser.add_argument(
        "--manifest-only",
        action="store_true",
        help="Reuse cached transcript.words.json and re-export clips/manifest only",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voiceclipper",
        description=(
            "Review audio recordings, locate configured phrases, "
            "and export each match as a separate WAV clip."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    clip_parser = subparsers.add_parser(
        "clip",
        help="Process a single audio file",
    )
    _add_shared_args(clip_parser)
    clip_parser.add_argument("input", type=Path, help="Path to the source audio file")

    batch_parser = subparsers.add_parser(
        "batch",
        help="Process every audio file in a directory",
    )
    _add_shared_args(batch_parser)
    batch_parser.add_argument("input_dir", type=Path, help="Directory containing source audio files")
    batch_parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip sessions whose manifest matches the source and phrases file hashes",
    )
    batch_parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop batch processing on the first failed session",
    )
    batch_parser.add_argument(
        "--index",
        type=Path,
        default=None,
        help="Append one JSON line per processed session to this corpus index file",
    )

    return parser


def _print_clip_results(result: PipelineResult) -> None:
    for clip in result.clips:
        exported = clip.entry
        entry = exported.entry
        print(
            f"saved {exported.output_path} "
            f"({entry.start_ms}-{entry.end_ms} ms) "
            f"matched: {entry.matched_text!r}"
        )

    print(f"manifest: {result.manifest_path}")

    if result.missing_phrase_ids:
        print(
            "warning: no match found for: " + ", ".join(result.missing_phrase_ids),
            file=sys.stderr,
        )


def _run_clip(args: argparse.Namespace, phrases_path: Path, phrases: list) -> int:
    job = ClipJob(
        input_path=args.input,
        output_dir=args.output_dir,
        phrases_path=phrases_path,
        phrases=phrases,
        session_id=args.session_id,
        whisper_model=args.model,
        device=args.device,
        compute_type=args.compute_type,
        manifest_only=args.manifest_only,
    )

    try:
        result = run_clip_job(job)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - surfaced to CLI users
        print(f"error: {exc}", file=sys.stderr)
        return 1

    _print_clip_results(result)

    if not result.clips:
        print("error: no phrase matches found; no clips were exported", file=sys.stderr)
        return 1

    return 0


def _run_batch(args: argparse.Namespace, phrases_path: Path, phrases: list) -> int:
    try:
        result = run_batch(
            args.input_dir,
            args.output_dir,
            phrases_path,
            phrases,
            whisper_model=args.model,
            device=args.device,
            compute_type=args.compute_type,
            skip_existing=args.skip_existing,
            fail_fast=args.fail_fast,
            index_path=args.index,
            manifest_only=args.manifest_only,
        )
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover - surfaced to CLI users
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for session in result.sessions:
        if session.status == "ok":
            print(
                f"session {session.session_id}: exported {session.clips_exported} clips "
                f"from {session.input_path.name}"
            )
        elif session.status == "skipped":
            print(f"session {session.session_id}: skipped ({session.message})")
        else:
            print(
                f"session {session.session_id}: failed ({session.message})",
                file=sys.stderr,
            )

    print(
        "batch summary: "
        f"{result.processed} processed, {result.skipped} skipped, {result.failed} failed"
    )

    if result.processed == 0 and result.skipped > 0 and result.failed == 0:
        return 2
    if result.failed > 0:
        return 1
    if result.processed == 0:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    # Backward compatibility: `voiceclipper file.mp3` delegates to the clip command.
    if argv and not argv[0].startswith("-") and argv[0] not in {"clip", "batch", "--version", "-h", "--help"}:
        argv = ["clip", *argv]

    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 1

    try:
        phrases = load_phrases(args.phrases)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.command == "clip":
        return _run_clip(args, args.phrases, phrases)
    if args.command == "batch":
        return _run_batch(args, args.phrases, phrases)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
