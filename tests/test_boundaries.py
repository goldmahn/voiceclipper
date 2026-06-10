from voiceclipper.boundaries import clip_boundaries
from voiceclipper.transcriber import TranscriptWord


def test_clip_boundaries_stays_within_word_gaps() -> None:
    words = [
        TranscriptWord(text="who", start=1.759, end=2.380),
        TranscriptWord(text="sent", start=2.380, end=2.660),
        TranscriptWord(text="you?", start=2.660, end=2.940),
        TranscriptWord(text="who", start=3.760, end=4.380),
    ]

    start_ms, end_ms = clip_boundaries(
        words,
        start_word_index=0,
        end_word_index=2,
        padding_ms=250,
        audio_length_ms=5000,
    )

    assert start_ms == 1509
    assert end_ms == 3190
    assert end_ms - start_ms < 2000


def test_clip_boundaries_does_not_bleed_into_adjacent_phrase_without_padding() -> None:
    words = [
        TranscriptWord(text="who", start=1.759, end=2.380),
        TranscriptWord(text="sent", start=2.380, end=2.660),
        TranscriptWord(text="you?", start=2.660, end=2.940),
        TranscriptWord(text="who", start=3.760, end=4.380),
    ]

    start_ms, end_ms = clip_boundaries(
        words,
        start_word_index=0,
        end_word_index=2,
        padding_ms=0,
        audio_length_ms=5000,
    )

    assert start_ms == 1759
    assert end_ms == 2940
