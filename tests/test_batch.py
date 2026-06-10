from pathlib import Path

from voiceclipper.batch import discover_audio_files


def test_discover_audio_files(tmp_path: Path) -> None:
    (tmp_path / "a.mp3").write_bytes(b"a")
    (tmp_path / "b.wav").write_bytes(b"b")
    (tmp_path / "notes.txt").write_bytes(b"ignore")

    files = discover_audio_files(tmp_path)

    assert [path.name for path in files] == ["a.mp3", "b.wav"]
