from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class StageSummary:
    total: int
    pass_count: int
    review: int
    reject: int
    failures: list[str]


@dataclass(frozen=True)
class PostProcessResult:
    normalized_dir: Path
    training_dir: Path
    reports_dir: Path
    lufs: StageSummary
    finalize: StageSummary


def resolve_node_cli(*, env_var: str, bin_name: str, sibling_project: str) -> list[str]:
    override = os.environ.get(env_var)
    if override:
        return override.split()

    bin_path = shutil.which(bin_name)
    if bin_path:
        return [bin_path]

    repo_root = Path(__file__).resolve().parents[2]
    cli_js = repo_root.parent / sibling_project / "src" / "cli.js"
    if cli_js.is_file():
        node = shutil.which("node") or "node"
        return [node, str(cli_js)]

    raise FileNotFoundError(
        f"Could not find {bin_name}. Install it on PATH, set {env_var}, "
        f"or place {sibling_project} next to the voiceclipper project."
    )


def run_postprocess(
    session_dir: Path,
    clips_dir: Path,
    *,
    target_lufs: float = -23,
    leading_pad_ms: int = 75,
    trailing_pad_ms: int = 75,
    fade_ms: int = 3,
) -> PostProcessResult:
    if not clips_dir.is_dir():
        raise FileNotFoundError(f"Clips folder not found: {clips_dir}")

    wav_files = sorted(clips_dir.glob("*.wav"))
    if not wav_files:
        raise ValueError(f"No WAV clips found in {clips_dir}")

    normalized_dir = session_dir / "normalized_clips"
    training_dir = session_dir / "training_clips"
    reports_dir = session_dir / "reports"

    normalized_dir.mkdir(parents=True, exist_ok=True)
    training_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    lufs_cmd = resolve_node_cli(
        env_var="LUFS_BUFF_CLI",
        bin_name="lufs-buff",
        sibling_project="lufs-buff",
    )
    _run_command(
        [
            *lufs_cmd,
            str(clips_dir),
            str(normalized_dir),
            "--report",
            str(reports_dir),
            "--target",
            str(target_lufs),
        ],
        stage="LUFS Buff",
    )

    finisher_cmd = resolve_node_cli(
        env_var="CORPUS_FINISHER_CLI",
        bin_name="corpus-finisher",
        sibling_project="corpus-finisher",
    )
    finisher_args = [
        *finisher_cmd,
        str(normalized_dir),
        str(training_dir),
        "--report",
        str(reports_dir),
        "--leading-pad",
        str(leading_pad_ms),
        "--trailing-pad",
        str(trailing_pad_ms),
        "--fade",
        str(fade_ms),
    ]
    _run_command(finisher_args, stage="Corpus Finisher")

    lufs_report = _load_report(reports_dir / "qc-report.json", "LUFS Buff")
    finalize_report = _load_report(reports_dir / "finalize-report.json", "Corpus Finisher")

    return PostProcessResult(
        normalized_dir=normalized_dir,
        training_dir=training_dir,
        reports_dir=reports_dir,
        lufs=_report_summary(lufs_report),
        finalize=_report_summary(finalize_report),
    )


def _run_command(args: list[str], *, stage: str) -> None:
    try:
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"{stage} command not found: {args[0]}") from exc

    if result.returncode != 0:
        details = (result.stderr or result.stdout or "").strip()
        message = f"{stage} failed with exit code {result.returncode}"
        if details:
            message = f"{message}\n{details}"
        raise RuntimeError(message)


def _load_report(path: Path, stage: str) -> dict[str, object]:
    if not path.is_file():
        raise RuntimeError(f"{stage} did not write report: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _report_summary(report: dict[str, object]) -> StageSummary:
    summary = report.get("summary")
    if not isinstance(summary, dict):
        raise RuntimeError("Post-process report is missing summary")

    failures: list[str] = []
    clips = report.get("clips")
    if isinstance(clips, list):
        for clip in clips:
            if not isinstance(clip, dict):
                continue
            if clip.get("status") != "REJECT":
                continue
            filename = clip.get("filename", "unknown")
            notes = clip.get("notes") or clip.get("error") or "rejected"
            if isinstance(notes, list):
                notes = "; ".join(str(note) for note in notes)
            failures.append(f"{filename}: {notes}")

    return StageSummary(
        total=int(summary.get("total", 0)),
        pass_count=int(summary.get("pass", 0)),
        review=int(summary.get("review", 0)),
        reject=int(summary.get("reject", 0)),
        failures=failures,
    )
