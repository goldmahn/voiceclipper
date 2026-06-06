from voiceclipper.config import PhraseTarget
from voiceclipper.detector import find_phrase_matches
from voiceclipper.transcriber import TranscriptSegment


def test_find_phrase_matches_is_case_insensitive() -> None:
    phrases = [
        PhraseTarget(id="intro", text="Welcome To The Show", padding_ms=100),
        PhraseTarget(id="outro", text="thanks for listening", padding_ms=50),
    ]
    segments = [
        TranscriptSegment(text="Welcome to the show, everyone.", start=1.2, end=4.5),
        TranscriptSegment(text="Some middle content here.", start=10.0, end=12.0),
        TranscriptSegment(text="Thanks for listening.", start=58.2, end=60.1),
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
        TranscriptSegment(text="hello there", start=0.0, end=1.0),
        TranscriptSegment(text="hello again", start=5.0, end=6.0),
    ]

    matches = find_phrase_matches(phrases, segments)

    assert len(matches) == 1
    assert matches[0].segment.start == 0.0
