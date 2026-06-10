from voiceclipper.config import PhraseTarget
from voiceclipper.detector import find_phrase_matches
from voiceclipper.transcriber import TranscriptWord


def test_find_phrase_matches_is_case_insensitive() -> None:
    phrases = [
        PhraseTarget(id="intro", text="Welcome To The Show", padding_ms=100),
        PhraseTarget(id="outro", text="thanks for listening", padding_ms=50),
    ]
    words = [
        TranscriptWord(text="Welcome", start=1.2, end=1.5),
        TranscriptWord(text="to", start=1.5, end=1.7),
        TranscriptWord(text="the", start=1.7, end=1.9),
        TranscriptWord(text="show,", start=1.9, end=2.2),
        TranscriptWord(text="everyone.", start=2.2, end=4.5),
        TranscriptWord(text="Thanks", start=58.2, end=58.6),
        TranscriptWord(text="for", start=58.6, end=58.8),
        TranscriptWord(text="listening.", start=58.8, end=60.1),
    ]

    matches = find_phrase_matches(phrases, words)

    assert len(matches) == 2
    assert matches[0].phrase.id == "intro"
    assert matches[0].start_ms == 1100
    assert matches[0].end_ms == 2300
    assert matches[1].phrase.id == "outro"
    assert matches[1].start_ms == 58150
    assert matches[1].end_ms == 60150


def test_find_phrase_matches_finds_every_occurrence() -> None:
    phrases = [PhraseTarget(id="repeat", text="hello", padding_ms=0)]
    words = [
        TranscriptWord(text="hello", start=0.0, end=0.4),
        TranscriptWord(text="there", start=0.4, end=0.8),
        TranscriptWord(text="hello", start=5.0, end=5.4),
        TranscriptWord(text="again", start=5.4, end=5.8),
    ]

    matches = find_phrase_matches(phrases, words)

    assert len(matches) == 2
    assert matches[0].start_ms == 0
    assert matches[0].end_ms == 400
    assert matches[1].start_ms == 5000
    assert matches[1].end_ms == 5400


def test_find_phrase_matches_handles_multi_word_phrases() -> None:
    phrases = [PhraseTarget(id="who_sent_you", text="Who sent you?", padding_ms=0)]
    words = [
        TranscriptWord(text="Who", start=1.0, end=1.2),
        TranscriptWord(text="sent", start=1.2, end=1.5),
        TranscriptWord(text="you?", start=1.5, end=1.8),
    ]

    matches = find_phrase_matches(phrases, words)

    assert len(matches) == 1
    assert matches[0].matched_text == "Who sent you?"
    assert matches[0].start_ms == 1000
    assert matches[0].end_ms == 1800
