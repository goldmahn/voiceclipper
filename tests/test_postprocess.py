from __future__ import annotations

import json
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from voiceclipper.postprocess import PostProcessResult, resolve_node_cli, run_postprocess


def test_resolve_node_cli_prefers_env_override(monkeypatch) -> None:
    monkeypatch.setenv("LUFS_BUFF_CLI", "node /opt/lufs-buff/src/cli.js")
    command = resolve_node_cli(
        env_var="LUFS_BUFF_CLI",
        bin_name="lufs-buff",
        sibling_project="lufs-buff",
    )
    assert command == ["node", "/opt/lufs-buff/src/cli.js"]


def test_run_postprocess_runs_both_stages(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    clips_dir = session_dir / "clips"
    clips_dir.mkdir(parents=True)
    (clips_dir / "phrase.wav").write_bytes(b"wav")

    reports_dir = session_dir / "reports"
    reports_dir.mkdir(parents=True)

    call_count = 0

    def fake_run(args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            (reports_dir / "qc-report.json").write_text(
                json.dumps(
                    {
                        "summary": {"total": 1, "pass": 0, "review": 1, "reject": 0},
                        "clips": [{"filename": "phrase.wav", "status": "REVIEW"}],
                    }
                ),
                encoding="utf-8",
            )
        else:
            (reports_dir / "finalize-report.json").write_text(
                json.dumps(
                    {
                        "summary": {"total": 1, "pass": 1, "review": 0, "reject": 0},
                        "clips": [{"filename": "phrase.wav", "status": "PASS"}],
                    }
                ),
                encoding="utf-8",
            )
        return CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    with patch("voiceclipper.postprocess.resolve_node_cli") as resolve:
        resolve.side_effect = [
            ["lufs-buff"],
            ["corpus-finisher"],
        ]
        with patch("voiceclipper.postprocess.subprocess.run", side_effect=fake_run):
            result = run_postprocess(session_dir, clips_dir)

    assert isinstance(result, PostProcessResult)
    assert result.normalized_dir == session_dir / "normalized_clips"
    assert result.training_dir == session_dir / "training_clips"
    assert call_count == 2
    assert result.lufs.review == 1
    assert result.finalize.pass_count == 1


def test_run_postprocess_requires_clips(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    clips_dir = session_dir / "clips"
    clips_dir.mkdir(parents=True)

    with pytest.raises(ValueError, match="No WAV clips"):
        run_postprocess(session_dir, clips_dir)


def test_run_postprocess_surfaces_stage_failure(tmp_path: Path) -> None:
    session_dir = tmp_path / "session"
    clips_dir = session_dir / "clips"
    clips_dir.mkdir(parents=True)
    (clips_dir / "phrase.wav").write_bytes(b"wav")

    with patch("voiceclipper.postprocess.resolve_node_cli", return_value=["lufs-buff"]):
        with patch(
            "voiceclipper.postprocess.subprocess.run",
            return_value=CompletedProcess(args=[], returncode=1, stdout="", stderr="boom"),
        ):
            with pytest.raises(RuntimeError, match="LUFS Buff failed"):
                run_postprocess(session_dir, clips_dir)
