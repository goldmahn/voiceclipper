from voiceclipper.transcript_cache import load_transcript_cache, save_transcript_cache
from voiceclipper.transcriber import TranscriptWord


def test_transcript_cache_round_trip(tmp_path) -> None:
    cache_path = tmp_path / "transcript.words.json"
    words = [
        TranscriptWord(text="who", start=1.0, end=1.2),
        TranscriptWord(text="sent", start=1.2, end=1.5),
    ]

    save_transcript_cache(cache_path, words)
    loaded = load_transcript_cache(cache_path)

    assert loaded is not None
    assert len(loaded) == 2
    assert loaded[0].text == "who"
    assert loaded[1].start == 1.2
