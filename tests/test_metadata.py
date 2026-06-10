from __future__ import annotations

import json
from pathlib import Path

import pytest

from voiceclipper.config import load_phrases
from voiceclipper.manifest import ClipEntry, build_manifest, write_manifest
from voiceclipper.metadata import (
    collect_corpus_metadata,
    default_corpus_metadata,
    generate_speaker_id,
    load_metadata_json,
    merge_corpus_metadata,
    parse_phrase_content_metadata,
    prompt_for_corpus_metadata,
)


def test_load_metadata_json(tmp_path: Path) -> None:
    metadata_path = tmp_path / "session.json"
    metadata_path.write_text(
        json.dumps(
            {
                "speaker": {"speaker_name": "Ariel Goldman", "speaker_id": "speaker_ariel_001"},
                "session": {"session_id": "session_001", "recording_location_type": "studio"},
            }
        ),
        encoding="utf-8",
    )

    metadata = load_metadata_json(metadata_path)

    assert metadata.speaker["speaker_name"] == "Ariel Goldman"
    assert metadata.session["recording_location_type"] == "studio"


def test_generate_speaker_id_from_name() -> None:
    assert generate_speaker_id("Ariel Goldman", "session_001") == "speaker_ariel_goldman"


def test_interactive_prompt_mapping(tmp_path: Path) -> None:
    source = tmp_path / "test.m4a"
    source.write_bytes(b"audio")
    responses = iter(
        [
            "Ariel Goldman",
            "Ariel",
            "owned/self-recorded",
            "internal-v1",
            "",
            "English",
            "General American",
            "",
            "speaker_ariel_001",
            "session_001",
            "2026-06-10",
            "home office",
            "small office",
            "iPhone built-in mic",
            "iPhone 15 Pro",
            "arm's length",
            "phone on table",
            "none noticeable",
            "test.m4a",
            "",
        ]
    )

    def fake_prompt(_label: str) -> str:
        return next(responses)

    metadata = prompt_for_corpus_metadata(
        merge_corpus_metadata(
            default_corpus_metadata(session_id="session_001", source_path=source),
            load_metadata_json(Path(__file__).resolve().parent.parent / "metadata" / "example_session.json"),
        ),
        prompt_fn=fake_prompt,
    )

    assert metadata.speaker["speaker_display_name"] == "Ariel"
    assert metadata.session["recording_location_type"] == "home office"


def test_collect_metadata_from_json_only(tmp_path: Path) -> None:
    source = tmp_path / "source.m4a"
    source.write_bytes(b"audio")
    metadata_path = tmp_path / "meta.json"
    metadata_path.write_text(
        json.dumps(
            {
                "speaker": {"speaker_id": "speaker_test_001"},
                "session": {"session_id": "session_test", "microphone": "USB microphone"},
            }
        ),
        encoding="utf-8",
    )

    metadata = collect_corpus_metadata(
        session_id="session_test",
        source_path=source,
        metadata_path=metadata_path,
    )

    assert metadata.speaker["speaker_id"] == "speaker_test_001"
    assert metadata.session["microphone"] == "USB microphone"


def test_manifest_includes_speaker_and_session_metadata(tmp_path: Path) -> None:
    source = tmp_path / "source.mp3"
    phrases = tmp_path / "phrases.yaml"
    source.write_bytes(b"audio")
    phrases.write_text("phrases: []\n", encoding="utf-8")

    clip = ClipEntry(
        clip_id="session_001_000001",
        phrase_id="close_the_door",
        occurrence_index=0,
        filename="close_the_door.wav",
        path="clips/close_the_door.wav",
        matched_text="Close the door.",
        start_ms=12340,
        end_ms=14220,
        duration_ms=1880,
        word_start_index=0,
        word_end_index=2,
        phrase_text="Close the door.",
        start=12.34,
        end=14.22,
        content_metadata={
            "species": "human",
            "situation": "warning",
            "emotion": "tense",
            "intensity": 3,
            "character_archetype": "guard",
            "delivery_style": "controlled",
            "context_notes": "",
        },
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
        session_metadata={
            "session_id": "session_001",
            "recording_date": "2026-06-10",
            "recording_location_type": "home office",
            "room_description": "",
            "microphone": "iPhone built-in mic",
            "recorder_device": "",
            "recording_distance": "",
            "recording_position": "",
            "background_noise": "",
            "source_audio_filename": "source.mp3",
            "recording_notes": "",
        },
        speaker_metadata={
            "speaker_id": "speaker_ariel_001",
            "speaker_name": "Ariel Goldman",
            "speaker_display_name": "Ariel",
            "consent_status": "owned/self-recorded",
            "consent_version": "internal-v1",
            "age_range": "",
            "native_language": "English",
            "accent_or_dialect": "General American",
            "vocal_notes": "",
        },
    )

    manifest_path = tmp_path / "manifest.json"
    write_manifest(manifest_path, manifest)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert payload["schema_version"] == 2
    assert payload["speaker"]["speaker_id"] == "speaker_ariel_001"
    assert payload["session"]["recording_location_type"] == "home office"
    assert payload["clips"][0]["content_metadata"]["emotion"] == "tense"
    assert payload["processing"]["voiceclipper"]["source_audio"].endswith("source.mp3")


def test_load_phrases_with_optional_metadata(tmp_path: Path) -> None:
    phrases_path = tmp_path / "phrases.yaml"
    phrases_path.write_text(
        """
phrases:
  - id: close_the_door
    text: "Close the door."
    padding_ms: 250
    metadata:
      species: human
      emotion: tense
      intensity: 3
""".strip(),
        encoding="utf-8",
    )

    phrases = load_phrases(phrases_path)

    assert phrases[0].content_metadata is not None
    assert phrases[0].content_metadata["species"] == "human"
    assert phrases[0].content_metadata["intensity"] == 3


def test_phrases_without_metadata_still_load(tmp_path: Path) -> None:
    phrases_path = tmp_path / "phrases.yaml"
    phrases_path.write_text(
        """
phrases:
  - id: who_sent_you
    text: "Who sent you?"
""".strip(),
        encoding="utf-8",
    )

    phrases = load_phrases(phrases_path)

    assert phrases[0].content_metadata is None


def test_intensity_validation() -> None:
    with pytest.raises(ValueError, match="intensity must be numeric"):
        parse_phrase_content_metadata({"intensity": "loud"})
