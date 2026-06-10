from voiceclipper.config import PhraseTarget
from voiceclipper.detector import (
    SpeakerSegment,
    _dominant_speaker,
    _find_word_span,
    find_phrase_matches,
)
from voiceclipper.transcriber import TranscriptSegment, WordTimestamp


def _seg(text: str, start: float, end: float, words: tuple[WordTimestamp, ...] = ()) -> TranscriptSegment:
    return TranscriptSegment(text=text, start=start, end=end, words=words)


def _words(*pairs: tuple[str, float, float]) -> tuple[WordTimestamp, ...]:
    return tuple(WordTimestamp(word=w, start=s, end=e) for w, s, e in pairs)


# --- existing tests (still pass) ---

def test_find_phrase_matches_is_case_insensitive() -> None:
    phrases = [
        PhraseTarget(id="intro", text="Welcome To The Show", padding_ms=100),
        PhraseTarget(id="outro", text="thanks for listening", padding_ms=50),
    ]
    segments = [
        _seg("Welcome to the show, everyone.", 1.2, 4.5),
        _seg("Some middle content here.", 10.0, 12.0),
        _seg("Thanks for listening.", 58.2, 60.1),
    ]

    matches = find_phrase_matches(phrases, segments)

    assert len(matches) == 2
    assert matches[0].phrase.id == "intro"
    assert matches[0].start_ms == 1100
    assert matches[0].end_ms == 4600
    assert matches[1].phrase.id == "outro"
    assert matches[1].start_ms == 58150


def test_find_phrase_matches_reports_only_first_segment_match() -> None:
    phrases = [PhraseTarget(id="repeat", text="hello", padding_ms=0)]
    segments = [
        _seg("hello there", 0.0, 1.0),
        _seg("hello again", 5.0, 6.0),
    ]

    matches = find_phrase_matches(phrases, segments)

    assert len(matches) == 1
    assert matches[0].segment.start == 0.0


# --- word-level timestamps ---

def test_find_word_span_returns_tight_boundaries() -> None:
    words = _words(
        ("Welcome", 1.0, 1.4),
        ("to", 1.4, 1.6),
        ("the", 1.6, 1.8),
        ("show", 1.8, 2.2),
        ("everyone", 2.3, 2.9),
    )
    span = _find_word_span(words, "welcome to the show")
    assert span is not None
    assert span[0] == 1.0
    assert span[1] == 2.2


def test_find_word_span_strips_punctuation() -> None:
    words = _words(
        ("Thanks,", 4.0, 4.3),
        ("for", 4.3, 4.5),
        ("listening.", 4.5, 4.9),
    )
    span = _find_word_span(words, "thanks for listening")
    assert span is not None
    assert span[0] == 4.0
    assert span[1] == 4.9


def test_find_word_span_returns_none_when_not_found() -> None:
    words = _words(("hello", 0.0, 0.5), ("world", 0.5, 1.0))
    assert _find_word_span(words, "goodbye") is None


def test_find_word_span_empty_words() -> None:
    assert _find_word_span((), "anything") is None


def test_word_timestamps_used_in_phrase_match() -> None:
    words = _words(
        ("Welcome", 1.0, 1.4),
        ("to", 1.4, 1.6),
        ("the", 1.6, 1.8),
        ("show", 1.8, 2.2),
        ("everyone", 2.3, 2.9),
    )
    phrases = [PhraseTarget(id="intro", text="welcome to the show", padding_ms=0)]
    segments = [_seg("Welcome to the show, everyone.", 1.0, 2.9, words=words)]

    matches = find_phrase_matches(phrases, segments)

    assert len(matches) == 1
    # Should use tight word boundaries (1000-2200ms), not full segment (1000-2900ms)
    assert matches[0].start_ms == 1000
    assert matches[0].end_ms == 2200


# --- fuzzy matching ---

def test_fuzzy_matching_finds_near_match() -> None:
    phrases = [PhraseTarget(id="intro", text="welcome to the show", padding_ms=0)]
    # Simulate a slight transcription error
    segments = [_seg("Welcome to the shaw everyone.", 1.0, 3.0)]

    exact_matches = find_phrase_matches(phrases, segments, min_confidence=1.0)
    assert len(exact_matches) == 0

    fuzzy_matches = find_phrase_matches(phrases, segments, min_confidence=0.7)
    assert len(fuzzy_matches) == 1
    assert fuzzy_matches[0].confidence < 1.0
    assert fuzzy_matches[0].confidence >= 0.7


def test_exact_match_has_confidence_1() -> None:
    phrases = [PhraseTarget(id="intro", text="welcome to the show", padding_ms=0)]
    segments = [_seg("Welcome to the show, everyone.", 1.0, 3.0)]

    matches = find_phrase_matches(phrases, segments, min_confidence=1.0)
    assert len(matches) == 1
    assert matches[0].confidence == 1.0


# --- speaker diarization ---

def test_dominant_speaker_returns_most_overlapping() -> None:
    diarization = [
        SpeakerSegment(speaker="A", start=0.0, end=2.0),
        SpeakerSegment(speaker="B", start=2.0, end=5.0),
    ]
    assert _dominant_speaker(diarization, 0.0, 1.5) == "A"
    assert _dominant_speaker(diarization, 1.5, 5.0) == "B"


def test_dominant_speaker_returns_none_with_no_overlap() -> None:
    diarization = [SpeakerSegment(speaker="A", start=10.0, end=12.0)]
    assert _dominant_speaker(diarization, 0.0, 1.0) is None


def test_speaker_attached_to_phrase_match() -> None:
    diarization = [SpeakerSegment(speaker="SPEAKER_00", start=0.0, end=5.0)]
    phrases = [PhraseTarget(id="intro", text="welcome to the show", padding_ms=0)]
    segments = [_seg("Welcome to the show.", 1.0, 3.0)]

    matches = find_phrase_matches(phrases, segments, diarization=diarization)

    assert len(matches) == 1
    assert matches[0].speaker == "SPEAKER_00"


def test_no_diarization_speaker_is_none() -> None:
    phrases = [PhraseTarget(id="intro", text="welcome to the show", padding_ms=0)]
    segments = [_seg("Welcome to the show.", 1.0, 3.0)]

    matches = find_phrase_matches(phrases, segments)

    assert matches[0].speaker is None
