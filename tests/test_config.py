from pathlib import Path

import pytest

from voiceclipper.config import load_phrases


def test_load_phrases_from_example(tmp_path: Path) -> None:
    phrases_file = tmp_path / "phrases.yaml"
    phrases_file.write_text(
        """
phrases:
  - id: hello
    text: "hello world"
    padding_ms: 100
  - id: goodbye
    text: goodbye
""",
        encoding="utf-8",
    )

    phrases = load_phrases(phrases_file)

    assert len(phrases) == 2
    assert phrases[0].id == "hello"
    assert phrases[0].text == "hello world"
    assert phrases[0].padding_ms == 100
    assert phrases[1].padding_ms == 250


def test_load_phrases_requires_entries(tmp_path: Path) -> None:
    phrases_file = tmp_path / "phrases.yaml"
    phrases_file.write_text("phrases: []\n", encoding="utf-8")

    with pytest.raises(ValueError, match="at least one phrase"):
        load_phrases(phrases_file)
