from __future__ import annotations

import re
from dataclasses import dataclass

from rapidfuzz import fuzz

from voiceclipper.config import PhraseTarget
from voiceclipper.transcriber import TranscriptSegment, WordTimestamp

_PUNCT_RE = re.compile(r"[^\w\s]")


@dataclass(frozen=True)
class SpeakerSegment:
    speaker: str
    start: float
    end: float


@dataclass(frozen=True)
class PhraseMatch:
    phrase: PhraseTarget
    segment: TranscriptSegment
    start_ms: int
    end_ms: int
    confidence: float = 1.0
    speaker: str | None = None


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _clean_word(text: str) -> str:
    return _PUNCT_RE.sub("", text).strip().lower()


def _find_word_span(
    words: tuple[WordTimestamp, ...],
    needle: str,
) -> tuple[float, float] | None:
    """Return (start_s, end_s) of the tightest word span covering needle, or None."""
    if not words:
        return None

    cleaned = [_clean_word(w.word) for w in words]
    joined = " ".join(cleaned)

    if needle not in joined:
        return None

    start_char = joined.index(needle)
    end_char = start_char + len(needle) - 1

    char_pos = 0
    start_idx = end_idx = None
    for i, token in enumerate(cleaned):
        word_end = char_pos + len(token) - 1
        if start_idx is None and word_end >= start_char:
            start_idx = i
        if char_pos <= end_char:
            end_idx = i
        char_pos += len(token) + 1

    if start_idx is None or end_idx is None:
        return None

    return words[start_idx].start, words[end_idx].end


def _dominant_speaker(
    diarization: list[SpeakerSegment],
    start_s: float,
    end_s: float,
) -> str | None:
    overlap: dict[str, float] = {}
    for seg in diarization:
        ov_start = max(seg.start, start_s)
        ov_end = min(seg.end, end_s)
        if ov_end > ov_start:
            overlap[seg.speaker] = overlap.get(seg.speaker, 0.0) + (ov_end - ov_start)
    if not overlap:
        return None
    return max(overlap, key=overlap.__getitem__)


def find_phrase_matches(
    phrases: list[PhraseTarget],
    segments: list[TranscriptSegment],
    diarization: list[SpeakerSegment] | None = None,
    min_confidence: float = 1.0,
) -> list[PhraseMatch]:
    matches: list[PhraseMatch] = []
    seen_ids: set[str] = set()

    for phrase in phrases:
        if phrase.id in seen_ids:
            continue

        needle = _normalize(phrase.text)

        for segment in segments:
            seg_text = _normalize(segment.text)

            if min_confidence >= 1.0:
                if needle not in seg_text:
                    continue
                score = 1.0
            else:
                score = fuzz.partial_ratio(needle, seg_text) / 100.0
                if score < min_confidence:
                    continue

            # Word-level timestamps for exact matches only
            span: tuple[float, float] | None = None
            if min_confidence >= 1.0 and segment.words:
                span = _find_word_span(segment.words, needle)

            if span:
                start_ms = max(0, int(span[0] * 1000) - phrase.padding_ms)
                end_ms = int(span[1] * 1000) + phrase.padding_ms
            else:
                start_ms = max(0, int(segment.start * 1000) - phrase.padding_ms)
                end_ms = int(segment.end * 1000) + phrase.padding_ms

            speaker: str | None = None
            if diarization:
                speaker = _dominant_speaker(diarization, start_ms / 1000.0, end_ms / 1000.0)

            matches.append(
                PhraseMatch(
                    phrase=phrase,
                    segment=segment,
                    start_ms=start_ms,
                    end_ms=end_ms,
                    confidence=score,
                    speaker=speaker,
                )
            )
            seen_ids.add(phrase.id)
            break

    return matches
