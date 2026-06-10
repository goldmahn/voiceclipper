from pathlib import Path

from voiceclipper.manifest import build_manifest, manifest_is_current, write_manifest
from voiceclipper.manifest import ClipEntry


def test_build_manifest_and_is_current(tmp_path: Path) -> None:
    source = tmp_path / "source.mp3"
    phrases = tmp_path / "phrases.yaml"
    source.write_bytes(b"audio")
    phrases.write_text("phrases: []\n", encoding="utf-8")

    clip = ClipEntry(
        clip_id="session_001_000001",
        phrase_id="who_sent_you",
        occurrence_index=0,
        filename="who_sent_you.wav",
        path="clips/who_sent_you.wav",
        matched_text="who sent you?",
        start_ms=1000,
        end_ms=2000,
        duration_ms=1000,
        word_start_index=0,
        word_end_index=2,
    )
    manifest = build_manifest(
        session_id="session_001",
        source_path=source,
        source_duration_ms=5000,
        phrases_path=phrases,
        phrases_count=1,
        whisper_model="base",
        device="cpu",
        word_count=3,
        missing_phrase_ids=[],
        clips=[clip],
    )

    manifest_path = tmp_path / "manifest.json"
    write_manifest(manifest_path, manifest)

    assert manifest_is_current(manifest_path, source, phrases)
    source.write_bytes(b"changed")
    assert not manifest_is_current(manifest_path, source, phrases)
